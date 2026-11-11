    fn write(&self, file: &VfsFile, data: &[u8], _offset: u64) -> VfsResult<usize> {
        (self.0)(SimpleFileOperation::Write { file, data })?;
        Ok(data.len())
    }

