fn symlink_at_entry(
        &self,
        root: &Path,
        base: &Path,
        target: &str,
        cred: &Cred,
    ) -> VfsResult<CreatedEntry> {
        let (parent, last, has_trailing_slash) = self
            .parent_at(root, base, LookupIntent::Open, cred)?
            .into_create()?;
        let name = last.as_str();

        let path = parent
            .dentry()
            .as_dir()?
            .create_exclusive_with(name, |candidate| {
                if has_trailing_slash {
                    return Err(VfsError::NotFound);
                }
                parent.vfs_symlink(candidate, target, cred)
            })
            .map(|entry| parent.with_dentry(entry))?;
        Ok(CreatedEntry {
            path,
            name: String::from(name),
            parent: parent.inode(),
        })
    }