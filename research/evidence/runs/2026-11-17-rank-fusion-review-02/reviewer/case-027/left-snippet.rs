fn detach_tree(&self, path: &Path) -> VfsResult<()> {
        let mut mounts = self.mounts.lock();
        let root = Self::registered_mount_at(&mounts, path)?.clone();
        let removed = root.collect_subtree();
        for mount in &removed {
            Self::require_mount(&mounts, mount)?;
        }

        path.detach_mount_subtree(&removed)?;
        for mount in &removed {
            mounts.remove(&mount.mount_id());
        }
        drop(mounts);
        Ok(())
    }