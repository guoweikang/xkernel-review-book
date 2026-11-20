fn new_file_with_flags<T>(node: Arc<T>, flags: NodeFlags, init: VfsInodeInit) -> Arc<Self>
    where
        T: Any + Send + Sync + InodeOperations + FileOperations,
    {
        let private_data: Arc<dyn Any + Send + Sync> = node.clone();
        let inode_operations: Arc<dyn InodeOperations> = node.clone();
        let file_operations: Arc<dyn FileOperations> = node;
        Self::new_file_with_operations(private_data, inode_operations, file_operations, flags, init)
    }