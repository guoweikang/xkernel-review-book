enum Step {
    /// The source is exhausted; stop with the completed prefix. Nothing was
    /// confirmed and no destination side effect happened for this step.
    Eof,
    /// `confirmed` bytes landed at the destination. `stop` ends the pump
    /// after this step — a short source chunk, or a stream source whose
    /// published data must not be followed by a second blocking read.
    Data { confirmed: usize, stop: bool },
}

/// The one settlement loop shared by every transfer shape. Each step moves
/// at most `chunk` bytes through the buffer and reports what the destination
/// confirmed (`total` flows back in so pipe steps can downgrade to
/// non-blocking after the first byte). An error after progress returns the
/// completed prefix; only a zero-progress failure propagates.
fn pump(
    len: usize,
    mut step: impl FnMut(&mut [u8], usize, usize) -> KResult<Step>,
) -> KResult<usize> {
    let mut buf = vec![0; 0x1000]; // 4KB intermediate buffer
    let mut total = 0;
    let mut remaining = len;
    let mut result = Ok(0);
    while remaining > 0 {
        let chunk = buf.len().min(remaining);
        match step(&mut buf, chunk, total) {
            Ok(Step::Eof) => break,
            Ok(Step::Data { confirmed, stop }) => {
                total += confirmed;
                remaining -= confirmed;
                result = Ok(total);
                if stop || confirmed == 0 {
                    break;
                }
            }
            Err(error) => {
                result = if total > 0 { Ok(total) } else { Err(error) };
                break;
            }
        }
    }
    result
}

/// The buffered file-pair copy step shared by [`transfer_files`] and
/// [`copy_file_range`]: one read at the local source position, one write at
/// the local destination position, the oversized-backend-count guards, and
/// the accepted-prefix rewind. [`pump`] owns the settlement around it.
fn file_pair_step(
    input: &Arc<VfsFile>,
    output: &Arc<VfsFile>,
    input_pos: &mut u64,
    output_pos: &mut u64,
    buf: &mut [u8],
    chunk: usize,
) -> KResult<Step> {
    let mut read_pos = *input_pos;
    let read = input.read_from(&mut buf[..chunk], &mut read_pos)?;
    if read > chunk {
        return Err(KError::Io);
    }
    if read == 0 {
        return Ok(Step::Eof);
    }
    let mut write_pos = *output_pos;
    let written = output.write_from(&buf[..read], &mut write_pos)?;
    if written > read {
        return Err(KError::Io);
    }
    // Only the accepted prefix commits: the tail stays at the source
    // for the next step to re-read.
    *input_pos += written as u64;
    *output_pos = write_pos;
    Ok(Step::Data {
        confirmed: written,
        stop: written < read,
    })
}

