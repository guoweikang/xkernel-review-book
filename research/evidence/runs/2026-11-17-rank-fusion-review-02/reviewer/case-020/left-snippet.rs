fn rmdir_tracked(&self, name: &str, cred: &Cred) -> VfsResult<Option<RemovedEntry>> {
        self.check_writable_mount()?;
        let mut removed = None;
        self.dentry.as_dir()?.rmdir_with(name, |victim| {
            self.may_modify_directory(cred)?;
            let victim_path = self.with_dentry(victim.clone());
            self.check_sticky(&victim_path, cred)?;
            victim_path.check_not_mountpoint()?;
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