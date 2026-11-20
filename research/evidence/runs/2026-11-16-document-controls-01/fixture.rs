fn unit_01(value: u16) -> u16 { if value > 63 { 63 } else { value } }
fn unit_02(value: u16) -> u16 { let mut result = 0; while result < value && result < 63 { result += 1; } result }
fn unit_03(value: u16) -> u16 { value & 15 }
fn unit_04(value: u16) -> u16 { let mut remaining = value; while remaining >= 16 { remaining -= 16; } remaining }
fn unit_05(value: u16) -> u16 { value >> 4 }
fn unit_06(value: u16) -> u16 { let mut remaining = value; let mut count = 0; while remaining >= 16 { remaining -= 16; count += 1; } count }
fn unit_07(value: u16) -> u16 { value & 240 }
fn unit_08(value: u16) -> u16 { if value >= 16 { 1 } else { 0 } }
fn main() { for value in 0..=255u16 {
println!("unit_01,{},{}", value, unit_01(value));
println!("unit_02,{},{}", value, unit_02(value));
println!("unit_03,{},{}", value, unit_03(value));
println!("unit_04,{},{}", value, unit_04(value));
println!("unit_05,{},{}", value, unit_05(value));
println!("unit_06,{},{}", value, unit_06(value));
println!("unit_07,{},{}", value, unit_07(value));
println!("unit_08,{},{}", value, unit_08(value));
} }
