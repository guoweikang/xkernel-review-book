fn mount_filesystem_with_requested_superblock_flags(
        &self,
        fs: &Arc<SuperBlock>,
        flags: MountFlags,
        devname: Option<&str>,
        requested_superblock_flags: Option<SuperBlockFlags>,
    ) -> VfsResult<Arc<Mount>> {
        // A second mount of the same superblock at its own root cannot make
        // any new filesystem state visible, but stacking it would hide every
        // child mount attached below the existing mount. Keep the existing
        // mount when it is at least as restrictive as the request; otherwise
        // let the new mount replace it so stricter flags take effect. A
        // request for looser flags is left to MS_REMOUNT rather than silently
        // weakening the live mount. A bind mount of a subdirectory is not the
        // superblock root, so it is always replaced by a full-filesystem mount.
        if requested_superblock_flags.is_none_or(|flags| flags.is_empty())
            && self.is_mount_root()
            && Arc::ptr_eq(self.mount().super_block(), fs)
            && self.mount().root_path().dentry.ptr_eq(&fs.root_dir())
            && self.mount().flags().contains(flags)
        {
            return Ok(self.mount().clone());
        }
        let mount = Mount::try_new_detached(fs, flags, devname, requested_superblock_flags)?
            .ok_or(VfsError::ResourceBusy)?;
        self.graft_tree(mount)
    }