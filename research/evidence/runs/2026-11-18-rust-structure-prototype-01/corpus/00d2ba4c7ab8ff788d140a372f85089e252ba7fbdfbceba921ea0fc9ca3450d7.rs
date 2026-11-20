fn insert_cache(&self, name: String, entry: Dentry) -> Option<Dentry> {
        if self.can_cache_children() && entry.can_cache_as_child() {
            let mut children = self.0.children.lock();
            if let Some(existing) = children
                .get(&name)
                .and_then(|entry| entry.upgrade().map(Dentry))
            {
                return Some(existing);
            }
            children.insert(name, Arc::downgrade(&entry.0));
            drop(children);
            if let Some(super_block) = entry.super_block() {
                super_block.cache_dentry(entry);
            }
        }
        None
    }