fn write_block_device(device: &Arc<BlockDevice>, buf: &[u8], offset: u64) -> VfsResult<usize> {
    if buf.is_empty() {
        return Ok(0);
    }
    if device.is_read_only() {
        return Err(KError::OperationNotPermitted);
    }
    let total_bytes = device.size();
    if offset >= total_bytes {
        return Err(VfsError::StorageFull);
    }

    let block_size = device.block_size();
    let length = core::cmp::min(buf.len() as u64, total_bytes - offset) as usize;
    let input = &buf[..length];
    // Keep partial-sector writes on the read/modify/write path below.
    if offset.is_multiple_of(block_size as u64) && length.is_multiple_of(block_size) {
        device
            .write_block(offset / block_size as u64, input)
            .map_err(map_block_error)?;
        return Ok(length);
    }
    let first_block = offset / block_size as u64;
    let first_offset = (offset % block_size as u64) as usize;
    let extent = first_offset
        .checked_add(length)
        .ok_or(KError::InvalidInput)?;
    let blocks = extent.div_ceil(block_size);
    let mut copied = 0;
    let mut scratch = None;

    for index in 0..blocks {
        let block_offset = if index == 0 { first_offset } else { 0 };
        let copy_length = core::cmp::min(block_size - block_offset, length - copied);
        let block_id = first_block + index as u64;
        let result = if block_offset == 0 && copy_length == block_size {
            device.write_block(block_id, &input[copied..copied + copy_length])
        } else {
            let block = scratch.get_or_insert_with(|| alloc::vec![0u8; block_size]);
            device.read_block(block_id, block).and_then(|()| {
                block[block_offset..block_offset + copy_length]
                    .copy_from_slice(&input[copied..copied + copy_length]);
                device.write_block(block_id, block)
            })
        };
        if let Err(error) = result {
            return if copied == 0 {
                Err(map_block_error(error))
            } else {
                Ok(copied)
            };
        }
        copied += copy_length;
    }

    Ok(length)
}