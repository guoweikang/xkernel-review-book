fn lookup_or_create_with<F>(
        &self,
        name: &str,
        exclusive: bool,
        create_fn: F,
    ) -> VfsResult<LookupCreateResult>
    where
        F: FnOnce(&Dentry) -> VfsResult<()>,
    {
        self.with_locked_child(name, |candidate| {
            if candidate.is_really_positive() {
                return if exclusive {
                    Err(VfsError::AlreadyExists)
                } else {
                    Ok(LookupCreateResult::Existing(candidate.clone()))
                };
            }

            create_fn(candidate)?;
            if candidate.is_negative() {
                return Err(VfsError::InvalidInput);
            }
            Ok(LookupCreateResult::Created(candidate.clone()))
        })
    }