fn write(&self, _file: &VfsFile, buf: &[u8], offset: u64) -> VfsResult<usize> {
        let mut data = self.data.lock();
        let start = offset as usize;
        if start + buf.len() > data.len() {
            data.resize(start + buf.len(), 0);
        }
        data[start..start + buf.len()].copy_from_slice(buf);
        Ok(buf.len())
    }