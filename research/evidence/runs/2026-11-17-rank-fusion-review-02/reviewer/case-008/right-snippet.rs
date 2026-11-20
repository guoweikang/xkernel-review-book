fn splice_read(
        &self,
        nonblocking: bool,
        scratch: &mut [u8],
        mut write_fn: impl FnMut(&[u8]) -> KResult<usize>,
    ) -> KResult<usize> {
        if scratch.is_empty() {
            return Ok(0);
        }
        let result = block_on(poll_file_io(self, IoEvents::IN, nonblocking, || {
            let mut state = self.state.lock();
            let count = scratch.len().min(state.buffer.len());
            if count == 0 {
                return if state.writers == 0 {
                    Ok(Ok(0))
                } else {
                    Err(KError::WouldBlock)
                };
            }
            state.copy_prefix(&mut scratch[..count]);
            let result = write_fn(&scratch[..count]);
            if let Ok(written) = result {
                if written > count {
                    return Ok(Err(KError::Io));
                }
                drop(state.buffer.drain(..written));
            }
            Ok(result)
        }))?;
        if matches!(result, Ok(count) if count > 0) {
            ktask::with_wake_sync(|| self.wr_wait.wake());
        }
        result
    }