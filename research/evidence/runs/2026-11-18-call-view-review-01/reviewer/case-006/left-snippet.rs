fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // Build debug representation as tuple structure
        let mut debug_builder = f.debug_tuple("LazyValue");

        // Display content based on initialization state
        let debug_builder = match self.value_storage.get() {
            Some(content) => debug_builder.field(&content),
            None => debug_builder.field(&format_args!("<uninit>")),
        };

        debug_builder.finish()
    }