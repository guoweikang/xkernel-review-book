fn try_call_once<F: FnOnce() -> Result<T, E>, E>(&self, f: F) -> Result<&T, E> {
        // Fast path: check if already initialized
        if let Some(existing_value) = self.get() {
            return Ok(existing_value);
        }

        // Slow path: perform initialization
        self.try_call_once_slow(f)
    }