fn cache_lookup_candidate(&self, name: &str, candidate: &Dentry) -> Option<Dentry> {
        let mut children = self.0.children.lock();
        if let Some(entry) = children
            .get(name)
            .and_then(|entry| entry.upgrade().map(Dentry))
        {
            return Some(entry);
        }
        children.insert(name.to_owned(), Arc::downgrade(&candidate.0));
        drop(children);
        if let Some(super_block) = candidate.super_block() {
            super_block.cache_dentry(candidate.clone());
        }
        None
    }