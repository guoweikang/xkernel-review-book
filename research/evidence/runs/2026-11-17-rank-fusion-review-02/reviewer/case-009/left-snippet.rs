fn unlink_with_pathname_tracked(
        &self,
        name: &str,
        has_trailing_slash: bool,
        cred: &Cred,
    ) -> VfsResult<Option<RemovedEntry>> {
        self.check_writable_mount()?;
        // Captured under the namespace lock, from the dentry the removal
        // actually unlinks -- the event identity must describe that object,
        // not whatever a separate lookup saw before the lock was taken.
        let mut removed = None;
        self.dentry.as_dir()?.unlink_with(name, |victim| {
            if has_trailing_slash {
                return Err(VfsError::NotADirectory);
            }
            self.may_modify_directory(cred)?;
            let victim_path = self.with_dentry(victim.clone());
            self.check_sticky(&victim_path, cred)?;
            victim_path.check_not_mountpoint()?;
            // Pre-unlink `nlink`: the FS decrements it when the unlink below
            // runs, and the retired-or-survives decision is about that move.
            // This one field must be authoritative, so it comes from `getattr`
            // -- a backend (9p) may leave the cached copy stale -- and a
            // failure means no retirement decision is taken at all rather than
            // a wrong one. Parent and victim references pin the event objects
            // independently of the mount used to reach them.
            removed = Some(RemovedEntry {
                parent: self.inode(),
                name: alloc::string::String::from(name),
                // Authoritative when the backend answers, cached otherwise:
                // a removal whose link count cannot be decided would leave the
                // watch pinned to a dead object forever, which is worse than
                // acting on a possibly stale count.
                victim_nlink: Some(
                    victim_path
                        .getattr()
                        .map_or_else(|_| victim_path.identity().nlink, |meta| meta.nlink),
                ),
                victim_dentry: victim.clone(),
            });
            Ok(())
        })?;
        Ok(removed)
    }