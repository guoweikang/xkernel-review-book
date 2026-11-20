fn create_exclusive_with(
        &self,
        name: &str,
        create_fn: impl FnOnce(&Dentry) -> VfsResult<()>,
    ) -> VfsResult<Dentry> {
        self.with_locked_child(name, |candidate| {
            if candidate.is_really_positive() {
                return Err(VfsError::AlreadyExists);
            }
            create_fn(candidate)?;
            if candidate.is_negative() {
                return Err(VfsError::InvalidInput);
            }
            Ok(candidate.clone())
        })
    }