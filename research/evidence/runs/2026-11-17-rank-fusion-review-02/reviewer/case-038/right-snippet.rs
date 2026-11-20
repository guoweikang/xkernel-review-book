fn read_iter_from(&self, iter: &mut IovIterDest<'_>, pos: &mut u64) -> VfsResult<usize> {
        if self.is_stream() {
            self.verify_read_area(0, iter.count())?;
            let mut iocb = Kiocb::new(self, 0);
            self.operations().read_iter(&mut iocb, iter)
        } else {
            self.verify_read_area(*pos, iter.count())?;
            let mut iocb = Kiocb::new(self, *pos);
            let read = self.operations().read_iter(&mut iocb, iter)?;
            *pos = iocb.ki_pos();
            Ok(read)
        }
    }