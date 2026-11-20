fn detach(&self, path: &Path) -> VfsResult<()> {
        let mut mounts = self.mounts.lock();
        let removed = Self::registered_mount_at(&mounts, path)?.clone();
        path.unmount()?;
        mounts.remove(&removed.mount_id());
        drop(mounts);
        Ok(())
    }