fn new_symlink_with_address_space_and_flags<T>(
        node: Arc<T>,
        flags: NodeFlags,
        address_space_operations: &'static dyn AddressSpaceOperations,
        init: VfsInodeInit,
    ) -> Arc<Self>
    where
        T: Any + Send + Sync + InodeOperations,
    {
        debug_assert_eq!(init.mode.node_type(), NodeType::Symlink);
        let private_data: Arc<dyn Any + Send + Sync> = node.clone();
        let inode_operations: Arc<dyn InodeOperations> = node.clone();
        Self::new_file_with_address_space_operations(
            private_data,
            inode_operations,
            None,
            flags,
            address_space_operations,
            init,
        )
    }