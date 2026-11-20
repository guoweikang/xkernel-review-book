fn pump_file_to_pipe(
    pipe: &PipeObject,
    output: &Arc<VfsFile>,
    input: &Arc<VfsFile>,
    input_position: TransferPosition<'_>,
    len: usize,
    nonblocking: bool,
) -> KResult<usize> {
    let input_offset = match input_position {
        TransferPosition::Managed => None,
        TransferPosition::At(offset) => Some(offset),
    };
    let mut input_pos = input_offset.as_deref().copied().unwrap_or(0);
    let input_managed = input_offset.is_none();
    let result = pump(len, |buf, chunk, total| {
        let wait = nonblocking || output.is_nonblocking() || total > 0;
        let confirmed = pipe.splice_write(wait, &mut buf[..chunk], |staged| {
            if input_managed && !input.is_stream() {
                input.read_from(staged, &mut input.position_lock())
            } else {
                input.read_from(staged, &mut input_pos)
            }
        })?;
        // Do not start a second blocking source read after publishing
        // stream data into the pipe; return that completed prefix.
        Ok(Step::Data {
            confirmed,
            stop: confirmed < chunk || input.is_stream(),
        })
    });
    if let Some(offset) = input_offset {
        *offset = input_pos;
    }
    result
}