fn splice_write(
        &self,
        nonblocking: bool,
        scratch: &mut [u8],
        mut read_fn: impl FnMut(&mut [u8]) -> KResult<usize>,
    ) -> KResult<usize> {
        if scratch.is_empty() {
            return Ok(0);
        }
        let result = block_on(poll_file_io(self, IoEvents::OUT, nonblocking, || {
            let mut state = self.state.lock();
            if state.readers == 0 {
                drop(state);
                let _ = send_sig_current(Signo::SIGPIPE);
                return Ok(Err(KError::BrokenPipe));
            }
            let count = scratch.len().min(state.available());
            if count == 0 {
                return Err(KError::WouldBlock);
            }
            let result = read_fn(&mut scratch[..count]);
            if let Ok(read) = result {
                if read > count {
                    return Ok(Err(KError::Io));
                }
                state.write_from(&scratch[..read]);
            }
            Ok(result)
        }))?;
        if matches!(result, Ok(count) if count > 0) {
            ktask::with_wake_sync(|| self.rd_wait.wake());
        }
        result
    }