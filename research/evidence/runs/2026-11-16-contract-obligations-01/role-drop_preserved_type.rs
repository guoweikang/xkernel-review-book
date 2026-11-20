/// Filesystem node type values.
#[repr(u8)]
#[derive(Debug, Clone, Copy, Eq, PartialEq)]
pub enum NodeType {
    Unknown         = 0,
    Fifo            = 0o1,
    CharacterDevice = 0o2,
    Directory       = 0o4,
    BlockDevice     = 0o6,
    RegularFile     = 0o10,
    Symlink         = 0o12,
    Socket          = 0o14,
}

impl NodeType {
    const fn from_mode_type(value: u8) -> Self {
        match value {
            0o1 => Self::Fifo,
            0o2 => Self::CharacterDevice,
            0o4 => Self::Directory,
            0o6 => Self::BlockDevice,
            0o10 => Self::RegularFile,
            0o12 => Self::Symlink,
            0o14 => Self::Socket,
            _ => Self::Unknown,
        }
    }

    pub(crate) const fn is_special(self) -> bool {
        matches!(
            self,
            Self::CharacterDevice | Self::BlockDevice | Self::Fifo | Self::Socket
        )
    }
}

impl From<u8> for NodeType {
    fn from(value: u8) -> Self {
        Self::from_mode_type(value)
    }
}

bitflags::bitflags! {
    /// Inode permission mode.
    #[derive(Debug, Clone, Copy)]
    pub struct NodePermission: u16 {
        /// Set user ID on execution.
        const SET_UID = 0o4000;
        /// Set group ID on execution.
        const SET_GID = 0o2000;
        /// Sticky bit.
        const STICKY = 0o1000;

        /// Owner has read permission.
        const OWNER_READ = 0o400;
        /// Owner has write permission.
        const OWNER_WRITE = 0o200;
        /// Owner has execute permission.
        const OWNER_EXEC = 0o100;

        /// Group has read permission.
        const GROUP_READ = 0o40;
        /// Group has write permission.
        const GROUP_WRITE = 0o20;
        /// Group has execute permission.
        const GROUP_EXEC = 0o10;

        /// Others have read permission.
        const OTHER_READ = 0o4;
        /// Others have write permission.
        const OTHER_WRITE = 0o2;
        /// Others have execute permission.
        const OTHER_EXEC = 0o1;
    }
}

impl Default for NodePermission {
    fn default() -> Self {
        Self::from_bits_truncate(0o666)
    }
}

const NODE_TYPE_SHIFT: u16 = 12;
const NODE_TYPE_MASK: u16 = 0o170000;
const PERMISSION_MASK: u16 = 0o7777;

/// Inode mode value encoded with Linux `umode_t` layout.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Umode(u16);

impl Umode {
    /// Creates a mode value from raw Linux mode bits.
    pub const fn from_bits(bits: u16) -> Self {
        Self(bits)
    }

    /// Creates a mode value from a node type and permission bits.
    pub const fn new(node_type: NodeType, permission: NodePermission) -> Self {
        Self(((node_type as u16) << NODE_TYPE_SHIFT) | (permission.bits() & PERMISSION_MASK))
    }

    /// Returns the raw Linux mode bits.
    pub const fn bits(self) -> u16 {
        self.0
    }

    /// Returns the file type encoded in this mode.
    pub const fn node_type(self) -> NodeType {
        NodeType::from_mode_type(((self.0 & NODE_TYPE_MASK) >> NODE_TYPE_SHIFT) as u8)
    }

    const fn type_bits(self) -> u16 {
        self.0 & NODE_TYPE_MASK
    }

    /// Returns the node type requested through a Linux `mknod(2)` mode.
    ///
    /// An absent type field denotes a regular file. Unsupported or malformed
    /// type fields are returned as their decoded [`NodeType`] so the namei
    /// boundary can assign the operation-specific error.
    pub const fn mknod_node_type(self) -> NodeType {
        match self.type_bits() {
            0 => NodeType::RegularFile,
            _ => self.node_type(),
        }
    }

    /// Returns the permission bits encoded in this mode.
    pub const fn permission(self) -> NodePermission {
        NodePermission::from_bits_truncate(self.0 & PERMISSION_MASK)
    }

    /// Returns this mode with new permission bits and the same file type.
    pub const fn with_permission(self, permission: NodePermission) -> Self {
        Self(permission.bits() & PERMISSION_MASK)
    }

    /// Returns this mode with a new file type and the same permission bits.
    pub const fn with_node_type(self, node_type: NodeType) -> Self {
        Self(((node_type as u16) << NODE_TYPE_SHIFT) | (self.0 & PERMISSION_MASK))
    }
}


#[test]
fn declared_obligations() {
    for bits in 0..=u16::MAX {
        for permission_bits in [0, 1, 0o644, 0o755, 0o4000, 0o7777] {
            let permission = NodePermission::from_bits_retain(permission_bits);
            let result = Umode::from_bits(bits).with_permission(permission).bits();
            assert_eq!(result & PERMISSION_MASK, permission_bits & PERMISSION_MASK, "replace:permission_bits bits={} permission={}", bits, permission_bits);
            assert_eq!(result & NODE_TYPE_MASK, bits & NODE_TYPE_MASK, "preserve:file_type_bits bits={} permission={}", bits, permission_bits);
        }
    }
}
