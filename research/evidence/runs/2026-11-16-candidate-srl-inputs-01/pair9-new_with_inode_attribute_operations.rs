fn new_with_inode_attribute_operations<T>(
        node: Arc<T>,
        flags: NodeFlags,
        address_space_operations: &'static dyn AddressSpaceOperations,
        mut init: VfsInodeInit,
    ) -> Arc<Self>
    where
        T: Any + Send + Sync + InodeOperations + FileOperations + InodeAttributeOperations,
    {
        let node_type = init.node_type();
        let private_data: Arc<dyn Any + Send + Sync> = node.clone();
        let inode_operations: Arc<dyn InodeOperations> = node.clone();
        let attribute_operations: Arc<dyn InodeAttributeOperations> = node.clone();
        let (file_operations, address_space_operations) = match node_type {
            NodeType::Directory => {
                let file_operations: Arc<dyn FileOperations> = node.clone();
                (Some(file_operations), empty_address_space_operations())
            }
            NodeType::RegularFile | NodeType::Unknown => {
                let file_operations: Arc<dyn FileOperations> = node.clone();
                (Some(file_operations), address_space_operations)
            }
            NodeType::Symlink => (None, address_space_operations),
            NodeType::CharacterDevice
            | NodeType::BlockDevice
            | NodeType::Fifo
            | NodeType::Socket => {
                let (file_operations, rdev) = init_special_inode(node_type, init.rdev);
                init.rdev = rdev;
                (file_operations, empty_address_space_operations())
            }
        };
        Self::from_parts_with_attribute_operations(
            InodeParts {
                private_data,
                inode_operations,
                file_operations,
                flags,
                address_space_operations,
                init,
            },
            attribute_operations,
        )
    }