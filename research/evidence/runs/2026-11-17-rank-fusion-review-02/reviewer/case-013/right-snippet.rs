fn read(&self, _file: &VfsFile, buf: &mut [u8], offset: u64) -> VfsResult<usize> {
        let data = self.data.lock();
        let offset = offset as usize;
        if offset >= data.len() {
            return Ok(0);
        }
        let count = buf.len().min(data.len() - offset);
        buf[..count].copy_from_slice(&data[offset..offset + count]);
        Ok(count)
    }