fn getattr(
        &self,
        _idmap: &crate::MountIdmap,
        _path: Option<&crate::Path>,
        _request_mask: crate::GetattrRequestMask,
        _query_flags: crate::GetattrQueryFlags,
    ) -> VfsResult<Metadata> {
        Ok(Metadata {
            device: 0,
            inode: self.inode,
            nlink: 1,
            mode: crate::Umode::new(NodeType::Directory, NodePermission::default()),
            uid: 0,
            gid: 0,
            size: 0,
            block_size: 512,
            blocks: 1,
            rdev: Default::default(),
            atime: SystemTime::UNIX_EPOCH,
            mtime: SystemTime::UNIX_EPOCH,
            ctime: SystemTime::UNIX_EPOCH,
        })
    }