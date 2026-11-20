fn mkdir(&self, dentry: &Dentry, mode: Umode, cred: &Cred) -> VfsResult<()> {
        let dentry = dentry.lock_location();
        self.require_directory_operations()?
            .mkdir(&MountIdmap, self, &dentry, mode, cred)
    }