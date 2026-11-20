fn initialize<E>(
        self: &Arc<Self>,
        ops: &'static dyn SuperBlockOperations,
        block_size: u64,
        max_file_size: u64,
        init_root_fn: impl FnOnce(&Arc<Self>) -> Result<Dentry, E>,
    ) -> Result<(), E> {
        self.initialize_inner(ops, None, None, block_size, max_file_size, init_root_fn)
    }