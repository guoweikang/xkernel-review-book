fn new_dir_with_inode_operations(
        private_data: Arc<dyn Any + Send + Sync>,
        inode_operations: Arc<dyn InodeOperations>,
        flags: NodeFlags,
        init: VfsInodeInit,
    ) -> Arc<Self> {
        let is_directory = init.mode.node_type() == NodeType::Directory;
        debug_assert!(is_directory);
        Self::from_parts(InodeParts {
            private_data,
            inode_operations,
            flags,
            file_operations: None,
            address_space_operations: empty_address_space_operations(),
            init,
        })
    }