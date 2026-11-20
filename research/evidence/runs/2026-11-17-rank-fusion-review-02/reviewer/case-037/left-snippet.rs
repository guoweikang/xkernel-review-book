fn llseek(&self, file: &VfsFile, offset: i64, whence: i32) -> VfsResult<u64> {
        if file.is_stream() || matches!(file.inode().node_type(), NodeType::Fifo | NodeType::Socket)
        {
            return Err(VfsError::from(LinuxError::ESPIPE));
        }

        let mut position = file.position_lock();
        let base = match whence {
            SEEK_SET => 0,
            SEEK_CUR => *position as i64,
            // The capacity view: `blkdev_llseek` reads `bd_inode`'s size
            // (block/fops.c:533), unlike record locks which read the node
            // inode (locks.c:465) — the two SEEK_END bases differ by design.
            SEEK_END => file.size() as i64,
            _ => return Err(VfsError::InvalidInput),
        };
        let new_offset = base.checked_add(offset).ok_or(VfsError::InvalidInput)?;
        if new_offset < 0 {
            return Err(VfsError::InvalidInput);
        }
        let new_offset = new_offset as u64;
        // Block devices bound seeks to the capacity (`blkdev_llseek` uses
        // `fixed_size_llseek`, EINVAL past the end); regular files may seek
        // past EOF.
        if file.inode().node_type() == NodeType::BlockDevice && new_offset > file.size() {
            return Err(VfsError::from(LinuxError::EINVAL));
        }
        *position = new_offset;
        Ok(new_offset)
    }