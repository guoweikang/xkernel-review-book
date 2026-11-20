extern crate alloc;
use std::{cell::RefCell, collections::VecDeque, marker::PhantomData, rc::Rc};

#[derive(Debug, Clone, Copy, PartialEq)]
enum VfsError { BadAddress, FileTooLarge, InvalidData, WriteZero }
type VfsResult<T> = Result<T, VfsError>;
mod memaddr { pub const PAGE_SIZE_4K: usize = 4096; }
struct VfsFile;
struct Kiocb<'a> { position: u64, file: &'a VfsFile }
impl Kiocb<'_> {
    fn file(&self) -> &VfsFile { self.file }
    fn ki_pos(&self) -> u64 { self.position }
    fn advance(&mut self, amount: usize) { self.position += amount as u64; }
}
type Trace = Rc<RefCell<Vec<String>>>;
struct IovIterSource<'a> {
    payload: Vec<u8>, cursor: usize, plan: VecDeque<VfsResult<usize>>,
    trace: Trace, marker: PhantomData<&'a ()>,
}
impl IovIterSource<'_> {
    fn count(&self) -> usize { self.payload.len() - self.cursor }
    fn copy_from_iter(&mut self, output: &mut [u8]) -> VfsResult<usize> {
        let limit = output.len().min(self.count());
        if limit == 0 { return Ok(0); }
        match self.plan.pop_front().unwrap_or(Ok(limit)) {
            Ok(requested) => {
                let count = requested.min(limit);
                output[..count].copy_from_slice(&self.payload[self.cursor..self.cursor + count]);
                self.cursor += count;
                self.trace.borrow_mut().push(format!("copy:{count}"));
                Ok(count)
            }
            Err(error) => {
                self.trace.borrow_mut().push("copy:BadAddress:no_cursor_effect".into());
                Err(error)
            }
        }
    }
    fn revert(&mut self, count: usize) -> VfsResult<()> {
        assert!(count <= self.cursor);
        self.cursor -= count;
        self.trace.borrow_mut().push(format!("rewind:{count}"));
        Ok(())
    }
}

fn scalar_write_iter(
    iocb: &mut Kiocb<'_>,
    iter: &mut IovIterSource<'_>,
    mut write: impl FnMut(&VfsFile, &[u8], u64) -> VfsResult<usize>,
) -> VfsResult<usize> {
    let mut total = 0usize;
    let mut chunk = [0u8; memaddr::PAGE_SIZE_4K];
    while iter.count() != 0 {
        let want = chunk.len().min(iter.count());
        let copied = match iter.copy_from_iter(&mut chunk[..want]) {
            Ok(copied) => copied,
            Err(_) if total != 0 => break,
            Err(error) => return Err(error),
        };
        if copied == 0 {
            break;
        }
        let written = match write(iocb.file(), &chunk[..copied], iocb.ki_pos()) {
            Ok(written) => written,
            Err(error) => {
                iter.revert(copied)?;
                if total != 0 {
                    break;
                }
                return Err(error);
            }
        };
        if written > copied {
            iter.revert(copied)?;
            return Err(VfsError::InvalidData);
        }
        iter.revert(copied - written)?;
        if written == 0 {
            if total != 0 {
                break;
            }
            return Err(VfsError::WriteZero);
        }
        total += written;
        iocb.advance(written);
        if written < copied {
            break;
        }
    }
    Ok(total)
}

struct Command { trace: Trace, calls: RefCell<Vec<(Vec<u8>, u64)>>, fail: bool }
impl Command {
    fn write(&self, _: &VfsFile, payload: &[u8], offset: u64) -> VfsResult<usize> {
        self.calls.borrow_mut().push((payload.to_vec(), offset));
        self.trace.borrow_mut().push(format!("callback:{}:{offset}", payload.len()));
        if self.fail { Err(VfsError::BadAddress) } else { Ok(payload.len()) }
    }
    fn write_iter(&self, iocb: &mut Kiocb<'_>, iter: &mut IovIterSource<'_>) -> VfsResult<usize> {
        const MAX_COMMAND_SIZE: usize = 4096;
        let count = iter.count();
        if count == 0 {
            return Ok(0);
        }
        if count > MAX_COMMAND_SIZE {
            return Err(VfsError::FileTooLarge);
        }
        let mut command = alloc::vec![0; count];
        let mut copied = 0;
        while copied < count {
            let read = match iter.copy_from_iter(&mut command[copied..]) {
                Ok(read) => read,
                Err(error) => {
                    iter.revert(copied)?;
                    return Err(error);
                }
            };
            if read == 0 {
                iter.revert(copied)?;
                return Err(VfsError::BadAddress);
            }
            copied += read;
        }
        let written = match self.write(iocb.file(), &command, iocb.ki_pos()) {
            Ok(written) => written,
            Err(error) => {
                iter.revert(count)?;
                return Err(error);
            }
        };
        if written > count {
            iter.revert(count)?;
            return Err(VfsError::InvalidData);
        }
        iter.revert(count - written)?;
        if written == 0 {
            return Err(VfsError::WriteZero);
        }
        iocb.advance(written);
        Ok(written)
    }
}

fn main() {
    for scenario in ["complete", "empty", "oversize", "short_success", "short_then_fault", "callback_fault"] {
        for adapter in ["scalar", "command"] {
            let length = match scenario { "empty" => 0, "oversize" => 4097, _ => 4 };
            let payload: Vec<u8> = (0..length).map(|index| (index % 251) as u8).collect();
            let plan = match scenario {
                "short_success" => vec![Ok(2), Ok(2)],
                "short_then_fault" => vec![Ok(2), Err(VfsError::BadAddress)],
                _ => vec![],
            };
            let trace = Rc::new(RefCell::new(Vec::new()));
            let mut iter = IovIterSource { payload, cursor: 0, plan: plan.into(), trace: trace.clone(), marker: PhantomData };
            let receiver = Command { trace: trace.clone(), calls: RefCell::new(Vec::new()), fail: scenario == "callback_fault" };
            let file = VfsFile;
            let mut iocb = Kiocb { position: 100, file: &file };
            let result = if adapter == "scalar" {
                scalar_write_iter(&mut iocb, &mut iter, |file, data, offset| receiver.write(file, data, offset))
            } else { receiver.write_iter(&mut iocb, &mut iter) };
            let calls = receiver.calls.borrow();
            let calls_json = calls.iter().map(|(data, offset)| format!("{{\"payload\":{data:?},\"offset\":{offset}}}")).collect::<Vec<_>>().join(",");
            println!("{{\"scenario\":\"{scenario}\",\"adapter\":\"{adapter}\",\"result\":\"{result:?}\",\"remaining\":{},\"position\":{},\"calls\":[{}],\"trace\":{:?}}}", iter.count(), iocb.position, calls_json, trace.borrow());
        }
    }
}
