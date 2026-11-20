extern crate alloc;

use alloc::{sync::{Arc, Weak}, vec::Vec};
use std::sync::Mutex;

struct Probe {
    identity: usize,
    drops: Arc<Mutex<Vec<usize>>>,
    lock_available: Option<Box<dyn Fn() -> bool + Send + Sync>>,
}

impl Drop for Probe {
    fn drop(&mut self) {
        if let Some(check) = &self.lock_available {
            assert!(check(), "destructor ran while wrapper mutex was held");
            println!("destructor identity={} same_mutex_try_lock=success", self.identity);
        }
        self.drops.lock().unwrap().push(self.identity);
    }
}

type SuperBlock = Probe;
type VfsInode = Probe;

struct SuperBlockSet {
    super_blocks: Vec<Weak<SuperBlock>>,
}

impl SuperBlockSet {
    fn live_super_blocks(&mut self) -> Vec<Arc<SuperBlock>> {
        let mut live = Vec::new();
        self.super_blocks
            .retain(|super_block| match super_block.upgrade() {
                Some(super_block) => {
                    live.push(super_block);
                    true
                }
                None => false,
            });
        live
    }

    fn candidate_live_super_blocks(&mut self) -> Vec<Arc<SuperBlock>> {
        collect_live(&mut self.super_blocks)
    }
}

struct InodeOwner {
    inodes: Arc<Mutex<Vec<Weak<VfsInode>>>>,
}

impl InodeOwner {
    fn live_inodes(&self) -> Vec<Arc<VfsInode>> {
        let mut live = Vec::new();
        self.inodes.lock().unwrap().retain(|inode| match inode.upgrade() {
            Some(inode) => {
                live.push(inode);
                true
            }
            None => false,
        });
        live
    }

    fn candidate_live_inodes(&self) -> Vec<Arc<VfsInode>> {
        let live = collect_live(&mut self.inodes.lock().unwrap());
        live
    }
}

fn collect_live<T>(entries: &mut Vec<Weak<T>>) -> Vec<Arc<T>> {
    let mut live = Vec::new();
    entries.retain(|entry| match entry.upgrade() {
        Some(value) => {
            live.push(value);
            true
        }
        None => false,
    });
    live
}

#[derive(Clone, Copy, Debug)]
enum Route {
    OriginalSet,
    CandidateSet,
    OriginalInodes,
    CandidateInodes,
}

const ROUTES: [Route; 4] = [
    Route::OriginalSet,
    Route::CandidateSet,
    Route::OriginalInodes,
    Route::CandidateInodes,
];

fn collect(route: Route, entries: &mut Vec<Weak<Probe>>) -> Vec<Arc<Probe>> {
    match route {
        Route::OriginalSet | Route::CandidateSet => {
            let mut set = SuperBlockSet { super_blocks: std::mem::take(entries) };
            let result = match route {
                Route::OriginalSet => set.live_super_blocks(),
                _ => set.candidate_live_super_blocks(),
            };
            *entries = set.super_blocks;
            result
        }
        Route::OriginalInodes | Route::CandidateInodes => {
            let owner = InodeOwner {
                inodes: Arc::new(Mutex::new(std::mem::take(entries))),
            };
            let result = match route {
                Route::OriginalInodes => owner.live_inodes(),
                _ => owner.candidate_live_inodes(),
            };
            *entries = std::mem::take(&mut *owner.inodes.lock().unwrap());
            result
        }
    }
}

fn pointers(values: &[Arc<Probe>]) -> Vec<*const Probe> {
    values.iter().map(Arc::as_ptr).collect()
}

fn weak_pointers(values: &[Weak<Probe>]) -> Vec<*const Probe> {
    values.iter().map(Weak::as_ptr).collect()
}

fn probe(identity: usize, drops: &Arc<Mutex<Vec<usize>>>) -> Arc<Probe> {
    Arc::new(Probe { identity, drops: drops.clone(), lock_available: None })
}

#[test]
fn empty_and_all_expired() {
    let drops = Arc::new(Mutex::new(Vec::new()));
    let dead = probe(9, &drops);
    let dead_weak = Arc::downgrade(&dead);
    drop(dead);
    for route in ROUTES {
        for (name, mut entries) in [
            ("empty", vec![]),
            ("all_expired", vec![dead_weak.clone(), Weak::new(), dead_weak.clone()]),
        ] {
            let result = collect(route, &mut entries);
            assert!(pointers(&result).is_empty());
            assert!(weak_pointers(&entries).is_empty());
            assert_eq!(*drops.lock().unwrap(), vec![9]);
            println!("{route:?} {name}: returned=[] retained=[] drops=[9]");
        }
    }
}

#[test]
fn mixed_duplicates_same_allocations_and_pinning() {
    let drops = Arc::new(Mutex::new(Vec::new()));
    let first = probe(10, &drops);
    let second = probe(20, &drops);
    let dead = probe(99, &drops);
    let dead_weak = Arc::downgrade(&dead);
    drop(dead);
    drops.lock().unwrap().clear();
    let weak_first = Arc::downgrade(&first);
    let weak_second = Arc::downgrade(&second);
    let input = vec![
        dead_weak.clone(), weak_first.clone(), dead_weak.clone(),
        weak_second.clone(), weak_first.clone(), Weak::new(), dead_weak,
    ];
    let expected = vec![Arc::as_ptr(&first), Arc::as_ptr(&second), Arc::as_ptr(&first)];
    let mut retained_lists = Vec::new();
    let mut snapshots = Vec::new();
    for (index, route) in ROUTES.into_iter().enumerate() {
        let mut entries = input.clone();
        let snapshot = collect(route, &mut entries);
        assert_eq!(pointers(&snapshot), expected);
        assert_eq!(weak_pointers(&entries), expected);
        assert_eq!(snapshot.iter().map(|value| value.identity).collect::<Vec<_>>(), vec![10, 20, 10]);
        let repeated = collect(route, &mut entries);
        assert_eq!(pointers(&repeated), expected);
        assert_eq!(weak_pointers(&entries), expected);
        drop(repeated);
        snapshots.push(snapshot);
        retained_lists.push(entries);
        assert_eq!(Arc::strong_count(&first), 1 + 2 * (index + 1));
        assert_eq!(Arc::strong_count(&second), 1 + index + 1);
        println!("{route:?} mixed: returned=[10,20,10] retained=[10,20,10] exact_pointer_oracle=PASS counts=({}, {})",
            Arc::strong_count(&first), Arc::strong_count(&second));
    }
    for pair in snapshots.windows(2) {
        assert_eq!(pointers(&pair[0]), pointers(&pair[1]));
    }
    drop((first, second));
    assert!(drops.lock().unwrap().is_empty());
    assert_eq!(weak_first.strong_count(), 8);
    assert_eq!(weak_second.strong_count(), 4);
    println!("external_owners_dropped: counts=(8,4) drops=[]");
    for remaining in (0..4).rev() {
        drop(snapshots.pop().unwrap());
        assert_eq!(weak_first.strong_count(), 2 * remaining);
        assert_eq!(weak_second.strong_count(), remaining);
        if remaining > 0 {
            assert!(drops.lock().unwrap().is_empty());
        }
    }
    let mut observed = drops.lock().unwrap().clone();
    observed.sort_unstable();
    assert_eq!(observed, vec![10, 20]);
    assert!(weak_first.upgrade().is_none());
    assert!(weak_second.upgrade().is_none());
    for (route, mut entries) in ROUTES.into_iter().zip(retained_lists) {
        assert_eq!(weak_pointers(&entries), expected);
        assert!(collect(route, &mut entries).is_empty());
        assert!(entries.is_empty());
    }
    println!("final_snapshots_dropped: counts=(0,0) drops_once_each=[10,20] recollect_empty=PASS");
}

fn check_guard_release(route: Route) {
    let drops = Arc::new(Mutex::new(Vec::new()));
    let (external, snapshot, lock_is_free): (Arc<Probe>, Vec<Arc<Probe>>, Box<dyn Fn() -> bool>) =
        match route {
            Route::OriginalSet | Route::CandidateSet => {
                let registry = Arc::new(Mutex::new(SuperBlockSet { super_blocks: Vec::new() }));
                let weak_registry = Arc::downgrade(&registry);
                let external = Arc::new(Probe {
                    identity: 42,
                    drops: drops.clone(),
                    lock_available: Some(Box::new(move || {
                        weak_registry.upgrade().unwrap().try_lock().is_ok()
                    })),
                });
                registry.lock().unwrap().super_blocks = vec![Arc::downgrade(&external); 2];
                let snapshot = {
                    let mut guard = registry.lock().unwrap();
                    assert!(registry.try_lock().is_err());
                    let result = match route {
                        Route::OriginalSet => guard.live_super_blocks(),
                        _ => guard.candidate_live_super_blocks(),
                    };
                    assert!(registry.try_lock().is_err());
                    assert!(drops.lock().unwrap().is_empty());
                    println!("{route:?} collection_boundary: outer_guard_held=true");
                    result
                };
                (external, snapshot, Box::new(move || registry.try_lock().is_ok()))
            }
            Route::OriginalInodes | Route::CandidateInodes => {
                let inodes = Arc::new(Mutex::new(Vec::new()));
                let weak_inodes = Arc::downgrade(&inodes);
                let external = Arc::new(Probe {
                    identity: 42,
                    drops: drops.clone(),
                    lock_available: Some(Box::new(move || {
                        weak_inodes.upgrade().unwrap().try_lock().is_ok()
                    })),
                });
                *inodes.lock().unwrap() = vec![Arc::downgrade(&external); 2];
                {
                    let guard = inodes.lock().unwrap();
                    assert!(inodes.try_lock().is_err());
                    assert_eq!(guard.len(), 2);
                }
                let owner = InodeOwner { inodes: inodes.clone() };
                let snapshot = match route {
                    Route::OriginalInodes => owner.live_inodes(),
                    _ => owner.candidate_live_inodes(),
                };
                println!("{route:?} collection_boundary: internal_guard_scope=source_checked; setup_try_lock_control=PASS");
                (external, snapshot, Box::new(move || inodes.try_lock().is_ok()))
            }
        };
    assert!(lock_is_free());
    assert_eq!(snapshot.len(), 2);
    assert!(Arc::ptr_eq(&snapshot[0], &external));
    assert!(Arc::ptr_eq(&snapshot[1], &external));
    assert_eq!(Arc::strong_count(&external), 3);
    let weak = Arc::downgrade(&external);
    drop(external);
    assert!(drops.lock().unwrap().is_empty());
    assert_eq!(weak.strong_count(), 2);
    println!("{route:?} wrapper_returned: guard_free=true external_dropped=true snapshot_pins=2 drops=[]");
    drop(snapshot);
    assert_eq!(*drops.lock().unwrap(), vec![42]);
    assert_eq!(weak.strong_count(), 0);
    assert!(lock_is_free());
    println!("{route:?} final_snapshot_drop: destructor_count=1 guard_free=true");
}

#[test]
fn original_set_guard_release() {
    check_guard_release(Route::OriginalSet);
}

#[test]
fn candidate_set_guard_release() {
    check_guard_release(Route::CandidateSet);
}

#[test]
fn original_inodes_guard_release() {
    check_guard_release(Route::OriginalInodes);
}

#[test]
fn candidate_inodes_guard_release() {
    check_guard_release(Route::CandidateInodes);
}
