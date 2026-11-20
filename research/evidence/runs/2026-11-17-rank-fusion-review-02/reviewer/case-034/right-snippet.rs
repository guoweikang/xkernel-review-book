fn new_file_with_address_space<T>(
        node: Arc<T>,
        address_space_operations: &'static dyn AddressSpaceOperations,
        init: VfsInodeInit,
    ) -> Arc<Self>
    where
        T: Any + Send + Sync + InodeOperations + FileOperations,
    {
        let private_data: Arc<dyn Any + Send + Sync> = node.clone();
        let inode_operations: Arc<dyn InodeOperations> = node.clone();
        let file_operations: Arc<dyn FileOperations> = node.clone();
        Self::new_file_with_address_space_operations(
            private_data,
            inode_operations,
            Some(file_operations),
            NodeFlags::empty(),
            address_space_operations,
            init,
        )
    }