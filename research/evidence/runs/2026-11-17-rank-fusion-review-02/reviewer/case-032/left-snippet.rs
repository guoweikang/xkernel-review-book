fn read_iter(&self, iocb: &mut Kiocb<'_>, iter: &mut IovIterDest<'_>) -> VfsResult<usize> {
        let read = pipe_read_iter(iocb, iter)?;
        if read > 0 {
            iocb.file().file_accessed();
        }
        Ok(read)
    }