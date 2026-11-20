fn test_hidden_mount_cannot_be_unmounted_while_overmounted() {
    let root_fs = mock_filesystem(StatFsFlags::empty());
    let fs_a = mock_filesystem(StatFsFlags::empty());
    let fs_b = mock_filesystem(StatFsFlags::empty());

    let root_mount = Mount::new_root(&root_fs);
    let mount_dir = lookup_no_follow(&root_mount.root_path(), "mnt").unwrap();
    let mount_a = mount_filesystem(&mount_dir, &fs_a).unwrap();
    let mount_b = mount_filesystem(&mount_dir, &fs_b).unwrap();

    assert_eq!(mount_a.root_path().unmount(), Err(VfsError::InvalidInput));

    mount_b.root_path().unmount().unwrap();
    mount_a.root_path().unmount().unwrap();
    assert_eq!(root_mount.children().len(), 0);
}