extern crate alloc;

#[path = "original.rs"]
mod original;
#[path = "candidate.rs"]
mod candidate;

fn compare_borrows(before: Option<&str>, after: Option<&str>) {
    match (before, after) {
        (None, None) => {}
        (Some(before), Some(after)) => {
            assert_eq!(before, after);
            assert_eq!(before.len(), after.len());
            assert_eq!(before.as_ptr(), after.as_ptr());
        }
        _ => assert!(false, "Option variants differ"),
    }
}

#[kani::proof]
#[kani::unwind(64)]
fn check_path_methods() {
    let buffer: [u8; 4] = kani::any();
    let length: usize = kani::any();
    kani::assume(length <= buffer.len());
    let parsed = core::str::from_utf8(&buffer[..length]);
    kani::assume(parsed.is_ok());
    let input = parsed.unwrap();
    let before = original::Pathname::new(input);
    let after = candidate::Pathname::new(input);
    compare_borrows(before.file_name(), after.file_name());
    compare_borrows(before.parent().map(|path| path.as_str()), after.parent().map(|path| path.as_str()));
}
