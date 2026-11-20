#[test]
fn make_mut_unsized() {
    use alloc::sync::Arc;

    let mut data: Arc<[i32]> = Arc::new([10, 20, 30]);

    Arc::make_mut(&mut data)[0] += 1; // Won't clone anything
    let mut other_data = Arc::clone(&data); // Won't clone inner data
    Arc::make_mut(&mut data)[1] += 1; // Clones inner data
    Arc::make_mut(&mut data)[2] += 1; // Won't clone anything
    Arc::make_mut(&mut other_data)[0] *= 10; // Won't clone anything

    // Now `data` and `other_data` point to different allocations.
    assert_eq!(*data, [11, 21, 31]);
    assert_eq!(*other_data, [110, 20, 30]);
}
