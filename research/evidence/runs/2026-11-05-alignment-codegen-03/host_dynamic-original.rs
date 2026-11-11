#![no_std]
fn align_up(value: usize, alignment: usize) -> Option<usize> {
    value
        .checked_add(alignment - 1)
        .map(|value| value & !(alignment - 1))
}

#[unsafe(no_mangle)]
pub fn evaluate(value: usize, alignment: usize) -> Option<usize> {
    align_up(value, alignment)
}
