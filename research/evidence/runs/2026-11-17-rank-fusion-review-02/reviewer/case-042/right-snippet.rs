fn test_dir_search_allowed_for_owner() {
    let mut m = meta(1000, 1000, 0o100);
    m.mode = m.mode.with_node_type(NodeType::Directory);
    assert!(check_dac_permission(&m, Permission::MAY_EXEC, &creds(1000, 2000, &[])).is_ok());
}