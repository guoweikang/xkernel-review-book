fn interrupted_pipe_write_preserves_committed_prefix() {
    let pipe = PipeObject::new_anonymous();
    pipe.resize(PIPE_BUF).unwrap();
    let bytes = vec![0x53; PIPE_BUF + 17];
    let task = ktask::current();
    task.interrupt();
    let result = pipe.write(false, false, &bytes);
    task.clear_interrupt();
    assert_eq!(result, Ok(PIPE_BUF));
    let mut output = vec![0; PIPE_BUF + 17];
    assert_eq!(pipe.read(true, &mut output), Ok(PIPE_BUF));
    assert_eq!(&output[..PIPE_BUF], &bytes[..PIPE_BUF]);
    assert_eq!(pipe.read(true, &mut output), Err(KError::WouldBlock));
}