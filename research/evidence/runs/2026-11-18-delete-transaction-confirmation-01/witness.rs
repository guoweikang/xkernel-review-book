use std::cell::RefCell;
use std::rc::Rc;

type Trace = Rc<RefCell<Vec<&'static str>>>;

fn event(trace: &Trace, name: &'static str) {
    trace.borrow_mut().push(name);
}

struct Guard {
    trace: Trace,
    release: &'static str,
}

impl Guard {
    fn acquire(trace: &Trace, acquire: &'static str, release: &'static str) -> Self {
        event(trace, acquire);
        Self { trace: trace.clone(), release }
    }
}

impl Drop for Guard {
    fn drop(&mut self) {
        event(&self.trace, self.release);
    }
}

struct Capture(Trace);

impl Drop for Capture {
    fn drop(&mut self) {
        event(&self.0, "may_drop");
    }
}

#[derive(Clone, Copy, PartialEq)]
enum Condition { TypeMismatch, CallbackError, Success }

fn original<F: FnOnce() -> Result<(), &'static str>>(trace: &Trace, condition: Condition, may: F) -> Result<(), &'static str> {
    let _parent = Guard::acquire(trace, "parent_lock", "parent_unlock");
    let _victim = Guard::acquire(trace, "victim_lock", "victim_unlock");
    event(trace, "type_check");
    if condition == Condition::TypeMismatch { return Err("WrongType"); }
    may()?;
    event(trace, "backend");
    event(trace, "mark");
    event(trace, "forget");
    Ok(())
}

fn helper<F: FnOnce() -> Result<(), &'static str>>(trace: &Trace, operation: F) -> Result<(), &'static str> {
    let _parent = Guard::acquire(trace, "parent_lock", "parent_unlock");
    let _victim = Guard::acquire(trace, "victim_lock", "victim_unlock");
    operation()?;
    event(trace, "mark");
    event(trace, "forget");
    Ok(())
}

fn naive<F: FnOnce() -> Result<(), &'static str>>(trace: &Trace, condition: Condition, may: F) -> Result<(), &'static str> {
    helper(trace, move || {
        event(trace, "type_check");
        if condition == Condition::TypeMismatch { return Err("WrongType"); }
        may()?;
        event(trace, "backend");
        Ok(())
    })
}

fn main() {
    for (name, condition) in [("type_mismatch", Condition::TypeMismatch), ("callback_error", Condition::CallbackError), ("success", Condition::Success)] {
        for variant in ["original", "naive"] {
            let trace = Trace::default();
            let capture = Capture(trace.clone());
            let callback_trace = trace.clone();
            let may = move || {
                std::hint::black_box(&capture);
                event(&callback_trace, "may_call");
                if condition == Condition::CallbackError { Err("PermissionDenied") } else { Ok(()) }
            };
            let result = if variant == "original" { original(&trace, condition, may) } else { naive(&trace, condition, may) };
            let outcome = match result { Ok(()) => "Ok", Err(error) => error };
            println!("{}\t{}\t{}\t{}", name, variant, outcome, trace.borrow().join(","));
        }
    }
}
