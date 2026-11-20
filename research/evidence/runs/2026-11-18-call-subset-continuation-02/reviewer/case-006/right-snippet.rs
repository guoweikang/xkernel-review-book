fn create(&self, name: &str, permission: NodePermission, cred: &Cred) -> VfsResult<Self> {
        let mode = Umode::new(NodeType::RegularFile, permission);
        self.dentry
            .as_dir()?
            .create_exclusive_with(name, |candidate| {
                self.vfs_create(candidate, mode, NodePermission::empty(), true, cred)
            })
            .map(|entry| self.with_dentry(entry))
    }