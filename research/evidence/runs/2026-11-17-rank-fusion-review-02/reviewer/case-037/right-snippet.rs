fn llseek(&self, offset: i64, whence: i32) -> VfsResult<u64> {
        if !self.mode().contains(FMode::LSEEK) {
            return Err(VfsError::from(LinuxError::ESPIPE));
        }
        self.operations().llseek(self, offset, whence)
    }