fn lookup_inode(self: &Arc<Self>, inode_number: u64) -> Option<Arc<VfsInode>> {
        node::lookup_inode(self, inode_number)
    }