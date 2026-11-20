fn verify_write_area(&self, pos: u64, count: usize) -> VfsResult<()> {
        self.verify_mode(FMode::WRITE)?;
        if !self.mode().contains(FMode::CAN_WRITE) {
            return Err(VfsError::InvalidInput);
        }
        self.verify_io_area(pos, count)?;
        if self.node_type().is_special() {
            Ok(())
        } else {
            self.path().check_writable_mount()
        }
    }