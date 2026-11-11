#![no_std]
fn align_up(value: usize, align: usize) -> Option<usize> {
    debug_assert!(align.is_power_of_two());
    value.checked_next_multiple_of(align)
}

#[unsafe(no_mangle)]
pub fn evaluate(value: usize, alignment: usize) -> Option<usize> {
    align_up(value, alignment)
}
