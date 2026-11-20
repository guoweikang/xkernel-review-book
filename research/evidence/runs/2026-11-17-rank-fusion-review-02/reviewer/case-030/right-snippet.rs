fn file_name(&self) -> Option<&'a str> {
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
            return match name {
                "." | ".." => None,
                _ => Some(name),
            };
        }
    }