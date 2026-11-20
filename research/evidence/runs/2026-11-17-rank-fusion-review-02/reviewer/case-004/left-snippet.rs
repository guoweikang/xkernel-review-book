fn new_dir<T>(node: Arc<T>, init: VfsInodeInit) -> Arc<Self>
    where
        T: Any + Send + Sync + InodeOperations,
    {
        let private_data: Arc<dyn Any + Send + Sync> = node.clone();
        let inode_operations: Arc<dyn InodeOperations> = node;
        Self::new_dir_with_inode_operations(
            private_data,
            inode_operations,
            NodeFlags::empty(),
            init,
        )
    }