fn test_chown_without_new_ids_still_cleans_setid() {
    let fs = mock_regular_file_filesystem(NodePermission::from_bits_truncate(0o6666));
    let root = Mount::new_root(&fs).root_path();

    root.chown(None, None, &Cred::new(1000, 100)).unwrap();

    let metadata = root.metadata();
    assert_eq!((metadata.uid, metadata.gid), (1000, 100));
    assert_eq!(metadata.mode.permission().bits(), 0o2666);
}