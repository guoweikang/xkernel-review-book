fn write_iter(&self, iocb: &mut Kiocb<'_>, iter: &mut IovIterSource<'_>) -> VfsResult<usize> {
        const MAX_COMMAND_SIZE: usize = 4096;
        let count = iter.count();
        if count == 0 {
            return Ok(0);
        }
        if count > MAX_COMMAND_SIZE {
            return Err(VfsError::FileTooLarge);
        }
        let mut command = alloc::vec![0; count];
        let mut copied = 0;
        while copied < count {
            let read = match iter.copy_from_iter(&mut command[copied..]) {
                Ok(read) => read,
                Err(error) => {
                    iter.revert(copied)?;
                    return Err(error);
                }
            };
            if read == 0 {
                iter.revert(copied)?;
                return Err(VfsError::BadAddress);
            }
            copied += read;
        }
        let written = match self.write(iocb.file(), &command, iocb.ki_pos()) {
            Ok(written) => written,
            Err(error) => {
                iter.revert(count)?;
                return Err(error);
            }
        };
        if written > count {
            iter.revert(count)?;
            return Err(VfsError::InvalidData);
        }
        iter.revert(count - written)?;
        if written == 0 {
            return Err(VfsError::WriteZero);
        }
        iocb.advance(written);
        Ok(written)
    }