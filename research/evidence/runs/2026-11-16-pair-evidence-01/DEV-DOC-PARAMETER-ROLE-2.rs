const fn with_node_type(self, node_type: NodeType) -> Self {
        Self(((node_type as u16) << NODE_TYPE_SHIFT) | (self.0 & PERMISSION_MASK))
    }