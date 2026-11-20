fn live_inodes(&self) -> Vec<Arc<VfsInode>> {
        let mut live = Vec::new();
        self.inodes.lock().retain(|inode| match inode.upgrade() {
            Some(inode) => {
                live.push(inode);
                true
            }
            None => false,
        });
        live
    }