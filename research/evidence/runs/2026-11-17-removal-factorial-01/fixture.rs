use core::sync::atomic::{AtomicUsize as RemovalAtomic, Ordering as RemovalOrdering};

struct RemovalEventState {
    backend_nlink: RemovalAtomic,
    getattr_calls: RemovalAtomic,
    getattr_seen_at_remove: RemovalAtomic,
    unlink_calls: RemovalAtomic,
    rmdir_calls: RemovalAtomic,
    fail_getattr: bool,
    fail_remove: bool,
}

struct RemovalEventOps {
    base: MockDirOps,
    state: Arc<RemovalEventState>,
    victim: bool,
    node_type: NodeType,
}

impl InodeOperations for RemovalEventOps {
    fn directory_operations(&self) -> Option<&dyn InodeDirOperations> {
        Some(self)
    }

    fn getattr(
        &self,
        idmap: &crate::MountIdmap,
        path: Option<&crate::Path>,
        request_mask: crate::GetattrRequestMask,
        query_flags: crate::GetattrQueryFlags,
    ) -> VfsResult<Metadata> {
        if self.victim {
            self.state.getattr_calls.fetch_add(1, RemovalOrdering::SeqCst);
            if self.state.fail_getattr {
                return Err(VfsError::OperationNotSupported);
            }
        }
        let mut metadata = self.base.getattr(idmap, path, request_mask, query_flags)?;
        metadata.mode = crate::Umode::new(
            self.node_type,
            NodePermission::from_bits_truncate(0o777),
        );
        if self.victim {
            metadata.nlink = self.state.backend_nlink.load(RemovalOrdering::SeqCst) as u64;
        }
        Ok(metadata)
    }
}

impl FileOperations for RemovalEventOps {}

impl RemovalEventOps {
    fn remove_event_victim(&self, dentry: &LockedDentry<'_>) -> VfsResult<()> {
        self.state.getattr_seen_at_remove.store(
            self.state.getattr_calls.load(RemovalOrdering::SeqCst),
            RemovalOrdering::SeqCst,
        );
        if self.state.fail_remove {
            return Err(VfsError::OperationNotSupported);
        }
        self.state.backend_nlink.store(2, RemovalOrdering::SeqCst);
        dentry.set_link_count(2);
        Ok(())
    }
}

impl InodeDirOperations for RemovalEventOps {
    fn lookup(
        &self,
        dir: &VfsInode,
        dentry: &LockedDentry<'_>,
        flags: crate::InodeLookupFlags,
    ) -> VfsResult<Option<Dentry>> {
        self.base.lookup(dir, dentry, flags)
    }

    fn unlink(&self, _dir: &VfsInode, dentry: &LockedDentry<'_>) -> VfsResult<()> {
        self.state.unlink_calls.fetch_add(1, RemovalOrdering::SeqCst);
        self.remove_event_victim(dentry)
    }

    fn rmdir(&self, _dir: &VfsInode, dentry: &LockedDentry<'_>) -> VfsResult<()> {
        self.state.rmdir_calls.fetch_add(1, RemovalOrdering::SeqCst);
        self.remove_event_victim(dentry)
    }
}

fn removal_event_init(number: u64, node_type: NodeType, nlink: u64) -> VfsInodeInit {
    VfsInodeInit::new(
        number,
        0,
        crate::Umode::new(node_type, NodePermission::from_bits_truncate(0o777)),
    )
    .with_owner_links_and_rdev(0, 0, nlink, Default::default())
    .with_stat_data(
        512,
        1,
        SystemTime::UNIX_EPOCH,
        SystemTime::UNIX_EPOCH,
        SystemTime::UNIX_EPOCH,
    )
}

fn check_removal_event_case(is_directory: bool, fail_getattr: bool, fail_remove: bool) {
    let state = Arc::new(RemovalEventState {
        backend_nlink: RemovalAtomic::new(7),
        getattr_calls: RemovalAtomic::new(0),
        getattr_seen_at_remove: RemovalAtomic::new(0),
        unlink_calls: RemovalAtomic::new(0),
        rmdir_calls: RemovalAtomic::new(0),
        fail_getattr,
        fail_remove,
    });
    let parent_ops = Arc::new(RemovalEventOps {
        base: MockDirOps::new(StatFsFlags::empty(), 8001),
        state: state.clone(),
        victim: false,
        node_type: NodeType::Directory,
    });
    let parent_inode = VfsInode::new_openable_dir(
        parent_ops,
        removal_event_init(8001, NodeType::Directory, 1),
    );
    let parent = Dentry::new_dir_from_inode(parent_inode.clone(), None, String::new());
    let super_block = mock_superblock(parent.clone(), StatFsFlags::empty());
    let mount = Mount::new_root(&super_block);
    let root = mount.root_path();
    let node_type = if is_directory { NodeType::Directory } else { NodeType::RegularFile };
    let victim_ops = Arc::new(RemovalEventOps {
        base: MockDirOps::new(StatFsFlags::empty(), 8002),
        state: state.clone(),
        victim: true,
        node_type,
    });
    let init = removal_event_init(8002, node_type, 3);
    let victim_inode = if is_directory {
        VfsInode::new_openable_dir(victim_ops, init)
    } else {
        VfsInode::new_file(victim_ops, init)
    };
    let name = "removal-event-victim";
    let victim = if is_directory {
        Dentry::new_dir_from_inode(victim_inode.clone(), Some(parent.clone()), String::from(name))
    } else {
        Dentry::new_file_from_inode(victim_inode.clone(), Some(parent.clone()), String::from(name))
    };
    parent.insert_cache(String::from(name), victim.clone());
    assert_eq!(root.with_dentry(victim.clone()).identity().nlink, 3);
    assert_eq!(state.getattr_calls.load(RemovalOrdering::SeqCst), 0);
    let cred = kcred::initial_cred();
    let result = if is_directory {
        root.rmdir_tracked(name, &cred)
    } else {
        root.unlink_with_pathname_tracked(name, false, &cred)
    };
    assert_eq!(state.unlink_calls.load(RemovalOrdering::SeqCst), if is_directory { 0 } else { 1 });
    assert_eq!(state.rmdir_calls.load(RemovalOrdering::SeqCst), if is_directory { 1 } else { 0 });
    assert_eq!(state.getattr_calls.load(RemovalOrdering::SeqCst), 1);
    assert_eq!(state.getattr_seen_at_remove.load(RemovalOrdering::SeqCst), 1);
    if fail_remove {
        assert_eq!(result.err(), Some(VfsError::OperationNotSupported));
        assert!(parent.lookup_cache(name).unwrap().ptr_eq(&victim));
        assert_eq!(state.backend_nlink.load(RemovalOrdering::SeqCst), 7);
        assert_eq!(victim_inode.link_count(), 3);
    } else {
        let removed = result.unwrap().unwrap();
        assert!(Arc::ptr_eq(&removed.parent, &parent_inode));
        assert_eq!(removed.name.as_str(), name);
        assert!(removed.victim_dentry.ptr_eq(&victim));
        assert!(Arc::ptr_eq(&removed.victim_dentry.inode_ref(), &victim_inode));
        assert_eq!(removed.victim_nlink, Some(if fail_getattr { 3 } else { 7 }));
        assert_eq!(state.backend_nlink.load(RemovalOrdering::SeqCst), 2);
        assert_eq!(victim_inode.link_count(), 2);
        assert!(parent.lookup_cache(name).is_none());
    }
}

#[def_test]
fn removal_event_unlink_backend_snapshot() {
    check_removal_event_case(false, false, false);
}

#[def_test]
fn removal_event_rmdir_backend_snapshot() {
    check_removal_event_case(true, false, false);
}

#[def_test]
fn removal_event_unlink_cached_fallback() {
    check_removal_event_case(false, true, false);
}

#[def_test]
fn removal_event_rmdir_cached_fallback() {
    check_removal_event_case(true, true, false);
}

#[def_test]
fn removal_event_unlink_failure_not_committed() {
    check_removal_event_case(false, false, true);
    check_removal_event_case(false, true, true);
}

#[def_test]
fn removal_event_rmdir_failure_not_committed() {
    check_removal_event_case(true, false, true);
    check_removal_event_case(true, true, true);
}
