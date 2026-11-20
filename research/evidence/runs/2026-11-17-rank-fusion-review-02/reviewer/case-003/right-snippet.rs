fn remove_xattr(&self, name: &XattrName, cred: &Cred) -> VfsResult<()> {
        self.check_writable_mount()?;
        let inode = self.inode();
        check_xattr_permission(&inode, name, XattrAccess::Write, cred)?;
        let _data_guard = inode.lock_data();
        inode.remove_xattr(self.dentry(), name)
    }