fn getattr(
        &self,
        _idmap: &MountIdmap,
        _path: Option<&crate::Path>,
        _request_mask: GetattrRequestMask,
        _query_flags: GetattrQueryFlags,
    ) -> VfsResult<Metadata> {
        Ok(Metadata {
            device: 0,
            inode: 8,
            nlink: 1,
            mode: Umode::new(
                NodeType::BlockDevice,
                NodePermission::from_bits_truncate(0o666),
            ),
            uid: 0,
            gid: 0,
            size: 0,
            block_size: 0,
            blocks: 0,
            rdev: self.rdev,
            atime: SystemTime::UNIX_EPOCH,
            mtime: SystemTime::UNIX_EPOCH,
            ctime: SystemTime::UNIX_EPOCH,
        })
    }