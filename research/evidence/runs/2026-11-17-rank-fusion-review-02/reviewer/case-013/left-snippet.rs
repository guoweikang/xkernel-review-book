fn read(&self, _file: &VfsFile, buf: &mut [u8], offset: u64) -> VfsResult<usize> {
        let data = self.data.lock();
        let start = offset as usize;
        if start >= data.len() {
            return Ok(0);
        }
        let count = buf.len().min(data.len() - start);
        buf[..count].copy_from_slice(&data[start..start + count]);
        Ok(count)
    }