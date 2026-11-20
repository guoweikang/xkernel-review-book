fn graft_tree(&self, mount: Mount) -> VfsResult<Arc<Mount>> {
        let inode = self.inode();
        let _namespace_guard = inode.lock_namespace_exclusive();
        if mount.mnt.mnt_root.as_dir().is_ok() != self.is_dir() {
            // Linux `graft_tree()` returns `ENOTDIR` for either direction of
            // a directory/non-directory mismatch.
            return Err(VfsError::NotADirectory);
        }
        let result = mount.into_arc_at(Some(self.clone()));
        if let Some(old) = self.mnt.install_child_mount(&self.dentry, &result) {
            *result.covers.lock() = Some(old);
        }
        Ok(result)
    }