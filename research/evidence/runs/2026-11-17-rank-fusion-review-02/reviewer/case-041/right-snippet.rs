fn new_file<T>(node: Arc<T>, init: VfsInodeInit) -> Arc<Self>
    where
        T: Any + Send + Sync + InodeOperations + FileOperations,
    {
        let private_data: Arc<dyn Any + Send + Sync> = node.clone();
        let inode_operations: Arc<dyn InodeOperations> = node.clone();
        let file_operations: Arc<dyn FileOperations> = node;
        Self::new_file_with_operations(
            private_data,
            inode_operations,
            file_operations,
            NodeFlags::empty(),
            init,
        )
    }