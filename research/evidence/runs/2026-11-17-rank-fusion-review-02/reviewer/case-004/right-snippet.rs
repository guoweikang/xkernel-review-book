fn new_dir_with_flags<T>(node: Arc<T>, flags: NodeFlags, init: VfsInodeInit) -> Arc<Self>
    where
        T: Any + Send + Sync + InodeOperations,
    {
        let private_data: Arc<dyn Any + Send + Sync> = node.clone();
        let inode_operations: Arc<dyn InodeOperations> = node;
        Self::new_dir_with_inode_operations(private_data, inode_operations, flags, init)
    }