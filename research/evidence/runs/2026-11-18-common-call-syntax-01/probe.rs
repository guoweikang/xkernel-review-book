use std::io::{self, Read};

use serde_json::{Value, json};
use syn::{spanned::Spanned, visit::Visit};

#[derive(Default)]
struct Calls {
    sites: Vec<Value>,
    deferred_depth: usize,
}

impl Calls {
    fn record(&mut self, kind: &str, name: Option<String>, span: proc_macro2::Span) {
        let bytes = span.byte_range();
        self.sites.push(json!({
            "kind": kind, "name": name, "range": [bytes.start, bytes.end],
            "deferred_depth": self.deferred_depth, "target_resolution": "unresolved",
            "cfg": "not_evaluated", "execution": "not_established"
        }));
    }
}

impl<'ast> Visit<'ast> for Calls {
    fn visit_expr_call(&mut self, expression: &'ast syn::ExprCall) {
        let name = match expression.func.as_ref() {
            syn::Expr::Path(path) => Some(path.path.segments.iter()
                .map(|segment| segment.ident.to_string()).collect::<Vec<_>>().join("::")),
            _ => None,
        };
        self.record("call_expression", name, expression.func.span());
        syn::visit::visit_expr_call(self, expression);
    }

    fn visit_expr_method_call(&mut self, expression: &'ast syn::ExprMethodCall) {
        self.record("method_expression", Some(expression.method.to_string()), expression.method.span());
        syn::visit::visit_expr_method_call(self, expression);
    }

    fn visit_macro(&mut self, expression: &'ast syn::Macro) {
        self.record("opaque_macro", Some(expression.path.segments.iter()
            .map(|segment| segment.ident.to_string()).collect::<Vec<_>>().join("::")), expression.span());
    }

    fn visit_expr_closure(&mut self, expression: &'ast syn::ExprClosure) {
        self.deferred_depth += 1;
        syn::visit::visit_expr_closure(self, expression);
        self.deferred_depth -= 1;
    }

    fn visit_expr_async(&mut self, expression: &'ast syn::ExprAsync) {
        self.deferred_depth += 1;
        syn::visit::visit_expr_async(self, expression);
        self.deferred_depth -= 1;
    }

    fn visit_item(&mut self, item: &'ast syn::Item) {
        self.deferred_depth += 1;
        syn::visit::visit_item(self, item);
        self.deferred_depth -= 1;
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut source = String::new();
    io::stdin().read_to_string(&mut source)?;
    let result = match syn::parse_str::<syn::ImplItemFn>(&source) {
        Ok(function) => {
            let mut calls = Calls::default();
            calls.visit_block(&function.block);
            calls.sites.sort_by_key(|site| site["range"][0].as_u64());
            json!({"schema": "rust-call-syntax/1", "status": "parsed", "sites": calls.sites})
        }
        Err(error) => json!({"schema": "rust-call-syntax/1", "status": "rejected", "sites": [], "error": error.to_string()}),
    };
    println!("{result}");
    Ok(())
}
