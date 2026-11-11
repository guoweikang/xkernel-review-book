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

