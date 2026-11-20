fn rwlock_try_write_fails_when_reader_is_active() {
    let lock = TestRwSpinIrq::new(());
    let reader = lock.read();

    assert!(lock.try_write().is_none());
    assert_eq!(IRQ_CNT.load(Ordering::Relaxed), 1);

    drop(reader);
    assert!(lock.try_write().is_some());
    assert_eq!(IRQ_CNT.load(Ordering::Relaxed), 0);
}