use std::sync::{Arc, Mutex};

type Trace = Arc<Mutex<Vec<&'static str>>>;

struct Payload(Trace);

impl Drop for Payload {
    fn drop(&mut self) {
        self.0.lock().unwrap().push("drop-payload");
    }
}

fn observe_edge(covers: &Mutex<Option<Payload>>, trace: &Trace) {
    trace.lock().unwrap().push(if covers.try_lock().is_ok() {
        "edge-covers-unlocked"
    } else {
        "edge-covers-locked"
    });
}

fn inline_form(covers: &Mutex<Option<Payload>>, trace: &Trace) {
    let covered = covers.lock().unwrap().take();
    match covered {
        Some(ref _mount) => observe_edge(covers, trace),
        None => observe_edge(covers, trace),
    }
    trace.lock().unwrap().push("detach");
}

fn helper_form(covers: &Mutex<Option<Payload>>, trace: &Trace) {
    match covers.lock().unwrap().take() {
        Some(_mount) => observe_edge(covers, trace),
        None => observe_edge(covers, trace),
    }
    trace.lock().unwrap().push("detach");
}

fn main() {
    for present in [false, true] {
        for helper in [false, true] {
            let trace = Arc::new(Mutex::new(Vec::new()));
            let covers = Mutex::new(present.then(|| Payload(trace.clone())));
            if helper {
                helper_form(&covers, &trace);
            } else {
                inline_form(&covers, &trace);
            }
            let expected = match (helper, present) {
                (false, false) => vec!["edge-covers-unlocked", "detach"],
                (false, true) => vec!["edge-covers-unlocked", "detach", "drop-payload"],
                (true, false) => vec!["edge-covers-locked", "detach"],
                (true, true) => vec!["edge-covers-locked", "drop-payload", "detach"],
            };
            assert_eq!(*trace.lock().unwrap(), expected);
            println!("helper={helper} present={present}: {expected:?}");
        }
    }
    println!("PASS: four compiler-scope observations; not a kernel test or deadlock proof");
}
