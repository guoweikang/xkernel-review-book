fn unlink_with<F>(&self, name: &str, may_unlink_fn: F) -> VfsResult<()>
    where
        F: FnOnce(&Dentry) -> VfsResult<()>,
    {
        self.as_dir()?;
        Self::verify_child_name(name)?;
        let dir_inode = self.vfs_inode();
        let _namespace_guard = dir_inode.lock_namespace_exclusive();
        let entry = self.lookup_positive_locked(&dir_inode, name)?;
        let victim_inode = entry.vfs_inode();
        if Arc::ptr_eq(&victim_inode, &dir_inode) {
            return Err(VfsError::InvalidInput);
        }
        let _victim_guard = victim_inode.lock_namespace_exclusive();
        if entry.is_dir() {
            return Err(VfsError::IsADirectory);
        }
        may_unlink_fn(&entry)?;
        dir_inode.unlink(&entry)?;
        entry.mark_unlinked();
        self.forget_cache_entry(name);
        Ok(())
    }