use std::cell::RefCell;
use std::rc::Rc;

struct Probe {
    values: Vec<Option<i32>>,
    position: usize,
    trace: Rc<RefCell<Vec<Option<i32>>>>,
}

impl Iterator for Probe {
    type Item = i32;

    fn next(&mut self) -> Option<i32> {
        let value = self.values.get(self.position).copied().flatten();
        self.position += 1;
        self.trace.borrow_mut().push(value);
        value
    }
}

fn scan_nth<Iter: Iterator>(iterator: &mut Iter, count: usize) -> Option<Iter::Item> {
    for _ in 0..count {
        iterator.next()?;
    }
    iterator.next()
}

fn render(value: Option<i32>) -> String {
    value.map_or("null".to_owned(), |number| number.to_string())
}

fn main() {
    for scenario in ["resumable", "finite"] {
        for arm in ["original", "scan"] {
            let values = if scenario == "resumable" {
                vec![None, Some(10), Some(20)]
            } else {
                vec![Some(10), Some(20), Some(30)]
            };
            let trace = Rc::new(RefCell::new(Vec::new()));
            let probe = Probe { values, position: 0, trace: Rc::clone(&trace) };
            let mut adapter = probe.take(2);
            let first = if arm == "original" { adapter.nth(1) } else { scan_nth(&mut adapter, 1) };
            let follow_up = adapter.next();
            let expected_first = if scenario == "finite" { Some(20) } else { None };
            let expected_follow = if scenario == "resumable" && arm == "scan" { Some(10) } else { None };
            assert_eq!(first, expected_first);
            assert_eq!(follow_up, expected_follow);
            let observed = trace.borrow().iter().copied().map(render).collect::<Vec<_>>().join(",");
            println!("{{\"scenario\":\"{scenario}\",\"arm\":\"{arm}\",\"first\":{},\"follow_up\":{},\"trace\":[{observed}]}}", render(first), render(follow_up));
        }
    }
}
