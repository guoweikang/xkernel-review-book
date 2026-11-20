use std::panic::{AssertUnwindSafe, catch_unwind};
use std::sync::atomic::{AtomicUsize, Ordering::Relaxed};

macro_rules! component_witness {
    ($module:ident, $owner:path) => {
        mod $module {
            use super::*;
            use $owner as Owner;

            static COUNTER: AtomicUsize = AtomicUsize::new(0);

            struct CountsDropsAndPanics {}

            impl CountsDropsAndPanics {
                fn new() -> Self {
                    COUNTER.fetch_add(1, Relaxed);
                    Self {}
                }
            }

            impl Clone for CountsDropsAndPanics {
                fn clone(&self) -> Self {
                    if COUNTER.load(Relaxed) == 4 {
                        panic!("intentional panic")
                    } else {
                        Self::new()
                    }
                }
            }

            impl Drop for CountsDropsAndPanics {
                fn drop(&mut self) {
                    COUNTER.fetch_sub(1, Relaxed);
                }
            }

            #[test]
            fn make_mut_clone_panic_components() {
                let array: [CountsDropsAndPanics; 3] =
                    core::array::from_fn(|_| CountsDropsAndPanics::new());
                let mut owner: Owner<[CountsDropsAndPanics]> = Owner::new(array);
                let retained = Owner::clone(&owner);
                assert_eq!(COUNTER.load(Relaxed), 3);
                assert_eq!(Owner::strong_count(&owner), 2);

                let panic_payload = catch_unwind(AssertUnwindSafe(|| {
                    Owner::make_mut(&mut owner);
                }))
                .unwrap_err();
                assert_eq!(
                    panic_payload.downcast::<&str>().unwrap(),
                    Box::new("intentional panic")
                );
                assert_eq!(COUNTER.load(Relaxed), 3, "leaked during clone!");
                assert!(Owner::ptr_eq(&owner, &retained));
                assert_eq!(Owner::strong_count(&owner), 2);
                drop(owner);
                assert_eq!(COUNTER.load(Relaxed), 3);
                drop(retained);
                assert_eq!(COUNTER.load(Relaxed), 0);
            }
        }
    };
}

component_witness!(rc_case, std::rc::Rc);
component_witness!(arc_case, std::sync::Arc);
