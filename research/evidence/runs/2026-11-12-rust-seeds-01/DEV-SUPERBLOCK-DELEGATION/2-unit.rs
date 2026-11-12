fn try_new_with_flags_and_private<T, E>(
        file_system_type: &'static FileSystemType,
        ops: &'static dyn SuperBlockOperations,
        private: KBox<T>,
        flags: SuperBlockFlags,
        block_size: u64,
        max_file_size: u64,
        init_root_fn: impl FnOnce(&Arc<Self>) -> Result<Dentry, E>,
    ) -> Result<Arc<Self>, E>
    where
        T: Any + Send + Sync + 'static,
    {
        let super_block = Self::allocate(file_system_type, None, flags);
        super_block.initialize_with_private(
            ops,
            private,
            block_size,
            max_file_size,
            init_root_fn,
        )?;
        super_block.finish_initialization();
        super_block_registry().register(&super_block);
        Ok(super_block)
    }