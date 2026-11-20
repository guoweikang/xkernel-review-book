fn inode_init(inode: u64, node_type: NodeType, size: u64) -> VfsInodeInit {
    VfsInodeInit::new(
        inode,
        size,
        crate::Umode::new(node_type, NodePermission::default()),
    )
    .with_owner_links_and_rdev(0, 0, 1, Default::default())
    .with_stat_data(
        4096,
        1,
        SystemTime::UNIX_EPOCH,
        SystemTime::UNIX_EPOCH,
        SystemTime::UNIX_EPOCH,
    )
}