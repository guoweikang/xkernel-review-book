fn test_dir_search_denied_when_exec_bit_clear() {
    let mut m = meta(1000, 1000, 0o600);
    m.mode = m.mode.with_node_type(NodeType::Directory);
    assert!(check_dac_permission(&m, Permission::MAY_EXEC, &creds(1000, 2000, &[])).is_err());
}