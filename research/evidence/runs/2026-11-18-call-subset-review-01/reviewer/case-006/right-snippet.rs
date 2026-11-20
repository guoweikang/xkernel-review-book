fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self.try_lock() {
            Some(guard) => f.debug_struct("SpinLock").field("data", &&*guard).finish(),
            None => f
                .debug_struct("SpinLock")
                .field("data", &"<locked>")
                .finish(),
        }
    }