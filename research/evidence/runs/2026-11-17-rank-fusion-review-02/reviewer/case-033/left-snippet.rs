fn get_link(
        &self,
        _dentry: Option<&Dentry>,
        _inode: &VfsInode,
        _done: &mut crate::DelayedCall,
    ) -> VfsResult<String> {
        String::from_utf8(self.data.lock().clone()).map_err(|_| VfsError::InvalidData)
    }