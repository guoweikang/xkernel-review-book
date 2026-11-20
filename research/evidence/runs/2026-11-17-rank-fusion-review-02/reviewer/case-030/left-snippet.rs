fn parent(&self) -> Option<Pathname<'a>> {
        let mut end = self.inner.len();
        loop {
            while end > 0 && self.inner.as_bytes()[end - 1] == b'/' {
                end -= 1;
            }
            if end == 0 {
                return None;
            }
            let start = self.inner[..end]
                .rfind('/')
                .map(|index| index + 1)
                .unwrap_or(0);
            let name = &self.inner[start..end];
            if name == "." && start > 0 {
                end = if start == 1 { 0 } else { start - 1 };
                continue;
            }
            let parent_end = if start == 0 {
                0
            } else if start == 1 {
                1
            } else {
                start - 1
            };
            return Some(Pathname::new(&self.inner[..parent_end]));
        }
    }