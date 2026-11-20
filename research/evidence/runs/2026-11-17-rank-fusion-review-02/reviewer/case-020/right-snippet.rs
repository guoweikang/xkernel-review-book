fn rmdir_at_tracked(
        &self,
        root: &Path,
        base: &Path,
        cred: &Cred,
    ) -> VfsResult<Option<RemovedEntry>> {
        let lookup = self.parent_at(root, base, LookupIntent::Open, cred)?;
        match lookup.last_type {
            LastType::Norm => lookup.parent.rmdir_tracked(lookup.last.as_str(), cred),
            LastType::Dotdot => Err(VfsError::DirectoryNotEmpty),
            LastType::Dot => Err(VfsError::InvalidInput),
            LastType::Root => Err(VfsError::ResourceBusy),
        }
    }