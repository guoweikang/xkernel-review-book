fn set_xattr(
        &self,
        name: &XattrName,
        value: &[u8],
        flags: XattrSetFlags,
        cred: &Cred,
    ) -> VfsResult<()> {
        self.check_writable_mount()?;
        let inode = self.inode();
        check_xattr_permission(&inode, name, XattrAccess::Write, cred)?;
        let _data_guard = inode.lock_data();
        inode.set_xattr(self.dentry(), name, value, flags)
    }