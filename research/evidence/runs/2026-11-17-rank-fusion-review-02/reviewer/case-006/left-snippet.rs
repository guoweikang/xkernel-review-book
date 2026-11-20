fn symlink(&self, name: &str, target: &str, cred: &Cred) -> VfsResult<Self> {
        self.dentry
            .as_dir()?
            .create_exclusive_with(name, |candidate| self.vfs_symlink(candidate, target, cred))
            .map(|entry| self.with_dentry(entry))
    }