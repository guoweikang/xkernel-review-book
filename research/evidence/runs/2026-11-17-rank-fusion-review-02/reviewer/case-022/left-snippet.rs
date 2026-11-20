fn new_dir_with_operations(
        private_data: Arc<dyn Any + Send + Sync>,
        inode_operations: Arc<dyn InodeOperations>,
        file_operations: Arc<dyn FileOperations>,
        flags: NodeFlags,
        init: VfsInodeInit,
    ) -> Arc<Self> {
        let is_directory = init.mode.node_type() == NodeType::Directory;
        debug_assert!(is_directory);
        Self::from_parts(InodeParts {
            private_data,
            inode_operations,
            file_operations: Some(file_operations),
            flags,
            address_space_operations: empty_address_space_operations(),
            init,
        })
    }