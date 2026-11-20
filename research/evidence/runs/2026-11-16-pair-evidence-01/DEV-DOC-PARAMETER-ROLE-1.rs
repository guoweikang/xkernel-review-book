const fn with_permission(self, permission: NodePermission) -> Self {
        Self((self.0 & NODE_TYPE_MASK) | (permission.bits() & PERMISSION_MASK))
    }