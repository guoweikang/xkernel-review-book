fn mknod(
        &self,
        name: &str,
        node_type: NodeType,
        permission: NodePermission,
        device: DeviceId,
        cred: &Cred,
    ) -> VfsResult<Self> {
        let mode = Umode::new(node_type, permission);
        self.dentry
            .as_dir()?
            .create_exclusive_with(name, |candidate| {
                self.vfs_mknod(candidate, mode, device, NodePermission::empty(), cred)
            })
            .map(|entry| self.with_dentry(entry))
    }