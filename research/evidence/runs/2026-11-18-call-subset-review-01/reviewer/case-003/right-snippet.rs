fn is_reachable_from(path: &Path, from: &Path) -> bool {
        let mut current = path.clone();
        loop {
            if current.ptr_eq(from) {
                return true;
            }
            match current.parent() {
                Some(parent) => current = parent,
                None => return false,
            }
        }
    }