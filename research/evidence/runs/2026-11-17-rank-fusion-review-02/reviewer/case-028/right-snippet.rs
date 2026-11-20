fn flock(&self, file: &VfsFile, request: &crate::FileLock, is_blocking: bool) -> VfsResult<()> {
        if request.kind() == crate::FileLockType::Unlock
            && file.inode().existing_file_locks().is_none()
        {
            return Ok(());
        }
        file.inode().file_locks()?.apply(request, is_blocking)
    }