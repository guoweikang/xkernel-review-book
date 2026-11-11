#![no_std]
fn align_up(value: usize, alignment: usize) -> Option<usize> {
    value.checked_next_multiple_of(alignment)
}

#[unsafe(no_mangle)]
pub fn evaluate(value: usize, alignment: usize) -> Option<usize> {
    align_up(value, alignment)
}
