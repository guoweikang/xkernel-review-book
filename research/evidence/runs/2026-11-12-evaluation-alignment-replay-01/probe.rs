mod cpu_original {
pub(crate) fn align_up(value: usize, align: usize) -> Option<usize> {
    debug_assert!(align.is_power_of_two());
    value
        .checked_add(align - 1)
        .map(|value| value & !(align - 1))
}
}
mod cpu_candidate {
pub(crate) fn align_up(value: usize, align: usize) -> Option<usize> {
    debug_assert!(align.is_power_of_two());
    value.checked_next_multiple_of(align)
}
}
mod boot_original {
pub(crate) fn align_up(value: u64, align: u64) -> Result<u64, &'static str> {
    if align == 0 || !align.is_power_of_two() {
        return Err("invalid alignment");
    }
    value
        .checked_add(align - 1)
        .map(|value| value & !(align - 1))
        .ok_or("aligned address overflow")
}
}
mod boot_candidate {
pub(crate) fn align_up(value: u64, align: u64) -> Result<u64, &'static str> {
    if align == 0 || !align.is_power_of_two() {
        return Err("invalid alignment");
    }
    value.checked_next_multiple_of(align)
        .ok_or("aligned address overflow")
}
}
mod host_original {
pub(crate) fn align_up(value: usize, alignment: usize) -> Option<usize> {
    value
        .checked_add(alignment - 1)
        .map(|value| value & !(alignment - 1))
}
}
mod host_candidate {
pub(crate) fn align_up(value: usize, alignment: usize) -> Option<usize> {
    value.checked_next_multiple_of(alignment)
}
}
#[test]
fn usize_power_two_domain() {
    for shift in 0..usize::BITS {
        let alignment = 1usize << shift;
        let top = usize::MAX & !(alignment - 1);
        let mut values: Vec<usize> = (0..4096).collect();
        values.extend((0..128).map(|delta| usize::MAX - delta));
        values.extend([alignment - 1, alignment, top, top - 1]);
        if let Some(next) = top.checked_add(1) {
            values.push(next);
        }
        for value in values {
            assert_eq!(cpu_original::align_up(value, alignment), cpu_candidate::align_up(value, alignment));
            assert_eq!(host_original::align_up(value, alignment), host_candidate::align_up(value, alignment));
        }
    }
}

#[test]
fn u64_power_two_domain() {
    for shift in 0..u64::BITS {
        let alignment = 1u64 << shift;
        let top = u64::MAX & !(alignment - 1);
        let mut values: Vec<u64> = (0..4096).collect();
        values.extend((0..128).map(|delta| u64::MAX - delta));
        values.extend([alignment - 1, alignment, top, top - 1]);
        if let Some(next) = top.checked_add(1) {
            values.push(next);
        }
        for value in values {
            assert_eq!(boot_original::align_up(value, alignment), boot_candidate::align_up(value, alignment));
        }
    }
}

#[test]
fn boot_invalid_alignment_errors_preserved() {
    for alignment in [0, 3, 5, 6, 7, u64::MAX] {
        for value in [0, 1, 17, u64::MAX] {
            assert_eq!(boot_original::align_up(value, alignment), Err("invalid alignment"));
            assert_eq!(boot_candidate::align_up(value, alignment), Err("invalid alignment"));
        }
    }
}

#[test]
fn unguarded_core_is_not_boot_contract() {
    assert_eq!(boot_original::align_up(17, 3), Err("invalid alignment"));
    assert_eq!(17u64.checked_next_multiple_of(3), Some(18));
    assert_eq!(boot_candidate::align_up(u64::MAX, 4), Err("aligned address overflow"));
}
