use std::io::{self, BufRead};

include!("original.rs");

struct CandidatePathname<'a> { inner: &'a str }

impl<'a> CandidatePathname<'a> {
    pub fn new(input: &'a str) -> Self { Self { inner: input } }
    pub fn as_str(&self) -> &'a str { self.inner }
    pub fn file_name(&self) -> Option<&'a str> {
        let (start, end) = scan(self.inner)?;
        match &self.inner[start..end] {
            "." | ".." => None,
            name => Some(name),
        }
    }
    pub fn parent(&self) -> Option<CandidatePathname<'a>> {
        let (start, _) = scan(self.inner)?;
        let parent_end = if start == 0 { 0 } else if start == 1 { 1 } else { start - 1 };
        Some(Self::new(&self.inner[..parent_end]))
    }
}

fn scan(input: &str) -> Option<(usize, usize)> {
    let mut end = input.len();
    loop {
        while end > 0 && input.as_bytes()[end - 1] == b'/' {
            end -= 1;
        }
        if end == 0 {
            return None;
        }
        let start = input[..end].rfind('/').map(|index| index + 1).unwrap_or(0);
        if &input[start..end] == "." && start > 0 {
            end = start - 1;
            continue;
        }
        return Some((start, end));
    }
}

fn candidate(input: &str, variant: usize) -> (Option<&str>, Option<&str>) {
    let Some((start, end)) = scan(input) else { return (None, None) };
    assert!(start <= end && end <= input.len());
    let name = &input[start..end];
    let file = match name { "." | ".." => None, _ => Some(name) };
    if variant == 1 && (name == "." || name == "..") {
        return (None, None);
    }
    let parent_end = if start == 0 { 0 } else if start == 1 { 1 } else { start - 1 };
    let parent = &input[..parent_end];
    let parent = if variant == 2 { parent.trim_end_matches('/') } else { parent };
    (file, Some(parent))
}

fn signature(input: &str, output: Option<&str>) -> String {
    match output {
        None => "none".into(),
        Some(value) => {
            let start = (value.as_ptr() as usize).checked_sub(input.as_ptr() as usize).unwrap();
            let end = start + value.len();
            assert!(end <= input.len() && input.is_char_boundary(start) && input.is_char_boundary(end));
            assert_eq!(&input[start..end], value);
            format!("{start}:{end}")
        }
    }
}

fn main() {
    for (input, expected) in [("../a/b/c", Some("c")), ("a/b/.", Some("b")), ("a/..", None)] {
        assert_eq!(Pathname::new(input).file_name(), expected);
        assert_eq!(CandidatePathname::new(input).file_name(), expected);
    }
    for (index, line) in io::stdin().lock().lines().enumerate() {
        let line = line.unwrap();
        let bytes: Vec<u8> = (0..line.len()).step_by(2)
            .map(|offset| u8::from_str_radix(&line[offset..offset + 2], 16).unwrap()).collect();
        let input = String::from_utf8(bytes).unwrap();
        let path = Pathname::new(&input);
        let reference = (path.file_name(), path.parent().map(|parent| parent.as_str()));
        let expected = (signature(&input, reference.0), signature(&input, reference.1));
        let mut differences = Vec::new();
        for variant in 0..3 {
            let result = if variant == 0 {
                let path = CandidatePathname::new(&input);
                (path.file_name(), path.parent().map(|parent| parent.as_str()))
            } else {
                candidate(&input, variant)
            };
            let actual = (signature(&input, result.0), signature(&input, result.1));
            differences.push(if expected == actual { "0" } else { "1" });
        }
        println!("{index}\t{}\t{}\t{}", expected.0, expected.1, differences.join("\t"));
    }
}
