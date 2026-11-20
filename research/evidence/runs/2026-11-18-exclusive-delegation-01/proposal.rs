    pub(crate) fn create_exclusive_with(
        &self,
        name: &str,
        create_fn: impl FnOnce(&Dentry) -> VfsResult<()>,
    ) -> VfsResult<Dentry> {
        self.lookup_or_create_with(name, true, create_fn)
            .map(|result| match result {
                LookupCreateResult::Existing(entry) | LookupCreateResult::Created(entry) => entry,
            })
    }
