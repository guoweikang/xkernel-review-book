fn align_up(value: u64, align: u64) -> Result<u64, &'static str> {
    if align == 0 || !align.is_power_of_two() {
        return Err("invalid alignment");
    }
    value.checked_next_multiple_of(align)
        .ok_or("aligned address overflow")
}
