fn rwlock_allows_multiple_readers() {
    let lock = TestRwSpinIrq::new(42);
    let first = lock.read();
    let second = lock.read();

    assert_eq!(*first, 42);
    assert_eq!(*second, 42);
    assert_eq!(IRQ_CNT.load(Ordering::Relaxed), 2);

    drop(first);
    drop(second);
    assert_eq!(IRQ_CNT.load(Ordering::Relaxed), 0);
}