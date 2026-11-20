fn test_unmount_rejects_mount_with_nested_children() {
    let root_fs = mock_filesystem(StatFsFlags::empty());
    let child_fs = mock_filesystem(StatFsFlags::empty());
    let grandchild_fs = mock_filesystem(StatFsFlags::empty());

    let root_mount = Mount::new_root(&root_fs);
    let first_mount_dir = lookup_no_follow(&root_mount.root_path(), "mnt").unwrap();
    let child_mount = mount_filesystem(&first_mount_dir, &child_fs).unwrap();
    let second_mount_dir = lookup_no_follow(&child_mount.root_path(), "mnt").unwrap();
    let grandchild_mount = mount_filesystem(&second_mount_dir, &grandchild_fs).unwrap();

    assert_eq!(
        child_mount.root_path().unmount(),
        Err(VfsError::ResourceBusy)
    );
    assert_eq!(child_mount.children().len(), 1);
    assert_eq!(root_mount.children().len(), 1);

    grandchild_mount.root_path().unmount().unwrap();
    child_mount.root_path().unmount().unwrap();
    assert_eq!(root_mount.children().len(), 0);
}