fn read_block_device(device: &Arc<BlockDevice>, buf: &mut [u8], offset: u64) -> VfsResult<usize> {
    if buf.is_empty() {
        return Ok(0);
    }
    let total_bytes = device.size();
    if offset >= total_bytes {
        return Ok(0);
    }

    let block_size = device.block_size();
    let length = core::cmp::min(buf.len() as u64, total_bytes - offset) as usize;
    let output = &mut buf[..length];
    // Preserve an aligned caller extent: block backends already accept
    // contiguous blocks, so each sector need not incur its own completion wait.
    if offset.is_multiple_of(block_size as u64) && length.is_multiple_of(block_size) {
        device
            .read_block(offset / block_size as u64, output)
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
        if block_offset == 0 && copy_length == block_size {
            device
                .read_block(block_id, &mut output[copied..copied + copy_length])
                .map_err(map_block_error)?;
        } else {
            let block = scratch.get_or_insert_with(|| alloc::vec![0u8; block_size]);
            device
                .read_block(block_id, block)
                .map_err(map_block_error)?;
            output[copied..copied + copy_length]
                .copy_from_slice(&block[block_offset..block_offset + copy_length]);
        }
        copied += copy_length;
    }
    Ok(length)
}