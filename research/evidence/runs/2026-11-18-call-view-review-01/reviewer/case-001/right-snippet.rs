fn inode_init(inode: u64) -> VfsInodeInit {
    VfsInodeInit::new(
        inode,
        0,
        crate::Umode::new(NodeType::Directory, NodePermission::default()),
    )
    .with_owner_links_and_rdev(0, 0, 1, Default::default())
    .with_stat_data(
        512,
        1,
        SystemTime::UNIX_EPOCH,
        SystemTime::UNIX_EPOCH,
        SystemTime::UNIX_EPOCH,
    )
}