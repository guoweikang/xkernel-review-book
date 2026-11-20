fn write_iter_from(&self, iter: &mut IovIterSource<'_>, pos: &mut u64) -> VfsResult<usize> {
        if self.is_stream() {
            self.verify_write_area(0, iter.count())?;
            let mut iocb = Kiocb::new(self, 0);
            self.operations().write_iter(&mut iocb, iter)
        } else if self.flags().contains(OpenFlags::APPEND)
            && self.inode().node_type() != NodeType::BlockDevice
        {
            // Block devices keep the caller's position for appends: Linux
            // `blkdev_write_iter` writes at `ki_pos` and never repositions to
            // the capacity end like regular-file append handling does.
            let end = self.size();
            self.verify_write_area(end, iter.count())?;
            let mut iocb = Kiocb::new(self, end);
            let written = self.operations().write_iter(&mut iocb, iter)?;
            if written != 0 {
                *pos = iocb.ki_pos();
            }
            Ok(written)
        } else {
            self.verify_write_area(*pos, iter.count())?;
            let mut iocb = Kiocb::new(self, *pos);
            let written = self.operations().write_iter(&mut iocb, iter)?;
            if written != 0 {
                *pos = iocb.ki_pos();
            }
            Ok(written)
        }
    }