fn link(&self, name: &str, source: &Self, cred: &Cred) -> VfsResult<Self> {
        self.dentry
            .as_dir()?
            .create_exclusive_with(name, |candidate| self.vfs_link(candidate, source, cred))
            .map(|entry| self.with_dentry(entry))
    }