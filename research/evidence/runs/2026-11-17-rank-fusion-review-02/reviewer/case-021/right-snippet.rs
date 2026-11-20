fn try_write(&self) -> Option<SpinRwLockWriteGuard<'_, G, T>> {
        let guard_state = G::acquire();
        let acquired = self
            .state
            .compare_exchange(0, WRITE_LOCKED, Ordering::Acquire, Ordering::Relaxed)
            .is_ok();

        if acquired {
            #[cfg(feature = "stats")]
            self.record_write_acquisition(false);
            Some(SpinRwLockWriteGuard {
                lock: self,
                guard_state,
            })
        } else {
            G::release(guard_state);
            None
        }
    }