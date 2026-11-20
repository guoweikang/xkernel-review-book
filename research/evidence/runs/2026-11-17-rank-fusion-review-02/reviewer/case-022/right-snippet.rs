fn new_file_with_operations(
        private_data: Arc<dyn Any + Send + Sync>,
        inode_operations: Arc<dyn InodeOperations>,
        file_operations: Arc<dyn FileOperations>,
        flags: NodeFlags,
        init: VfsInodeInit,
    ) -> Arc<Self> {
        Self::new_file_with_operation_tables(
            private_data,
            inode_operations,
            Some(file_operations),
            flags,
            init,
        )
    }