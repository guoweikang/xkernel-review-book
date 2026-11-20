fn symlink(&self, dentry: &Dentry, target: &str, cred: &Cred) -> VfsResult<()> {
        let dentry = dentry.lock_location();
        self.require_directory_operations()?
            .symlink(&MountIdmap, self, &dentry, target, cred)
    }