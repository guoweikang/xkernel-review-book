use std::io::{self, Read};

use proc_macro2::{Delimiter, Spacing, TokenStream, TokenTree};
use serde_json::json;

fn flatten(stream: TokenStream, output: &mut Vec<String>) {
    for token in stream {
        match token {
            TokenTree::Ident(identifier) => output.push(format!("ident:{identifier}")),
            TokenTree::Literal(literal) => output.push(format!("literal:{literal}")),
            TokenTree::Punct(punctuation) => {
                let spacing = match punctuation.spacing() {
                    Spacing::Joint => "joint",
                    Spacing::Alone => "alone",
                };
                output.push(format!("punct:{}:{spacing}", punctuation.as_char()));
            }
            TokenTree::Group(group) => {
                let delimiter = match group.delimiter() {
                    Delimiter::Parenthesis => "paren",
                    Delimiter::Brace => "brace",
                    Delimiter::Bracket => "bracket",
                    Delimiter::None => "none",
                };
                output.push(format!("open:{delimiter}"));
                flatten(group.stream(), output);
                output.push(format!("close:{delimiter}"));
            }
        }
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut source = String::new();
    io::stdin().read_to_string(&mut source)?;
    let result = match source.parse::<TokenStream>() {
        Ok(stream) => {
            let mut tokens = Vec::new();
            flatten(stream, &mut tokens);
            json!({"schema": "rust-token-probe/1", "status": "tokenized", "tokens": tokens})
        }
        Err(error) => json!({"schema": "rust-token-probe/1", "status": "rejected",
                             "tokens": [], "error": error.to_string()}),
    };
    println!("{result}");
    Ok(())
}
