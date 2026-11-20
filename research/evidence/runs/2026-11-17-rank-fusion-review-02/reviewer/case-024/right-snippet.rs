fn mknod_at_entry(
        &self,
        root: &Path,
        base: &Path,
        mode: Umode,
        device: DeviceId,
        umask: NodePermission,
        cred: &Cred,
    ) -> VfsResult<CreatedEntry> {
        let node_type = may_mknod(mode)?;
        let mode = mode.with_node_type(node_type);
        let (parent, last, has_trailing_slash) = self
            .parent_at(root, base, LookupIntent::Open, cred)?
            .into_create()?;
        let name = last.as_str();
        let device = if matches!(node_type, NodeType::CharacterDevice | NodeType::BlockDevice) {
            device
        } else {
            DeviceId::default()
        };

        let path = parent
            .dentry()
            .as_dir()?
            .create_exclusive_with(name, |candidate| {
                if has_trailing_slash {
                    return Err(VfsError::NotFound);
                }
                if node_type == NodeType::RegularFile {
                    parent.vfs_create(candidate, mode, umask, true, cred)
                } else {
                    parent.vfs_mknod(candidate, mode, device, umask, cred)
                }
            })
            .map(|entry| parent.with_dentry(entry))?;
        Ok(CreatedEntry {
            path,
            name: String::from(name),
            parent: parent.inode(),
        })
    }