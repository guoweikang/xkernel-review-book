fn rename(
        &self,
        _idmap: &crate::MountIdmap,
        _old_dir: &VfsInode,
        _old_dentry: &LockedDentry<'_>,
        _new_dir: &VfsInode,
        _new_dentry: &LockedDentry<'_>,
        _flags: crate::RenameFlags,
    ) -> VfsResult<()> {
        Err(VfsError::OperationNotSupported)
    }