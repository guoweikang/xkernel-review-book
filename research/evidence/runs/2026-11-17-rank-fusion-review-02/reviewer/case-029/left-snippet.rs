fn submit_bio(&self, mut bio: block::Bio) {
        let block_id = bio.sector() / (block::BlockDeviceOperations::block_size(self) as u64 / 512);
        let result = match bio.operation() {
            block::BioOperation::Read => {
                bio.read_contiguous(|bytes| self.read_block(block_id, bytes))
            }
            block::BioOperation::Write => {
                bio.write_contiguous(|bytes| self.write_block(block_id, bytes))
            }
            block::BioOperation::Flush => self.flush(),
        };
        bio.end_io(result);
    }