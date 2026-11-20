fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self.try_read() {
            Some(guard) => f
                .debug_struct("SpinRwLock")
                .field("data", &&*guard)
                .finish(),
            None => f
                .debug_struct("SpinRwLock")
                .field("data", &"<locked>")
                .finish(),
        }
    }