    fn write_at(&self, buf: &[u8], offset: u64) -> VfsResult<usize> {
        let data = self.ops.read_all()?;
        if offset == 0 && buf.len() >= data.len() {
            self.ops.write_all(buf)?;
            return Ok(buf.len());
        }
        let mut data = data.to_vec();
        let end_pos = offset + buf.len() as u64;
        if end_pos > data.len() as u64 {
            data.resize(end_pos as usize, 0);
        }
        data[offset as usize..end_pos as usize].copy_from_slice(buf);
        self.ops.write_all(&data)?;
        Ok(buf.len())
    }

