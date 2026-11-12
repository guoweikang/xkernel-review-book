fn new_with_flags_and_private<T>(
        file_system_type: &'static FileSystemType,
        ops: &'static dyn SuperBlockOperations,
        private: KBox<T>,
        flags: SuperBlockFlags,
        block_size: u64,
        max_file_size: u64,
        init_root_fn: impl FnOnce(&Arc<Self>) -> Dentry,
    ) -> Arc<Self>
    where
        T: Any + Send + Sync + 'static,
    {
        match Self::try_new_with_flags_and_private(
            file_system_type,
            ops,
            private,
            flags,
            block_size,
            max_file_size,
            |super_block| Ok::<_, core::convert::Infallible>(init_root_fn(super_block)),
        ) {
            Ok(super_block) => super_block,
            Err(error) => match error {},
        }
    }