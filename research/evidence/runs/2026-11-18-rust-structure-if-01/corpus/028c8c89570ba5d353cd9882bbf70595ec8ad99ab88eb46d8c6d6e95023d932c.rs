fn detach_mount_subtree(&self, mounts: &[Arc<Mount>]) -> VfsResult<()> {
        if !self.dentry.ptr_eq(&self.mnt.mnt.mnt_root) {
            return Err(VfsError::InvalidInput);
        }
        if !mounts
            .first()
            .is_some_and(|root| Arc::ptr_eq(root, &self.mnt))
        {
            return Err(VfsError::InvalidInput);
        }

        let parent_path = self.mnt.location().ok_or(VfsError::InvalidInput)?;
        let inode = parent_path.inode();
        let _namespace_guard = inode.lock_namespace_exclusive();
        if !parent_path
            .mnt
            .child_mount_at(&parent_path.dentry)
            .is_some_and(|mount| Arc::ptr_eq(&mount, &self.mnt))
        {
            return Err(VfsError::InvalidInput);
        }

        let covered = self.mnt.covers.lock().take();
        match covered {
            Some(ref mount) => {
                parent_path
                    .mnt
                    .install_child_mount(&parent_path.dentry, mount);
            }
            None => parent_path.mnt.remove_child_mount(&parent_path.dentry),
        }

        // All fallible checks complete before this commit phase. The namespace
        // entry point also validates registry membership for every layer. The
        // remaining operations are infallible, so an overmount cannot be
        // restored halfway and leave stale registry entries.
        for mount in mounts {
            mount.mnt_mounts.lock().clear();
            mount.covers.lock().take();
            mount.detach();
        }
        Ok(())
    }