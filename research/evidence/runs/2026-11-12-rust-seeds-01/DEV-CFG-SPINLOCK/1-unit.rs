const fn new(data: T) -> Self {
        Self {
            marker: PhantomData,
            storage: UnsafeCell::new(data),
            #[cfg(feature = "smp")]
            flag: AtomicBool::new(false),
        }
    }