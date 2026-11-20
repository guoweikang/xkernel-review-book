impl Dentry {
    fn cache_live_or_insert(
        &self,
        name: alloc::borrow::Cow<'_, str>,
        candidate: &Dentry,
    ) -> Option<Dentry> {
        let mut children = self.0.children.lock();
        if let Some(entry) = children
            .get(name.as_ref())
            .and_then(|entry| entry.upgrade().map(Dentry))
        {
            return Some(entry);
        }
        children.insert(name.into_owned(), Arc::downgrade(&candidate.0));
        None
    }

    fn cache_lookup_candidate(&self, name: &str, candidate: &Dentry) -> Option<Dentry> {
        if let Some(entry) =
            self.cache_live_or_insert(alloc::borrow::Cow::Borrowed(name), candidate)
        {
            return Some(entry);
        }
        if let Some(super_block) = candidate.super_block() {
            super_block.cache_dentry(candidate.clone());
        }
        None
    }

    pub fn insert_cache(&self, name: String, entry: Dentry) -> Option<Dentry> {
        if self.can_cache_children() && entry.can_cache_as_child() {
            if let Some(existing) =
                self.cache_live_or_insert(alloc::borrow::Cow::Owned(name), &entry)
            {
                return Some(existing);
            }
            if let Some(super_block) = entry.super_block() {
                super_block.cache_dentry(entry);
            }
        }
        None
    }
}
