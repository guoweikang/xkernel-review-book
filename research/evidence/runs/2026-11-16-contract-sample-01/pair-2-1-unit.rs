fn new(
        fs_type: &'static FileSystemType,
        source: Option<&'a str>,
        data: Option<&'a [u8]>,
        sb_flags: SuperBlockFlags,
        cred: &'a kcred::Cred,
    ) -> VfsResult<Self> {
        Self::initialize(Self {
            fs_type,
            purpose: FsContextPurpose::Mount,
            source,
            data,
            sb_flags,
            sb_flags_mask: SuperBlockFlags::empty(),
            cred,
            target_super_block: None,
            operations: None,
            fs_private: None,
            proposed_super_private: None,
        })
    }