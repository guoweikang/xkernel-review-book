fn mknod_with_mode(
        &self,
        dentry: &Dentry,
        mode: Umode,
        device: DeviceId,
        cred: &Cred,
    ) -> VfsResult<()> {
        let dentry = dentry.lock_location();
        self.require_directory_operations()?
            .mknod(&MountIdmap, self, &dentry, mode, device, cred)
    }