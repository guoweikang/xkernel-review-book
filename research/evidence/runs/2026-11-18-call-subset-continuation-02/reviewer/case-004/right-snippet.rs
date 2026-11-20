fn create_with_mode(
        &self,
        dentry: &Dentry,
        mode: Umode,
        exclusive: bool,
        cred: &Cred,
    ) -> VfsResult<()> {
        let dentry = dentry.lock_location();
        self.require_directory_operations()?.create(
            &MountIdmap,
            self,
            &dentry,
            mode,
            exclusive,
            cred,
        )
    }