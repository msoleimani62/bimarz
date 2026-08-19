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
//
// The exact upstream Xray version is pinned in `xray-proto-pin.env`
// (next to this file) and exposed to the compiled extension as the
// `BIMARZ_XRAY_PROTO_TAG` env so Python can warn when the running
// xray-core binary does not match the generated bindings.
//
// این اسکریپت فایل‌های رسمی ‎.proto مربوط به Xray-core را هنگام build به
// کد Rust کامپایل می‌کند و بعد یک درخت ماژول تودرتوی Rust تولید می‌کند که
// دقیقاً با نام‌های نقطه‌دار پکیج proto مطابقت دارد. نسخه‌ی دقیق upstream
// در `xray-proto-pin.env` پین شده و از طریق env به نام
// `BIMARZ_XRAY_PROTO_TAG` به اکستنشن کامپایل‌شده منتقل می‌شود تا پایتون
// بتواند هنگام ناهماهنگی باینری xray-core با bindingهای تولیدشده هشدار بدهد.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

// Name of the version pin file living next to this build script.
// نام فایل پین نسخه که کنار همین build script قرار دارد.
const PIN_FILE_NAME: &str = "xray-proto-pin.env";

// Dedicated subdirectory under OUT_DIR that holds only the prost/tonic
// output. Compiling into our own dir (instead of scanning all of OUT_DIR)
// means stale files from older builds can never leak into the module
// tree, because we wipe and recreate this dir on every build-script run.
// زیردایرکتوری اختصاصی زیر OUT_DIR که فقط خروجی prost/tonic را نگه می‌دارد.
// کامپایل داخل دایرکتوری خودمان (به‌جای اسکن کل OUT_DIR) یعنی فایل‌های
// کهنه‌ی buildهای قبلی هرگز نمی‌توانند به درخت ماژول نشت کنند، چون این
// دایرکتوری در هر اجرای build script پاک و دوباره ساخته می‌شود.
const GEN_DIR_NAME: &str = "pb";

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

// Reads XRAY_PROTO_TAG / XRAY_PROTO_COMMIT from the pin file. The file is
// also sourced by bash, so only `KEY="value"` lines are understood here.
// مقدار XRAY_PROTO_TAG / XRAY_PROTO_COMMIT را از فایل پین می‌خواند. چون
// این فایل در bash هم source می‌شود، اینجا فقط خط‌های `KEY="value"` فهمیده
// می‌شوند.
fn read_pin(pin_path: &Path) -> Result<(String, String), Box<dyn std::error::Error>> {
    let content = std::fs::read_to_string(pin_path).map_err(|e| {
        format!(
            "failed to read {}: {e}. The Xray proto version pin is mandatory; restore the file.",
            pin_path.display()
        )
    })?;

    let mut tag: Option<String> = None;
    let mut commit: Option<String> = None;
    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let Some((key, value)) = line.split_once('=') else {
            continue;
        };
        let value = value.trim().trim_matches('"').to_string();
        match key.trim() {
            "XRAY_PROTO_TAG" => tag = Some(value),
            "XRAY_PROTO_COMMIT" => commit = Some(value),
            _ => {}
        }
    }

    let tag = tag
        .filter(|t| !t.is_empty())
        .ok_or_else(|| format!("XRAY_PROTO_TAG missing or empty in {}", pin_path.display()))?;
    Ok((tag, commit.unwrap_or_default()))
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
// "type" یا "self")؛ این تابع آن تصادم را کنترل می‌کند.
//
// A few package name segments can collide with Rust keywords (e.g.
// "type" or "self"); this function controls that collision. It is
// deliberately robust beyond the currently known Xray proto tree so the
// generated-code boundary stays correct if upstream later adds packages
// with awkward names:
//
// - `self`, `super`, `crate` and `Self` can NEVER be raw identifiers, so
//   they are suffixed with `_` instead of the `r#` prefix.
// - every other strict/reserved keyword is emitted as a raw identifier.
// - characters that are invalid in Rust identifiers become `_`, and a
//   leading digit is neutralised by a `_` prefix.
fn safe_ident(segment: &str) -> String {
    // Raw identifiers are forbidden for these four, independent of edition.
    // این چهار مورد مستقل از edition هرگز نمی‌توانند raw identifier باشند.
    match segment {
        "self" | "super" | "crate" | "Self" => return format!("{segment}_"),
        _ => {}
    }

    // Strict and reserved keywords (2015/2018/2021, plus 2024's `gen`).
    // Including not-yet-strict keywords is harmless: `r#` on a plain
    // identifier is still valid Rust.
    // کلیدواژه‌های strict و reserved (۲۰۱۵/۲۰۱۸/۲۰۲۱ به‌علاوه‌ی `gen` مربوط
    // به ۲۰۲۴). گنجاندن کلیدواژه‌هایی که هنوز strict نشده‌اند بی‌ضرر است:
    // `r#` روی یک شناسه‌ی عادی هم Rust معتبر است.
    const KEYWORDS: &[&str] = &[
        "as", "async", "await", "become", "box", "break", "const", "continue", "do", "dyn", "else",
        "enum", "extern", "false", "final", "fn", "for", "gen", "if", "impl", "in", "let", "loop",
        "macro", "match", "mod", "move", "mut", "override", "priv", "pub", "ref", "return",
        "static", "struct", "trait", "true", "try", "type", "typeof", "unsafe", "unsized", "use",
        "virtual", "where", "while", "yield",
    ];

    let mut ident = String::with_capacity(segment.len() + 2);
    for (index, ch) in segment.chars().enumerate() {
        let valid = if index == 0 {
            ch == '_' || ch.is_ascii_alphabetic()
        } else {
            ch == '_' || ch.is_ascii_alphanumeric()
        };
        ident.push(if valid { ch } else { '_' });
    }
    if ident.is_empty() {
        ident.push('_');
    }

    if KEYWORDS.contains(&ident.as_str()) {
        format!("r#{ident}")
    } else {
        ident
    }
}

fn emit_tree(nodes: &BTreeMap<String, ModuleNode>, out: &mut String) {
    for (name, node) in nodes {
        out.push_str(&format!("pub mod {} {{\n", safe_ident(name)));
        if let Some(file) = &node.generated_file {
            // include! به‌جای include_proto! چون مسیر فایل را از قبل
            // خودمان با اسکن دایرکتوری تولید پیدا کرده‌ایم. قالب ‎{:?}‎ روی
            // مسیر، بک‌اسلش‌های ویندوز را escape می‌کند و لترال معتبر می‌سازد.
            // include! instead of include_proto! since we already found
            // the file path ourselves by scanning the generation dir. The
            // {:?} format escapes Windows backslashes into a valid literal.
            out.push_str(&format!("include!({:?});\n", file.display().to_string()));
        }
        emit_tree(&node.children, out);
        out.push_str("}\n");
    }
}

// Builds the pb_tree.rs module tree from the *.rs files prost/tonic wrote
// into gen_dir. BTreeMap iteration keeps the output deterministic
// regardless of filesystem traversal order.
// درخت ماژول pb_tree.rs را از فایل‌های ‎*.rs ساخته‌شده توسط prost/tonic در
// gen_dir می‌سازد. پیمایش BTreeMap خروجی را مستقل از ترتیب پیمایش سیستم‌فایل
// قطعی (deterministic) نگه می‌دارد.
fn generate_module_tree(gen_dir: &Path, out_dir: &Path) -> std::io::Result<usize> {
    let mut root: BTreeMap<String, ModuleNode> = BTreeMap::new();
    let mut count = 0usize;

    for entry in std::fs::read_dir(gen_dir)? {
        let entry = entry?;
        let path = entry.path();
        let is_rs = path.extension().is_some_and(|ext| ext == "rs");
        if !is_rs {
            continue;
        }
        let stem = path.file_stem().unwrap().to_string_lossy().to_string();
        let segments: Vec<&str> = stem.split('.').collect();
        insert_generated_file(&mut root, &segments, &path);
        count += 1;
    }

    let mut code = String::new();
    emit_tree(&root, &mut code);
    std::fs::write(out_dir.join("pb_tree.rs"), code)?;
    Ok(count)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let manifest_dir = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR")?);
    let pin_path = manifest_dir.join(PIN_FILE_NAME);
    let proto_root = manifest_dir.join("proto");

    // Re-run this script when the proto tree or the version pin changes.
    // بدون این directiveها تغییر protoها regeneration را trigger نمی‌کند.
    // Without these directives, proto changes would not trigger regeneration.
    println!("cargo:rerun-if-changed={}", proto_root.display());
    println!("cargo:rerun-if-changed={}", pin_path.display());

    let (xray_tag, _xray_commit) = read_pin(&pin_path)?;
    // Make the pinned version visible to the compiled extension so
    // `bimarz doctor` can warn about proto/binary mismatches at runtime.
    // نسخه‌ی پین‌شده را به اکستنشن کامپایل‌شده منتقل می‌کند تا
    // `bimarz doctor` بتواند هنگام ناهماهنگی proto/باینری هشدار بدهد.
    println!("cargo:rustc-env=BIMARZ_XRAY_PROTO_TAG={xray_tag}");
    println!("cargo:warning=building against xray-core proto pin {xray_tag}");

    if !proto_root.join("app").exists() || !proto_root.join("common").exists() {
        eprintln!(
            "error: proto/app or proto/common not found\n\
             hint: run scripts/fetch-protos.sh from the repository root first\n\
             hint: the expected Xray version is pinned in engine-core/{PIN_FILE_NAME}"
        );
        std::process::exit(1);
    }

    let mut proto_files = Vec::new();
    find_proto_files(&proto_root, &mut proto_files)?;
    // Sort for a deterministic protoc invocation regardless of the order
    // the filesystem happened to return directory entries in.
    // مرتب‌سازی برای فراخوانی قطعی و تکرارپذیر protoc، مستقل از ترتیبی که
    // سیستم‌فایل ورودی‌ها را برگردانده است.
    proto_files.sort();

    if proto_files.is_empty() {
        eprintln!(
            "error: no .proto files found under {}\n\
             hint: re-run scripts/fetch-protos.sh to restore the proto tree",
            proto_root.display()
        );
        std::process::exit(1);
    }

    println!("cargo:warning=compiling {} proto files", proto_files.len());

    let out_dir = PathBuf::from(std::env::var("OUT_DIR")?);
    let gen_dir = out_dir.join(GEN_DIR_NAME);
    // Wipe only OUR generation subdirectory; the rest of OUT_DIR belongs to
    // Cargo and must not be fought with.
    // فقط زیردایرکتوری تولید خودمان پاک می‌شود؛ بقیه‌ی OUT_DIR متعلق به
    // Cargo است و نباید با کش build آن درگیر شد.
    if gen_dir.exists() {
        std::fs::remove_dir_all(&gen_dir)?;
    }
    std::fs::create_dir_all(&gen_dir)?;

    tonic_build::configure()
        .build_server(false)
        .build_client(true)
        .out_dir(&gen_dir)
        .compile_protos(&proto_files, &[&proto_root])?;

    let generated = generate_module_tree(&gen_dir, &out_dir)?;
    if generated == 0 {
        return Err(format!(
            "tonic/prost produced no .rs files in {} — cannot build the module tree",
            gen_dir.display()
        )
        .into());
    }

    Ok(())
}
