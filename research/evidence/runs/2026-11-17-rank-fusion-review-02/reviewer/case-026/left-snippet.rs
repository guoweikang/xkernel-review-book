fn write(&self, _file: &VfsFile, buf: &[u8], offset: u64) -> VfsResult<usize> {
        let offset = offset as usize;
        let mut data = self.data.lock();
        if offset + buf.len() > data.len() {
            data.resize(offset + buf.len(), 0);
        }
        data[offset..offset + buf.len()].copy_from_slice(buf);
        Ok(buf.len())
    }