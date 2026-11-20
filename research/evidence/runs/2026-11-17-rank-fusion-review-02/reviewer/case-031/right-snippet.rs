fn test_chown_without_new_ids_is_a_noop_when_mode_does_not_change() {
    let fs = mock_regular_file_filesystem(NodePermission::from_bits_truncate(0o666));
    let root = Mount::new_root(&fs).root_path();

    // Linux turns chown's set-ID cleanup into ATTR_MODE only when a bit must
    // actually be cleared. An unrelated caller may therefore chown(-1, -1) on
    // a file without set-ID bits.
    root.chown(None, None, &Cred::new(2000, 200)).unwrap();

    let metadata = root.metadata();
    assert_eq!((metadata.uid, metadata.gid), (1000, 100));
    assert_eq!(metadata.mode.permission().bits(), 0o666);
}