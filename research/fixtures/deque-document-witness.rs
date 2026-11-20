use std::collections::VecDeque;

fn main() {
    for direction in ["front", "back"] {
        for length in [0, 1, 3] {
            for accept in [false, true] {
                let initial = vec![10, 20, 30][..length].to_vec();
                let mut deque: VecDeque<i32> = initial.iter().copied().collect();
                let mut calls = 0;
                let predicate = |value: &mut i32| {
                    calls += 1;
                    *value += 100;
                    accept
                };
                let returned = if direction == "front" {
                    deque.pop_front_if(predicate)
                } else {
                    deque.pop_back_if(predicate)
                };
                let remaining: Vec<i32> = deque.into_iter().collect();
                let mut expected = initial.clone();
                let expected_return = if length == 0 {
                    None
                } else {
                    let endpoint = if direction == "front" { 0 } else { length - 1 };
                    expected[endpoint] += 100;
                    if accept { Some(expected.remove(endpoint)) } else { None }
                };
                assert_eq!(calls, usize::from(length != 0));
                assert_eq!(returned, expected_return);
                assert_eq!(remaining, expected);
                let output = returned.map_or("null".to_owned(), |value| value.to_string());
                println!("{{\"direction\":\"{direction}\",\"length\":{length},\"accept\":{accept},\"calls\":{calls},\"returned\":{output},\"initial\":{initial:?},\"remaining\":{remaining:?}}}");
            }
        }
    }
}
