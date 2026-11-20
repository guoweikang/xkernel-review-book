fn new_reconfigure(
        super_block: &'a SuperBlock,
        source: Option<&'a str>,
        data: Option<&'a [u8]>,
        sb_flags: SuperBlockFlags,
        sb_flags_mask: SuperBlockFlags,
        cred: &'a kcred::Cred,
    ) -> VfsResult<Self> {
        Self::initialize(Self {
            fs_type: super_block.file_system_type(),
            purpose: FsContextPurpose::Reconfigure,
            source,
            data,
            sb_flags,
            sb_flags_mask,
            cred,
            target_super_block: Some(super_block),
            operations: None,
            fs_private: None,
            proposed_super_private: None,
        })
    }