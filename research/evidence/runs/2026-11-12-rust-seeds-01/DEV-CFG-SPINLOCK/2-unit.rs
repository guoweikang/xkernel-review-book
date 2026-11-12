const fn new(data: T) -> Self {
        Self::new_with_stats(data, &klockstat::NOOP_CLASS)
    }