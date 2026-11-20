use std::collections::HashMap;
use std::io::{self, Read};
use proc_macro2::Span;
use serde_json::{json, Value};
use syn::{spanned::Spanned, Expr, FnArg, Pat, Stmt};

struct Frame {
    id: usize,
    names: HashMap<String, usize>,
    uncertain: bool,
}

struct Exporter<'source> {
    source: &'source str,
    nodes: Vec<Value>,
    scopes: Vec<Value>,
    frames: Vec<Frame>,
    binders: Vec<Value>,
    occurrences: Vec<Value>,
}

impl<'source> Exporter<'source> {
    fn scope(&mut self, kind: &str) -> usize {
        let id = self.scopes.len();
        self.scopes.push(json!({"scope_id": id, "parent_id": self.frames.last().map(|frame| frame.id), "kind": kind, "unknown_binding_effects": false}));
        self.frames.push(Frame { id, names: HashMap::new(), uncertain: false });
        id
    }

    fn node(&mut self, kind: &str, span: Span, parent: Option<usize>, role: &str) -> usize {
        let bytes = span.byte_range();
        let id = self.nodes.len();
        self.nodes.push(json!({"node_id": id, "syntax_kind": kind, "parent_id": parent,
            "ordered_children": [], "range": [bytes.start, bytes.end], "role": role,
            "scope_id": self.frames.last().map(|frame| frame.id), "coverage": "supported",
            "source_text": self.source.get(bytes).unwrap_or(""), "subtree_closed": false}));
        if let Some(parent) = parent {
            self.nodes[parent]["ordered_children"].as_array_mut().unwrap().push(json!(id));
        }
        id
    }

    fn opaque(&mut self, span: Span, parent: usize, role: &str, reason: &str, taint: bool) {
        let id = self.node("opaque", span, Some(parent), role);
        self.nodes[id]["coverage"] = json!("opaque");
        self.nodes[id]["reason"] = json!(reason);
        if taint {
            self.frames.last_mut().unwrap().uncertain = true;
            let scope = self.frames.last().unwrap().id;
            self.scopes[scope]["unknown_binding_effects"] = json!(true);
        }
    }

    fn name(&mut self, ident: &syn::Ident, parent: usize, role: &str, binder: bool, local: bool) {
        let id = self.node("identifier", ident.span(), Some(parent), role);
        let spelling = ident.to_string();
        let normalized = spelling.strip_prefix("r#").unwrap_or(&spelling).to_owned();
        let scope = self.frames.last().unwrap().id;
        let unknown = self.frames.iter().any(|frame| frame.uncertain);
        let candidate = if local && !unknown {
            self.frames.iter().rev().find_map(|frame| frame.names.get(&normalized).copied())
        } else { None };
        let status = if !local { "not_a_local_use" } else if unknown { "unknown_scope" }
            else if candidate.is_some() { "lexical_candidate" } else { "no_visible_lexical_binder" };
        self.occurrences.push(json!({"node_id": id, "scope_id": scope, "role": role,
            "spelling": spelling, "normalized_name": normalized, "binder_candidate": candidate,
            "candidate_status": status}));
        if binder {
            let binder_id = self.binders.len();
            self.binders.push(json!({"binder_id": binder_id, "node_id": id, "scope_id": scope,
                "spelling": spelling, "normalized_name": normalized}));
            self.frames.last_mut().unwrap().names.insert(normalized, binder_id);
        }
    }

    fn simple_pattern(pattern: &Pat) -> Option<&syn::PatIdent> {
        match pattern {
            Pat::Ident(pattern) if pattern.subpat.is_none() && pattern.attrs.is_empty() => Some(pattern),
            _ => None,
        }
    }

    fn block(&mut self, block: &syn::Block, parent: usize, role: &str) -> usize {
        self.scope("block");
        if block.stmts.iter().any(|statement| matches!(statement, Stmt::Item(_))) {
            self.frames.last_mut().unwrap().uncertain = true;
            let scope = self.frames.last().unwrap().id;
            self.scopes[scope]["unknown_binding_effects"] = json!(true);
        }
        let id = self.node("block", block.span(), Some(parent), role);
        for statement in &block.stmts {
            match statement {
                Stmt::Local(local) => {
                    let pattern = Self::simple_pattern(&local.pat);
                    if !local.attrs.is_empty() || pattern.is_none() || local.init.as_ref().is_some_and(|init| init.diverge.is_some()) {
                        self.opaque(local.span(), id, "statement", "unsupported_let_pattern_attributes_or_else", true);
                        continue;
                    }
                    let declaration = self.node("let", local.span(), Some(id), "statement");
                    if let Some(init) = &local.init { self.expr(&init.expr, declaration, "initializer"); }
                    let pattern = pattern.unwrap();
                    self.name(&pattern.ident, declaration, "let_binder", true, false);
                }
                Stmt::Expr(expression, _) => self.expr(expression, id, "statement"),
                Stmt::Macro(item) => self.opaque(item.span(), id, "statement", "opaque_statement_macro", true),
                Stmt::Item(item) => self.opaque(item.span(), id, "statement", "unsupported_nested_item", true),
            }
        }
        self.frames.pop();
        id
    }

    fn expr(&mut self, expression: &Expr, parent: usize, role: &str) {
        let (kind, attributes) = match expression {
            Expr::Path(value) => ("path", &value.attrs),
            Expr::Call(value) => ("call", &value.attrs),
            Expr::MethodCall(value) => ("method_call", &value.attrs),
            Expr::Lit(value) => ("literal", &value.attrs),
            Expr::Block(value) if value.label.is_none() => ("block_expression", &value.attrs),
            Expr::Paren(value) => ("paren", &value.attrs),
            Expr::Group(value) => ("group", &value.attrs),
            Expr::Binary(value) => ("binary", &value.attrs),
            Expr::Unary(value) => ("unary", &value.attrs),
            Expr::Assign(value) => ("assign", &value.attrs),
            Expr::Reference(value) => ("reference", &value.attrs),
            Expr::Field(value) => ("field", &value.attrs),
            Expr::Index(value) => ("index", &value.attrs),
            Expr::Tuple(value) => ("tuple", &value.attrs),
            Expr::Array(value) => ("array", &value.attrs),
            Expr::Return(value) => ("return", &value.attrs),
            _ => {
                let reason = match expression {
                    Expr::Closure(_) => "unsupported_closure",
                    Expr::Match(_) => "unsupported_match",
                    Expr::ForLoop(_) => "unsupported_for",
                    Expr::If(_) => "unsupported_if_including_if_let",
                    Expr::Macro(_) => "opaque_expression_macro",
                    Expr::Async(_) => "unsupported_async",
                    Expr::Unsafe(_) => "unsupported_unsafe",
                    Expr::Loop(_) => "unsupported_loop",
                    Expr::While(_) => "unsupported_while",
                    _ => "unsupported_expression_variant",
                };
                self.opaque(expression.span(), parent, role, reason, true);
                return;
            }
        };
        if !attributes.is_empty() {
            self.opaque(expression.span(), parent, role, "unevaluated_expression_attributes", true);
            return;
        }
        if let Expr::Path(path) = expression {
            if path.qself.is_some() || path.path.leading_colon.is_some() || path.path.segments.len() != 1
                || !matches!(path.path.segments[0].arguments, syn::PathArguments::None) {
                self.opaque(path.span(), parent, role, "unsupported_qualified_or_generic_path", false);
                return;
            }
        }
        let id = self.node(kind, expression.span(), Some(parent), role);
        match expression {
            Expr::Path(path) => self.name(&path.path.segments[0].ident, id, "local_use", false, true),
            Expr::Call(call) => {
                self.expr(&call.func, id, "callee");
                for argument in &call.args { self.expr(argument, id, "argument"); }
            }
            Expr::MethodCall(call) => {
                self.expr(&call.receiver, id, "receiver");
                self.name(&call.method, id, "method_name", false, false);
                if let Some(arguments) = &call.turbofish {
                    self.opaque(arguments.span(), id, "generic_arguments", "type_arguments_not_traversed", false);
                }
                for argument in &call.args { self.expr(argument, id, "argument"); }
            }
            Expr::Block(value) => { self.block(&value.block, id, "body"); }
            Expr::Paren(value) => self.expr(&value.expr, id, "operand"),
            Expr::Group(value) => self.expr(&value.expr, id, "operand"),
            Expr::Binary(value) => {
                self.expr(&value.left, id, "left");
                self.node("operator", value.op.span(), Some(id), "operator");
                self.expr(&value.right, id, "right");
            }
            Expr::Unary(value) => {
                self.node("operator", value.op.span(), Some(id), "operator");
                self.expr(&value.expr, id, "operand");
            }
            Expr::Assign(value) => {
                self.expr(&value.left, id, "left");
                self.node("operator", value.eq_token.span(), Some(id), "operator");
                self.expr(&value.right, id, "right");
            }
            Expr::Reference(value) => self.expr(&value.expr, id, "operand"),
            Expr::Field(value) => {
                self.expr(&value.base, id, "receiver");
                match &value.member {
                    syn::Member::Named(ident) => self.name(ident, id, "field_name", false, false),
                    syn::Member::Unnamed(index) => { self.node("field_index", index.span(), Some(id), "field_name"); }
                }
            }
            Expr::Index(value) => { self.expr(&value.expr, id, "receiver"); self.expr(&value.index, id, "index"); }
            Expr::Tuple(value) => { for element in &value.elems { self.expr(element, id, "element"); } }
            Expr::Array(value) => { for element in &value.elems { self.expr(element, id, "element"); } }
            Expr::Return(value) => { if let Some(value) = &value.expr { self.expr(value, id, "return_value"); } }
            Expr::Lit(_) => {}
            _ => unreachable!(),
        }
    }

    fn function(&mut self, function: &syn::ImplItemFn) -> Value {
        self.scope("function");
        let root = self.node("function", function.span(), None, "root");
        for attribute in &function.attrs {
            self.opaque(attribute.span(), root, "attribute", "unevaluated_function_attribute", true);
        }
        let signature = self.node("signature", function.sig.span(), Some(root), "signature");
        self.name(&function.sig.ident, signature, "function_name", false, false);
        if !function.sig.generics.params.is_empty() {
            self.opaque(function.sig.generics.span(), signature, "generics", "generics_not_traversed", false);
        }
        if let Some(clause) = &function.sig.generics.where_clause {
            self.opaque(clause.span(), signature, "where_clause", "where_clause_not_traversed", false);
        }
        for input in &function.sig.inputs {
            let parameter = self.node("parameter", input.span(), Some(signature), "parameter");
            match input {
                FnArg::Receiver(receiver) if receiver.attrs.is_empty() => {
                    self.name(&syn::Ident::new("self", receiver.self_token.span), parameter, "parameter_binder", true, false);
                    if receiver.colon_token.is_some() {
                        self.opaque(receiver.ty.span(), parameter, "type", "type_syntax_not_traversed", false);
                    }
                }
                FnArg::Typed(argument) if argument.attrs.is_empty() && Self::simple_pattern(&argument.pat).is_some() => {
                    self.name(&Self::simple_pattern(&argument.pat).unwrap().ident, parameter, "parameter_binder", true, false);
                    self.opaque(argument.ty.span(), parameter, "type", "type_syntax_not_traversed", false);
                }
                _ => self.opaque(input.span(), parameter, "pattern", "unsupported_parameter_pattern_or_attributes", true),
            }
        }
        if let syn::ReturnType::Type(_, output) = &function.sig.output {
            self.opaque(output.span(), signature, "return_type", "type_syntax_not_traversed", false);
        }
        if let Some(variadic) = &function.sig.variadic {
            self.opaque(variadic.span(), signature, "parameter", "unsupported_variadic", true);
        }
        let body = self.block(&function.block, root, "body");
        self.frames.pop();
        for index in (0..self.nodes.len()).rev() {
            let mut children: Vec<usize> = self.nodes[index]["ordered_children"].as_array().unwrap()
                .iter().map(|child| child.as_u64().unwrap() as usize).collect();
            children.sort_by_key(|child| (self.nodes[*child]["range"][0].as_u64(), self.nodes[*child]["range"][1].as_u64(), *child));
            let closed = self.nodes[index]["coverage"] == "supported" && children.iter().all(|child| self.nodes[*child]["subtree_closed"] == true);
            self.nodes[index]["ordered_children"] = json!(children);
            self.nodes[index]["subtree_closed"] = json!(closed);
        }
        let unsupported = self.nodes.iter().filter(|node| node["coverage"] == "opaque").count();
        json!({"schema": "rust-structure-subset/1", "status": "parsed", "source_text": self.source,
            "root_id": root, "body_node_id": body, "nodes": self.nodes, "scopes": self.scopes,
            "binders": self.binders, "occurrences": self.occurrences,
            "coverage": {"domain": "exported_body_subset_not_full_rust_ast", "complete_supported": self.nodes[body]["subtree_closed"],
                "unsupported_nodes": unsupported, "exported_tree_closed": self.nodes[root]["subtree_closed"],
                "lexical_scopes_without_unknown_effects": self.scopes.iter().all(|scope| scope["unknown_binding_effects"] == false)},
            "cfg": "not_evaluated", "signature_semantics": "not_evaluated", "resolved_edges": 0,
            "binding_semantics": "lexical_candidates_only_not_rust_resolution"})
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut source = String::new();
    io::stdin().read_to_string(&mut source)?;
    let result = match syn::parse_str::<syn::ImplItemFn>(&source) {
        Ok(function) => {
            let mut exporter = Exporter { source: &source, nodes: Vec::new(), scopes: Vec::new(), frames: Vec::new(), binders: Vec::new(), occurrences: Vec::new() };
            exporter.function(&function)
        }
        Err(error) => json!({"schema": "rust-structure-subset/1", "status": "rejected", "source_text": source,
            "nodes": [], "scopes": [], "binders": [], "occurrences": [], "error": error.to_string(),
            "coverage": {"domain": "exported_body_subset_not_full_rust_ast", "complete_supported": false,
                "unsupported_nodes": 0, "exported_tree_closed": false}, "cfg": "not_evaluated", "resolved_edges": 0}),
    };
    println!("{}", serde_json::to_string(&result)?);
    Ok(())
}
