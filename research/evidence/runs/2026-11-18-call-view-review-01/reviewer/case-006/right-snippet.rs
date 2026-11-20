fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        // Build debug representation based on current state
        let mut formatter = f.debug_tuple("OnceCell");

        let formatter = match self.get() {
            Some(value) => formatter.field(&value),
            None => formatter.field(&format_args!("<not-ready>")),
        };
        formatter.finish()
    }