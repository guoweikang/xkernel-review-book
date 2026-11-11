#![no_std]
fn align_up(value: usize, align: usize) -> Option<usize> {
    debug_assert!(align.is_power_of_two());
    value.checked_next_multiple_of(align)
}

#[repr(align(16))]
struct Aligned;
#[unsafe(no_mangle)]
pub fn evaluate(value: usize) -> Option<usize> {
    align_up(value, core::mem::align_of::<Aligned>())
}
