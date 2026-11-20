fn pump_pipe_to_file(
    pipe: &PipeObject,
    input: &Arc<VfsFile>,
    output: &Arc<VfsFile>,
    output_position: TransferPosition<'_>,
    len: usize,
    nonblocking: bool,
) -> KResult<usize> {
    let output_offset = match output_position {
        TransferPosition::Managed => None,
        TransferPosition::At(offset) => Some(offset),
    };
    let mut output_pos = output_offset.as_deref().copied().unwrap_or(0);
    let output_managed = output_offset.is_none();
    let result = pump(len, |buf, chunk, total| {
        let wait = nonblocking || input.is_nonblocking() || total > 0;
        let confirmed = pipe.splice_read(wait, &mut buf[..chunk], |staged| {
            if output_managed && !output.is_stream() {
                output.write_from(staged, &mut output.position_lock())
            } else {
                output.write_from(staged, &mut output_pos)
            }
        })?;
        Ok(Step::Data {
            confirmed,
            stop: confirmed < chunk,
        })
    });
    if let Some(offset) = output_offset {
        *offset = output_pos;
    }
    result
}