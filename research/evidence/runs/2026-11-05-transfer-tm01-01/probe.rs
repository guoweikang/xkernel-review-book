use std::sync::{Arc, Mutex};

#[derive(Debug, PartialEq)]
enum AxError { WouldBlock, Io }
type AxResult<Value> = Result<Value, AxError>;
type KResult<Value> = AxResult<Value>;
type KError = AxError;

struct IoEvents;
impl IoEvents {
    const IN: Self = Self;
    fn contains(&self, _: Self) -> bool { true }
}
trait FileLike {
    fn poll(&self) -> IoEvents;
    fn read(&self, buffer: &mut &mut [u8]) -> AxResult<usize>;
    fn write(&self, buffer: &mut &[u8]) -> AxResult<usize>;
}
trait PointerAccess {
    fn vm_read(&self) -> AxResult<u64>;
    fn vm_write(&self, value: u64) -> AxResult<()>;
}
impl PointerAccess for *mut u64 {
    fn vm_read(&self) -> AxResult<u64> { Ok(unsafe { **self }) }
    fn vm_write(&self, value: u64) -> AxResult<()> {
        unsafe { **self = value; }
        Ok(())
    }
}
struct File { bytes: Mutex<Vec<u8>>, limit: usize }
type VfsFile = File;
impl File {
    fn inner(&self) -> &Self { self }
    fn poll(&self) -> IoEvents { IoEvents }
    fn read_at(&self, buffer: &mut [u8], offset: u64) -> AxResult<usize> {
        let bytes = self.bytes.lock().unwrap();
        let start = (offset as usize).min(bytes.len());
        let count = buffer.len().min(bytes.len() - start);
        buffer[..count].copy_from_slice(&bytes[start..start + count]);
        Ok(count)
    }
    fn write_at(&self, buffer: &[u8], offset: u64) -> AxResult<usize> {
        let count = buffer.len().min(self.limit);
        let start = offset as usize;
        let mut bytes = self.bytes.lock().unwrap();
        let length = bytes.len().max(start + count);
        bytes.resize(length, 0);
        bytes[start..start + count].copy_from_slice(&buffer[..count]);
        Ok(count)
    }
    fn read_from(&self, buffer: &mut [u8], offset: &mut u64) -> AxResult<usize> {
        let count = self.read_at(buffer, *offset)?;
        *offset += count as u64;
        Ok(count)
    }
    fn write_from(&self, buffer: &[u8], offset: &mut u64) -> AxResult<usize> {
        let count = self.write_at(buffer, *offset)?;
        *offset += count as u64;
        Ok(count)
    }
}

enum SendFile {
    Direct(Arc<dyn FileLike>),
    Offset(Arc<File>, *mut u64),
}

impl SendFile {
    fn has_data(&self) -> bool {
        match self {
            SendFile::Direct(file) => file.poll(),
            SendFile::Offset(file, ..) => file.poll(),
        }
        .contains(IoEvents::IN)
    }

    fn read(&mut self, mut buf: &mut [u8]) -> AxResult<usize> {
        match self {
            SendFile::Direct(file) => file.read(&mut buf),
            SendFile::Offset(file, offset) => {
                let off = offset.vm_read()?;
                let bytes_read = file.inner().read_at(&mut buf, off)?;
                offset.vm_write(off + bytes_read as u64)?;
                Ok(bytes_read)
            }
        }
    }

    fn write(&mut self, mut buf: &[u8]) -> AxResult<usize> {
        match self {
            SendFile::Direct(file) => file.write(&mut buf),
            SendFile::Offset(file, offset) => {
                let off = offset.vm_read()?;
                let bytes_written = file.inner().write_at(buf, off)?;
                offset.vm_write(off + bytes_written as u64)?;
                Ok(bytes_written)
            }
        }
    }
}

fn do_send(mut src: SendFile, mut dst: SendFile, len: usize) -> AxResult<usize> {
    let mut buf = vec![0; 0x1000];
    let mut total_written = 0;
    let mut remaining = len;

    while remaining > 0 {
        if total_written > 0 && !src.has_data() {
            break;
        }
        let to_read = buf.len().min(remaining);
        let bytes_read = match src.read(&mut buf[..to_read]) {
            Ok(n) => n,
            Err(AxError::WouldBlock) if total_written > 0 => break,
            Err(e) => return Err(e),
        };
        if bytes_read == 0 {
            break;
        }

        let bytes_written = dst.write(&buf[..bytes_read])?;
        if bytes_written < bytes_read {
            break;
        }

        total_written += bytes_written;
        remaining -= bytes_written;
    }

    Ok(total_written)
}



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



fn check_transfer(starry: bool, limit: usize, expected: usize, expected_input: u64) {
    let input = Arc::new(File { bytes: Mutex::new(b"abcdefgh".to_vec()), limit: 8 });
    let output = Arc::new(File { bytes: Mutex::new(Vec::new()), limit });
    let mut input_pos = 0;
    let mut output_pos = 0;
    let result = if starry {
        do_send(SendFile::Offset(input.clone(), &mut input_pos),
                SendFile::Offset(output.clone(), &mut output_pos), 8)
    } else {
        pump(8, |buffer, chunk, _total| {
            file_pair_step(&input, &output, &mut input_pos, &mut output_pos, buffer, chunk)
        })
    };
    let source = input.bytes.lock().unwrap();
    let destination = output.bytes.lock().unwrap();
    let tail = &source[input_pos as usize..];
    println!("starry={starry} limit={limit} result={result:?} input={input_pos} output={output_pos} bytes={destination:?} tail={tail:?}");
    assert_eq!(result, Ok(expected));
    assert_eq!(input_pos, expected_input);
    assert_eq!(output_pos, limit as u64);
    assert_eq!(*destination, b"abcdefgh"[..limit]);
    assert_eq!(*source, b"abcdefgh");
    assert_eq!(tail, &b"abcdefgh"[expected_input as usize..]);
}

#[test]
fn starry_short_write_observation() { check_transfer(true, 3, 0, 8); }
#[test]
fn xkernel_short_write_observation() { check_transfer(false, 3, 3, 3); }
#[test]
fn starry_full_write_control() { check_transfer(true, 8, 8, 8); }
#[test]
fn xkernel_full_write_control() { check_transfer(false, 8, 8, 8); }
