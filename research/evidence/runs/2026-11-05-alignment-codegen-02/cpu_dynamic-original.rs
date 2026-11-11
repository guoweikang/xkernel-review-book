#![no_std]
fn align_up(value: usize, align: usize) -> Option<usize> {
    debug_assert!(align.is_power_of_two());
    value
        .checked_add(align - 1)
        .map(|value| value & !(align - 1))
}

#[unsafe(no_mangle)]
pub fn evaluate(value: usize, alignment: usize) -> Option<usize> {
    align_up(value, alignment)
}
