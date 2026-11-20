fn poll() {
    static INIT: Once<usize> = Once::new();

    assert!(INIT.poll().is_none());
    INIT.call_once(|| 3);
    assert_eq!(INIT.poll().map(|r| *r), Some(3));
}