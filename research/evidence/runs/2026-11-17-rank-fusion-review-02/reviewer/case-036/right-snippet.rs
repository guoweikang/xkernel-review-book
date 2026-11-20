fn write_iter(&self, iocb: &mut Kiocb<'_>, iter: &mut IovIterSource<'_>) -> VfsResult<usize> {
        let written = pipe_write_iter(iocb, iter)?;
        if written > 0 {
            iocb.file().file_update_time()?;
        }
        Ok(written)
    }