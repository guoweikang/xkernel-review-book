fn interrupted_small_pipe_write_remains_atomic() {
    let pipe = PipeObject::new_anonymous();
    pipe.resize(PIPE_BUF).unwrap();
    assert_eq!(
        pipe.write(true, false, &vec![0x21; PIPE_BUF - 2]),
        Ok(PIPE_BUF - 2)
    );
    let task = ktask::current();
    task.interrupt();
    let result = pipe.write(false, true, b"abcd");
    task.clear_interrupt();
    assert_eq!(result, Err(KError::IoWaitInterrupted));
    assert_eq!(pipe.readable_len(), PIPE_BUF - 2);
    let mut output = vec![0; PIPE_BUF];
    assert_eq!(pipe.read(true, &mut output), Ok(PIPE_BUF - 2));
    assert!(output[..PIPE_BUF - 2].iter().all(|byte| *byte == 0x21));
}