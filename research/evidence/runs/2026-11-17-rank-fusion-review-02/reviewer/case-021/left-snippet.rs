fn try_read(&self) -> Option<SpinRwLockReadGuard<'_, G, T>> {
        let guard_state = G::acquire();
        let state = self.state.load(Ordering::Relaxed);
        let acquired = state & WRITE_LOCKED == 0
            && state != READER_MASK
            && self
                .state
                .compare_exchange(state, state + 1, Ordering::Acquire, Ordering::Relaxed)
                .is_ok();

        if acquired {
            #[cfg(feature = "stats")]
            self.record_read_acquisition(false);
            Some(SpinRwLockReadGuard {
                lock: self,
                guard_state,
            })
        } else {
            G::release(guard_state);
            None
        }
    }