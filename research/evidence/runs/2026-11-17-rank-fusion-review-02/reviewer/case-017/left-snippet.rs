fn mkdir_at_entry(
        &self,
        root: &Path,
        base: &Path,
        permission: NodePermission,
        umask: NodePermission,
        cred: &Cred,
    ) -> VfsResult<CreatedEntry> {
        let (parent, last, _) = self
            .parent_at(root, base, LookupIntent::Open, cred)?
            .into_create()?;
        let name = last.as_str();

        let path = parent
            .dentry()
            .as_dir()?
            .create_exclusive_with(name, |candidate| {
                parent.vfs_mkdir(candidate, permission, umask, cred)
            })
            .map(|entry| parent.with_dentry(entry))?;
        Ok(CreatedEntry {
            path,
            name: String::from(name),
            parent: parent.inode(),
        })
    }