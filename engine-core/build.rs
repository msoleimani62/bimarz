// This script compiles the official Xray-core .proto files into Rust code
// at build time, then auto-generates a nested Rust module tree that
// exactly mirrors the dotted proto package names (e.g. "xray.app.proxyman"
// becomes `pub mod xray { pub mod app { pub mod proxyman { ... } } }`).
//
// This second step is required because prost-build emits one flat .rs
// file per unique proto package and expects the *consuming* crate to
// nest its own Rust modules to match; if that nesting is wrong, the
// generated cross-package `super::` references fail to resolve. Building
// the tree automatically (instead of hand-writing it) means it can never
// drift out of sync when the upstream proto files change shape.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

fn find_proto_files(dir: &Path, out: &mut Vec<PathBuf>) -> std::io::Result<()> {
    for entry in std::fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.is_dir() {
            find_proto_files(&path, out)?;
        } else if path.extension().is_some_and(|ext| ext == "proto") {
            out.push(path);
        }
    }
    Ok(())
}

#[derive(Default)]
struct ModuleNode {
    generated_file: Option<PathBuf>,
    children: BTreeMap<String, ModuleNode>,
}

fn insert_generated_file(root: &mut BTreeMap<String, ModuleNode>, segments: &[&str], file: &Path) {
    let (head, rest) = match segments.split_first() {
        Some(pair) => pair,
        None => return,
    };
    let node = root.entry(head.to_string()).or_default();
    if rest.is_empty() {
        node.generated_file = Some(file.to_path_buf());
    } else {
        insert_generated_file(&mut node.children, rest, file);
    }
}

// چند نام پکیج ممکن است با کلیدواژه‌های رزرو‌شده‌ی Rust برخورد کنند (مثل
// "type" یا "self")؛ این تابع با raw identifier (r#) این تصادم را کنترل می‌کند.
//
// A few package name segments can collide with Rust reserved keywords
// (e.g. "type" or "self"); this escapes them as raw identifiers (r#).
fn safe_ident(segment: &str) -> String {
    const RESERVED: &[&str] = &[
        "type", "self", "super", "crate", "mod", "fn", "struct", "enum", "impl", "trait", "move",
        "match", "loop", "if", "else", "let", "const", "static", "pub", "use", "as",
    ];
    if RESERVED.contains(&segment) {
        format!("r#{segment}")
    } else {
        segment.to_string()
    }
}

fn emit_tree(nodes: &BTreeMap<String, ModuleNode>, out: &mut String) {
    for (name, node) in nodes {
        out.push_str(&format!("pub mod {} {{\n", safe_ident(name)));
        if let Some(file) = &node.generated_file {
            // include! به‌جای include_proto! چون مسیر فایل را از قبل
            // خودمان با اسکن OUT_DIR پیدا کرده‌ایم.
            // include! instead of include_proto! since we already found
            // the file path ourselves by scanning OUT_DIR.
            out.push_str(&format!("include!({:?});\n", file.display().to_string()));
        }
        emit_tree(&node.children, out);
        out.push_str("}\n");
    }
}

fn generate_module_tree(out_dir: &Path) -> std::io::Result<()> {
    let mut root: BTreeMap<String, ModuleNode> = BTreeMap::new();

    for entry in std::fs::read_dir(out_dir)? {
        let entry = entry?;
        let path = entry.path();
        let is_rs = path.extension().is_some_and(|ext| ext == "rs");
        if !is_rs {
            continue;
        }
        let stem = path.file_stem().unwrap().to_string_lossy().to_string();
        if stem == "pb_tree" {
            continue; // خروجی خودمان از اجرای قبلی را دوباره پردازش نکن
        }
        let segments: Vec<&str> = stem.split('.').collect();
        insert_generated_file(&mut root, &segments, &path);
    }

    let mut code = String::new();
    emit_tree(&root, &mut code);
    std::fs::write(out_dir.join("pb_tree.rs"), code)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let proto_root = Path::new("proto");

    if !proto_root.join("app").exists() || !proto_root.join("common").exists() {
        eprintln!(
            "error: proto/app or proto/common not found\n\
             hint: run the fetch steps in engine-core/proto/README.md first"
        );
        std::process::exit(1);
    }

    let mut proto_files = Vec::new();
    find_proto_files(proto_root, &mut proto_files)?;

    if proto_files.is_empty() {
        eprintln!(
            "error: no .proto files found under {}",
            proto_root.display()
        );
        std::process::exit(1);
    }

    println!("cargo:warning=compiling {} proto files", proto_files.len());

    tonic_build::configure()
        .build_server(false)
        .build_client(true)
        .compile_protos(&proto_files, &[proto_root])?;

    let out_dir = PathBuf::from(std::env::var("OUT_DIR")?);
    generate_module_tree(&out_dir)?;

    Ok(())
}
