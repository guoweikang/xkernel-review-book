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
