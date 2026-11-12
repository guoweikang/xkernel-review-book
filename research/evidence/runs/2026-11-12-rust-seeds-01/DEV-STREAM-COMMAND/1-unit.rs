fn scalar_write_iter(
    iocb: &mut Kiocb<'_>,
    iter: &mut IovIterSource<'_>,
    mut write: impl FnMut(&VfsFile, &[u8], u64) -> VfsResult<usize>,
) -> VfsResult<usize> {
    let mut total = 0usize;
    let mut chunk = [0u8; memaddr::PAGE_SIZE_4K];
    while iter.count() != 0 {
        let want = chunk.len().min(iter.count());
        let copied = match iter.copy_from_iter(&mut chunk[..want]) {
            Ok(copied) => copied,
            Err(_) if total != 0 => break,
            Err(error) => return Err(error),
        };
        if copied == 0 {
            break;
        }
        let written = match write(iocb.file(), &chunk[..copied], iocb.ki_pos()) {
            Ok(written) => written,
            Err(error) => {
                iter.revert(copied)?;
                if total != 0 {
                    break;
                }
                return Err(error);
            }
        };
        if written > copied {
            iter.revert(copied)?;
            return Err(VfsError::InvalidData);
        }
        iter.revert(copied - written)?;
        if written == 0 {
            if total != 0 {
                break;
            }
            return Err(VfsError::WriteZero);
        }
        total += written;
        iocb.advance(written);
        if written < copied {
            break;
        }
    }
    Ok(total)
}