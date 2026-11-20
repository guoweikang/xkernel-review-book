fn call_once<F: FnOnce() -> T>(&self, f: F) -> &T {
        match self.try_call_once(|| Ok::<T, core::convert::Infallible>(f())) {
            Ok(x) => x,
            Err(void) => match void {},
        }
    }