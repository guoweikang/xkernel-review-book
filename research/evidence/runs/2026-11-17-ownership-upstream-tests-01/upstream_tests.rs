extern crate alloc;

mod rc_tests {
use std::rc::Rc;

#[test]
fn test_cowrc_clone_make_unique() {
    let mut cow0 = Rc::new(75);
    let mut cow1 = cow0.clone();
    let mut cow2 = cow1.clone();

    assert!(75 == *Rc::make_mut(&mut cow0));
    assert!(75 == *Rc::make_mut(&mut cow1));
    assert!(75 == *Rc::make_mut(&mut cow2));

    *Rc::make_mut(&mut cow0) += 1;
    *Rc::make_mut(&mut cow1) += 2;
    *Rc::make_mut(&mut cow2) += 3;

    assert!(76 == *cow0);
    assert!(77 == *cow1);
    assert!(78 == *cow2);

    // none should point to the same backing memory
    assert!(*cow0 != *cow1);
    assert!(*cow0 != *cow2);
    assert!(*cow1 != *cow2);
}

#[test]
fn test_cowrc_clone_unique2() {
    let mut cow0 = Rc::new(75);
    let cow1 = cow0.clone();
    let cow2 = cow1.clone();

    assert!(75 == *cow0);
    assert!(75 == *cow1);
    assert!(75 == *cow2);

    *Rc::make_mut(&mut cow0) += 1;

    assert!(76 == *cow0);
    assert!(75 == *cow1);
    assert!(75 == *cow2);

    // cow1 and cow2 should share the same contents
    // cow0 should have a unique reference
    assert!(*cow0 != *cow1);
    assert!(*cow0 != *cow2);
    assert!(*cow1 == *cow2);
}

#[test]
fn test_cowrc_clone_weak() {
    let mut cow0 = Rc::new(75);
    let cow1_weak = Rc::downgrade(&cow0);

    assert!(75 == *cow0);
    assert!(75 == *cow1_weak.upgrade().unwrap());

    *Rc::make_mut(&mut cow0) += 1;

    assert!(76 == *cow0);
    assert!(cow1_weak.upgrade().is_none());
}

#[test]
fn test_cowrc_unsized() {
    use std::rc::Rc;

    let mut data: Rc<[i32]> = Rc::new([10, 20, 30]);

    Rc::make_mut(&mut data)[0] += 1; // Won't clone anything
    let mut other_data = Rc::clone(&data); // Won't clone inner data
    Rc::make_mut(&mut data)[1] += 1; // Clones inner data
    Rc::make_mut(&mut data)[2] += 1; // Won't clone anything
    Rc::make_mut(&mut other_data)[0] *= 10; // Won't clone anything

    // Now `data` and `other_data` point to different allocations.
    assert_eq!(*data, [11, 21, 31]);
    assert_eq!(*other_data, [110, 20, 30]);
}

#[test]
fn test_clone_from_slice() {
    #[derive(Clone, Debug, Eq, PartialEq)]
    struct X(u32);

    let s: &[X] = &[X(1), X(2), X(3)];
    let r: Rc<[X]> = Rc::from(s);

    assert_eq!(&r[..], s);
}

#[test]
#[should_panic]
fn test_clone_from_slice_panic() {
    use std::string::{String, ToString};

    struct Fail(u32, String);

    impl Clone for Fail {
        fn clone(&self) -> Fail {
            if self.0 == 2 {
                panic!();
            }
            Fail(self.0, self.1.clone())
        }
    }

    let s: &[Fail] =
        &[Fail(0, "foo".to_string()), Fail(1, "bar".to_string()), Fail(2, "baz".to_string())];

    // Should panic, but not cause memory corruption
    let _r: Rc<[Fail]> = Rc::from(s);
}
}

mod arc_tests {
use std::sync::Arc;

#[test]
fn test_cowarc_clone_make_mut() {
    let mut cow0 = Arc::new(75);
    let mut cow1 = cow0.clone();
    let mut cow2 = cow1.clone();

    assert!(75 == *Arc::make_mut(&mut cow0));
    assert!(75 == *Arc::make_mut(&mut cow1));
    assert!(75 == *Arc::make_mut(&mut cow2));

    *Arc::make_mut(&mut cow0) += 1;
    *Arc::make_mut(&mut cow1) += 2;
    *Arc::make_mut(&mut cow2) += 3;

    assert!(76 == *cow0);
    assert!(77 == *cow1);
    assert!(78 == *cow2);

    // none should point to the same backing memory
    assert!(*cow0 != *cow1);
    assert!(*cow0 != *cow2);
    assert!(*cow1 != *cow2);
}

#[test]
fn test_cowarc_clone_unique2() {
    let mut cow0 = Arc::new(75);
    let cow1 = cow0.clone();
    let cow2 = cow1.clone();

    assert!(75 == *cow0);
    assert!(75 == *cow1);
    assert!(75 == *cow2);

    *Arc::make_mut(&mut cow0) += 1;
    assert!(76 == *cow0);
    assert!(75 == *cow1);
    assert!(75 == *cow2);

    // cow1 and cow2 should share the same contents
    // cow0 should have a unique reference
    assert!(*cow0 != *cow1);
    assert!(*cow0 != *cow2);
    assert!(*cow1 == *cow2);
}

#[test]
fn test_cowarc_clone_weak() {
    let mut cow0 = Arc::new(75);
    let cow1_weak = Arc::downgrade(&cow0);

    assert!(75 == *cow0);
    assert!(75 == *cow1_weak.upgrade().unwrap());

    *Arc::make_mut(&mut cow0) += 1;

    assert!(76 == *cow0);
    assert!(cow1_weak.upgrade().is_none());
}

#[test]
fn test_clone_from_slice() {
    #[derive(Clone, Debug, Eq, PartialEq)]
    struct X(u32);

    let s: &[X] = &[X(1), X(2), X(3)];
    let r: Arc<[X]> = Arc::from(s);

    assert_eq!(&r[..], s);
}

#[test]
#[should_panic]
fn test_clone_from_slice_panic() {
    use std::string::{String, ToString};

    struct Fail(u32, String);

    impl Clone for Fail {
        fn clone(&self) -> Fail {
            if self.0 == 2 {
                panic!();
            }
            Fail(self.0, self.1.clone())
        }
    }

    let s: &[Fail] =
        &[Fail(0, "foo".to_string()), Fail(1, "bar".to_string()), Fail(2, "baz".to_string())];

    // Should panic, but not cause memory corruption
    let _r: Arc<[Fail]> = Arc::from(s);
}

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
}
