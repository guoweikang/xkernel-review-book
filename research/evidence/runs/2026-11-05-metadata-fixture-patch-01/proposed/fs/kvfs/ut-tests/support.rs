use ktime_types::SystemTime;

use crate::{Metadata, NodePermission, NodeType};

pub(crate) fn directory_metadata(inode: u64) -> Metadata {
    Metadata {
        device: 0,
        inode: inode,
        nlink: 1,
        mode: crate::Umode::new(NodeType::Directory, NodePermission::default()),
        uid: 0,
        gid: 0,
        size: 0,
        block_size: 512,
        blocks: 1,
        rdev: Default::default(),
        atime: SystemTime::UNIX_EPOCH,
        mtime: SystemTime::UNIX_EPOCH,
        ctime: SystemTime::UNIX_EPOCH,
    }
}
