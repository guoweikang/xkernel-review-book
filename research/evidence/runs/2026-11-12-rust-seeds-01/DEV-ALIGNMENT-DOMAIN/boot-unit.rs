fn align_up(value: u64, align: u64) -> Result<u64, &'static str> {
    if align == 0 || !align.is_power_of_two() {
        return Err("invalid alignment");
    }
    value
        .checked_add(align - 1)
        .map(|value| value & !(align - 1))
        .ok_or("aligned address overflow")
}