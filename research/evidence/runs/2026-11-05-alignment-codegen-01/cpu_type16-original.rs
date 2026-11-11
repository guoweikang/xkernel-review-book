#![no_std]
fn align_up(value: usize, align: usize) -> Option<usize> {
    debug_assert!(align.is_power_of_two());
    value
        .checked_add(align - 1)
        .map(|value| value & !(align - 1))
}

#[repr(align(16))]
struct Aligned;
#[unsafe(no_mangle)]
pub fn evaluate(value: usize) -> Option<usize> {
    align_up(value, core::mem::align_of::<Aligned>())
}
