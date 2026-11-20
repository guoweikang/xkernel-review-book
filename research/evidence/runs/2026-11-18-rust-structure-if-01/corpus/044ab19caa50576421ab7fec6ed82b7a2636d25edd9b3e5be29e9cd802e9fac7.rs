fn chown_mode(mode: Umode, old_gid: u32, new_gid: Option<u32>, cred: &Cred) -> NodePermission {
        let permission = mode.permission();
        if mode.node_type() == NodeType::Directory {
            return permission;
        }

        let mut result = permission;
        result.remove(NodePermission::SET_UID);
        if permission.contains(NodePermission::SET_GID) {
            let old_group_ok = cred.has_cap(kcred::CAP_FSETID) || cred.in_group(old_gid);
            if permission.contains(NodePermission::GROUP_EXEC) || !old_group_ok {
                result.remove(NodePermission::SET_GID);
            }
        }
        if result.bits() != permission.bits()
            && new_gid.is_some_and(|gid| !cred.has_cap(kcred::CAP_FSETID) && !cred.in_group(gid))
        {
            result.remove(NodePermission::SET_GID);
        }
        result
    }