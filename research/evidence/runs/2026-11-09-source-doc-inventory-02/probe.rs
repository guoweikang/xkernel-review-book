use std::io::{self, Read};

use proc_macro2::Span;
use serde_json::{json, Value};
use syn::{spanned::Spanned, visit::Visit};

fn range(span: Span) -> Value {
    let bytes = span.byte_range();
    json!([bytes.start, bytes.end])
}

fn attribute_record(attribute: &syn::Attribute) -> Value {
    let doc_text = if attribute.path().is_ident("doc") {
        match &attribute.meta {
            syn::Meta::NameValue(value) => match &value.value {
                syn::Expr::Lit(literal) => match &literal.lit {
                    syn::Lit::Str(text) => Some(text.value()),
                    _ => None,
                },
                _ => None,
            },
            _ => None,
        }
    } else {
        None
    };
    json!({"path": attribute.path().segments.iter()
        .map(|segment| segment.ident.to_string()).collect::<Vec<_>>().join("::"),
        "range": range(attribute.span()), "doc_text": doc_text,
        "style": match attribute.style {
            syn::AttrStyle::Outer => "outer",
            syn::AttrStyle::Inner(_) => "inner",
        }})
}

#[derive(Default)]
struct Collector {
    units: Vec<Value>,
    ancestors: Vec<usize>,
}

impl Collector {
    fn enter(&mut self, kind: &str, name: Option<String>, span: Span) {
        let index = self.units.len();
        self.units.push(json!({
            "kind": kind, "name": name, "range": range(span),
            "ancestors": self.ancestors, "attributes": [],
        }));
        self.ancestors.push(index);
    }

    fn attributes(&mut self, attributes: &[syn::Attribute]) {
        let index = *self.ancestors.last().unwrap();
        self.units[index]["attributes"] = json!(attributes
            .iter()
            .map(attribute_record)
            .collect::<Vec<_>>());
    }

    fn function(&mut self, signature: &syn::Signature, body: Option<&syn::Block>) {
        let unit = &mut self.units[*self.ancestors.last().unwrap()];
        unit["signature_range"] = range(signature.span());
        unit["body_range"] = body.map(|block| range(block.span())).unwrap_or(Value::Null);
    }
}

impl<'ast> Visit<'ast> for Collector {
    fn visit_item(&mut self, item: &'ast syn::Item) {
        if let syn::Item::Verbatim(tokens) = item {
            self.enter("verbatim_item", None, tokens.span());
            self.ancestors.pop();
        }
        syn::visit::visit_item(self, item);
    }

    fn visit_item_fn(&mut self, item: &'ast syn::ItemFn) {
        self.enter("fn", Some(item.sig.ident.to_string()), item.span());
        self.attributes(&item.attrs);
        self.function(&item.sig, Some(&item.block));
        syn::visit::visit_item_fn(self, item);
        self.ancestors.pop();
    }

    fn visit_impl_item_fn(&mut self, item: &'ast syn::ImplItemFn) {
        self.enter("impl_fn", Some(item.sig.ident.to_string()), item.span());
        self.attributes(&item.attrs);
        self.function(&item.sig, Some(&item.block));
        syn::visit::visit_impl_item_fn(self, item);
        self.ancestors.pop();
    }

    fn visit_trait_item_fn(&mut self, item: &'ast syn::TraitItemFn) {
        self.enter("trait_fn", Some(item.sig.ident.to_string()), item.span());
        self.attributes(&item.attrs);
        self.function(&item.sig, item.default.as_ref());
        syn::visit::visit_trait_item_fn(self, item);
        self.ancestors.pop();
    }

    fn visit_item_impl(&mut self, item: &'ast syn::ItemImpl) {
        self.enter("impl", None, item.span());
        self.attributes(&item.attrs);
        syn::visit::visit_item_impl(self, item);
        self.ancestors.pop();
    }

    fn visit_item_trait(&mut self, item: &'ast syn::ItemTrait) {
        self.enter("trait", Some(item.ident.to_string()), item.span());
        self.attributes(&item.attrs);
        syn::visit::visit_item_trait(self, item);
        self.ancestors.pop();
    }

    fn visit_item_mod(&mut self, item: &'ast syn::ItemMod) {
        self.enter("mod", Some(item.ident.to_string()), item.span());
        self.attributes(&item.attrs);
        let index = *self.ancestors.last().unwrap();
        self.units[index]["inline"] = json!(item.content.is_some());
        self.units[index]["path_overrides"] = json!(item
            .attrs
            .iter()
            .filter(|attribute| attribute.path().is_ident("path"))
            .map(|attribute| match &attribute.meta {
                syn::Meta::NameValue(value) => match &value.value {
                    syn::Expr::Lit(literal) => match &literal.lit {
                        syn::Lit::Str(text) => Some(text.value()),
                        _ => None,
                    },
                    _ => None,
                },
                _ => None,
            })
            .collect::<Vec<_>>());
        syn::visit::visit_item_mod(self, item);
        self.ancestors.pop();
    }

    fn visit_macro(&mut self, item: &'ast syn::Macro) {
        self.enter("macro_tokens", None, item.span());
        syn::visit::visit_macro(self, item);
        self.ancestors.pop();
    }

    fn visit_expr_closure(&mut self, item: &'ast syn::ExprClosure) {
        self.enter("closure", None, item.span());
        self.attributes(&item.attrs);
        syn::visit::visit_expr_closure(self, item);
        self.ancestors.pop();
    }

    fn visit_item_struct(&mut self, item: &'ast syn::ItemStruct) {
        self.enter("struct", Some(item.ident.to_string()), item.span());
        self.attributes(&item.attrs);
        syn::visit::visit_item_struct(self, item);
        self.ancestors.pop();
    }

    fn visit_item_enum(&mut self, item: &'ast syn::ItemEnum) {
        self.enter("enum", Some(item.ident.to_string()), item.span());
        self.attributes(&item.attrs);
        syn::visit::visit_item_enum(self, item);
        self.ancestors.pop();
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut source = String::new();
    io::stdin().read_to_string(&mut source)?;
    if source.starts_with('\u{feff}') || (source.starts_with("#!") && !source.starts_with("#![")) {
        println!(
            "{}",
            json!({"schema": "syn-unit-probe/2", "status": "unsupported_prefix",
            "units": [], "diagnostics": [{"message": "BOM/shebang offset mapping not implemented"}]})
        );
        return Ok(());
    }
    let output = match syn::parse_file(&source) {
        Ok(file) => {
            let mut collector = Collector::default();
            collector.visit_file(&file);
            let attributes: Vec<_> = file
                .attrs
                .iter()
                .map(attribute_record)
                .collect();
            json!({"schema": "syn-unit-probe/2", "status": "parsed_by_syn",
                   "units": collector.units, "file_attributes": attributes, "diagnostics": []})
        }
        Err(error) => {
            let diagnostics: Vec<_> = error
                .into_iter()
                .map(|error| json!({"message": error.to_string(), "range": range(error.span())}))
                .collect();
            json!({"schema": "syn-unit-probe/2", "status": "rejected_by_syn",
                   "units": [], "diagnostics": diagnostics})
        }
    };
    println!("{}", serde_json::to_string(&output)?);
    Ok(())
}
