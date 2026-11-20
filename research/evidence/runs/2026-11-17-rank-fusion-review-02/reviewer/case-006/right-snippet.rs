fn mkdir(&self, name: &str, permission: NodePermission, cred: &Cred) -> VfsResult<Self> {
        self.dentry
            .as_dir()?
            .create_exclusive_with(name, |candidate| {
                self.vfs_mkdir(candidate, permission, NodePermission::empty(), cred)
            })
            .map(|entry| self.with_dentry(entry))
    }