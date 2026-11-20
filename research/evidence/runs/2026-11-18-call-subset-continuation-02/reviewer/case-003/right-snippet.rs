fn initialize_with_private<T, E>(
        self: &Arc<Self>,
        ops: &'static dyn SuperBlockOperations,
        private: KBox<T>,
        block_size: u64,
        max_file_size: u64,
        init_root_fn: impl FnOnce(&Arc<Self>) -> Result<Dentry, E>,
    ) -> Result<(), E>
    where
        T: Any + Send + Sync + 'static,
    {
        self.initialize_inner(
            ops,
            None,
            Some(private),
            block_size,
            max_file_size,
            init_root_fn,
        )
    }