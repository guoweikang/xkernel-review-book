fn get() {
    static INIT: Once<usize> = Once::new();

    assert!(INIT.get().is_none());
    INIT.call_once(|| 2);
    assert_eq!(INIT.get().map(|r| *r), Some(2));
}