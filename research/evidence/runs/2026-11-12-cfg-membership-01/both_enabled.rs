use std::{cell::UnsafeCell, marker::PhantomData};
#[cfg(feature = "smp")]
use std::sync::atomic::{AtomicBool, Ordering};
pub trait BaseGuard {}
struct ProbeGuard;
impl BaseGuard for ProbeGuard {}
mod klockstat {
    pub struct LockClassStats;
    pub static NOOP_CLASS: LockClassStats = LockClassStats;
}
pub struct SpinLock<G: BaseGuard, T: ?Sized> {
    marker: PhantomData<G>,
    #[cfg(feature = "smp")]
    flag: AtomicBool,
    #[cfg(feature = "stats")]
    stats: &'static klockstat::LockClassStats,
    storage: UnsafeCell<T>,
}
impl<G: BaseGuard, T> SpinLock<G, T> {
    /// Create a new spinlock.
    #[inline(always)]
    #[cfg(all())]
    pub const fn new(data: T) -> Self {
        Self {
            marker: PhantomData,
            storage: UnsafeCell::new(data),
            #[cfg(feature = "smp")]
            flag: AtomicBool::new(false),
        }
    }

    /// Create a new spinlock.
    #[inline(always)]
    #[cfg(all())]
    pub const fn new(data: T) -> Self {
        Self::new_with_stats(data, &klockstat::NOOP_CLASS)
    }

    /// Creates a new spinlock bound to `stats`.
    #[inline(always)]
    #[cfg(feature = "stats")]
    pub const fn new_with_stats(data: T, stats: &'static klockstat::LockClassStats) -> Self {
        Self {
            marker: PhantomData,
            storage: UnsafeCell::new(data),
            #[cfg(feature = "smp")]
            flag: AtomicBool::new(false),
            stats,
        }
    }

    /// Consume the lock and return the inner value.
    #[inline(always)]
    pub fn into_inner(self) -> T {
        self.storage.into_inner()
    }
}

fn main() {
    let lock = SpinLock::<ProbeGuard, u32>::new(42);
    #[cfg(feature = "smp")]
    assert!(!lock.flag.load(Ordering::Relaxed));
    #[cfg(feature = "stats")]
    assert!(std::ptr::eq(lock.stats, &klockstat::NOOP_CLASS));
    assert_eq!(lock.into_inner(), 42);
    println!("constructor assertions passed");
}
