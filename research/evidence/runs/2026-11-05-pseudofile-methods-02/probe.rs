use std::cell::RefCell;
use std::rc::Rc;

type VfsResult<Value> = Result<Value, &'static str>;
type Events = Rc<RefCell<Vec<String>>>;
struct VfsFile;
enum SimpleFileOperation<'source> {
    Write { file: &'source VfsFile, data: &'source [u8] },
}

struct ControlledOps {
    events: Events,
    fail_read: bool,
}

impl ControlledOps {
    fn read_all(&self) -> VfsResult<Vec<u8>> {
        self.events.borrow_mut().push("read".into());
        if self.fail_read {
            Err("read_failure")
        } else {
            Ok(b"abcdef".to_vec())
        }
    }

    fn write_all(&self, data: &[u8]) -> VfsResult<()> {
        self.events.borrow_mut().push(format!("write:{}", String::from_utf8_lossy(data)));
        Ok(())
    }
}

struct StarryFile { ops: ControlledOps }
impl StarryFile {
    fn write_at(&self, buf: &[u8], offset: u64) -> VfsResult<usize> {
        let data = self.ops.read_all()?;
        if offset == 0 && buf.len() >= data.len() {
            self.ops.write_all(buf)?;
            return Ok(buf.len());
        }
        let mut data = data.to_vec();
        let end_pos = offset + buf.len() as u64;
        if end_pos > data.len() as u64 {
            data.resize(end_pos as usize, 0);
        }
        data[offset as usize..end_pos as usize].copy_from_slice(buf);
        self.ops.write_all(&data)?;
        Ok(buf.len())
    }


}

struct CommandFile<Callback>(Callback);
impl<Callback> CommandFile<Callback>
where Callback: Fn(SimpleFileOperation<'_>) -> VfsResult<Option<Vec<u8>>> {
    fn write(&self, file: &VfsFile, data: &[u8], _offset: u64) -> VfsResult<usize> {
        (self.0)(SimpleFileOperation::Write { file, data })?;
        Ok(data.len())
    }


}

fn check_starry(fail_read: bool, offset: u64, expected: VfsResult<usize>, expected_events: &[&str]) {
    let events = Rc::new(RefCell::new(Vec::new()));
    let file = StarryFile { ops: ControlledOps { events: events.clone(), fail_read } };
    let result = file.write_at(b"XY", offset);
    println!("starry fail_read={fail_read} offset={offset} result={result:?} events={:?}", events.borrow());
    assert_eq!(result, expected);
    assert_eq!(*events.borrow(), expected_events);
}

fn check_xkernel(fail_read: bool, offset: u64) {
    let events = Rc::new(RefCell::new(Vec::new()));
    let ops = ControlledOps { events: events.clone(), fail_read };
    let handle = VfsFile;
    let command = CommandFile(|operation: SimpleFileOperation<'_>| {
        let SimpleFileOperation::Write { file, data } = operation;
        assert!(std::ptr::eq(file, &handle));
        ops.write_all(data)?;
        Ok(None::<Vec<u8>>)
    });
    let result = command.write(&handle, b"XY", offset);
    println!("xkernel unused_read_failure={fail_read} offset={offset} result={result:?} events={:?}", events.borrow());
    assert_eq!(result, Ok(2));
    assert_eq!(*events.borrow(), ["write:XY"]);
}

#[test]
fn pc01_starry_patches_old_content() {
    check_starry(false, 2, Ok(2), &["read", "write:abXYef"]);
}

#[test]
fn pc01_xkernel_delivers_one_command() {
    check_xkernel(false, 2);
}

#[test]
fn pc03_starry_stops_on_read_error() {
    check_starry(true, 0, Err("read_failure"), &["read"]);
}

#[test]
fn pc03_xkernel_does_not_read_old_content() {
    check_xkernel(true, 0);
}
