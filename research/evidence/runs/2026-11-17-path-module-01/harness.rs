extern crate alloc;
#[path = "original/src/path.rs"]
mod original;
#[path = "candidate/src/path.rs"]
mod candidate;
mod original_ut { include!("original/ut-adapted.rs"); }
mod candidate_ut { include!("candidate/ut-adapted.rs"); }

#[test]
fn differential_callers() {
    let mut count = 0;
    for (index, line) in include_str!("inputs.hex").lines().enumerate() {
        let bytes: Vec<u8> = (0..line.len()).step_by(2)
            .map(|offset| u8::from_str_radix(&line[offset..offset + 2], 16).unwrap()).collect();
        let input = String::from_utf8(bytes).unwrap();
        let before = original::Pathname::new(&input);
        let after = candidate::Pathname::new(&input);
        assert_eq!(before.file_name(), after.file_name(), "file input {index}");
        assert_eq!(before.parent().map(|value| value.as_str()), after.parent().map(|value| value.as_str()), "parent input {index}");
        let normalized_before = before.normalize().map(|value| value.as_str().to_owned());
        let normalized_after = after.normalize().map(|value| value.as_str().to_owned());
        assert_eq!(normalized_before, normalized_after, "normalize input {index}");
        let mut buffer_before = original::PathBuf::from(input.as_str());
        let mut buffer_after = candidate::PathBuf::from(input.as_str());
        let mut trace = Vec::new();
        let mut terminated = false;
        for _step in 0..=input.len() + 1 {
            let popped_before = buffer_before.pop();
            let popped_after = buffer_after.pop();
            assert_eq!(popped_before, popped_after, "pop bool input {index}");
            assert_eq!(buffer_before.as_str(), buffer_after.as_str(), "pop state input {index}");
            trace.push((popped_before, buffer_before.as_str().to_owned()));
            if !popped_before {
                terminated = true;
                break;
            }
        }
        assert!(terminated, "pop did not terminate for input {index}");
        println!("CASE {index}\t{normalized_before:?}\t{trace:?}");
        count += 1;
    }
    assert_eq!(count, 37459);
}
