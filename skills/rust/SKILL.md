---
name: rust
description: 'Write, review, and refactor idiomatic Rust with a focus on error handling, ownership/borrowing, API design, and safety. Use when: writing Rust code, fixing borrow-checker or lifetime errors, designing error types (thiserror/anyhow, Result, ?), replacing unwrap/panic, choosing between clone/borrow/Cow/Arc, structuring modules and traits, adding tests, or reviewing a Rust change for idiomatic style and correctness.'
argument-hint: '<what you are building, the error you hit, or the file/diff to review>'
---

# Rust Best Practices

Use this skill when writing new Rust, refactoring existing Rust, or reviewing a Rust change. It captures the idioms the compiler cannot enforce: how to handle errors, how to work with the borrow checker instead of against it, and how to design APIs that are hard to misuse.

Default to the simplest thing that compiles cleanly and reads well. Reach for `unsafe`, extra `clone`s, `Arc<Mutex<_>>`, or macro machinery only when a concrete problem demands it.

## When to Use

- Writing a new module, function, type, or crate in Rust.
- Fixing borrow-checker, lifetime, `move`, or trait-bound errors.
- Designing or cleaning up error handling (`Result`, `?`, custom error types).
- Removing `.unwrap()`, `.expect()`, or `panic!` from non-test code.
- Deciding between borrow / clone / `Cow` / `Rc` / `Arc` / `Box`.
- Reviewing a Rust diff for idiomatic style, correctness, and safety.

## Core Workflow

1. **Model the domain with types first.** Prefer enums and structs that make invalid states unrepresentable over runtime checks. A `NonEmptyVec` or an `enum State` beats a comment saying "must not be empty".
2. **Decide the error strategy up front** (see the Error Handling section). Library code → typed errors. Application/`main` code → `anyhow`-style context.
3. **Write the happy path with `?`,** then handle each failure explicitly at the boundary where you can act on it.
4. **Make it borrow-check cleanly** by adjusting ownership at API boundaries (see the Ownership & Borrowing section) rather than sprinkling `.clone()`.
5. **For I/O-bound concurrency, go async** (see the Async & Concurrency section); for CPU-bound work, use threads. Never block the async runtime.
6. **Add tests** — unit tests in a `#[cfg(test)] mod tests`, and `#[test]` cases for error paths, not just the happy path.
7. **Run the toolchain:** `cargo fmt`, `cargo clippy -- -D warnings`, `cargo test`. Treat clippy warnings as todo items, not noise.

## Error Handling

The single most important idiom in Rust. Follow these rules.

### Never `unwrap`/`panic` on recoverable errors

`unwrap`, `expect`, and `panic!` abort the program. They are acceptable only in tests, examples, prototypes, or on a genuinely unreachable invariant (document why with `expect("reason invariant holds")`). Everywhere else, return a `Result`.

```rust
// ✗ Bad — a malformed config crashes the whole process.
let port: u16 = config.get("port").unwrap().parse().unwrap();

// ✓ Good — the caller decides what to do with the failure.
let port: u16 = config
    .get("port")
    .ok_or(ConfigError::MissingPort)?
    .parse()
    .map_err(ConfigError::InvalidPort)?;
```

### Propagate with `?`, don't nest `match`

The `?` operator returns early on `Err` and unwraps on `Ok`, converting the error via `From`. Let it do the work.

```rust
// ✗ Bad
fn load(path: &Path) -> Result<Config, ConfigError> {
    let text = match std::fs::read_to_string(path) {
        Ok(t) => t,
        Err(e) => return Err(ConfigError::Io(e)),
    };
    match toml::from_str(&text) {
        Ok(c) => Ok(c),
        Err(e) => Err(ConfigError::Parse(e)),
    }
}

// ✓ Good — From impls (via thiserror #[from]) make ? convert automatically.
fn load(path: &Path) -> Result<Config, ConfigError> {
    let text = std::fs::read_to_string(path)?;
    let config = toml::from_str(&text)?;
    Ok(config)
}
```

### Library code: typed errors with `thiserror`

Libraries should expose a concrete, matchable error enum so callers can branch on failure kinds. `thiserror` generates the `Display` and `From` boilerplate.

```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("could not read config file")]
    Io(#[from] std::io::Error),

    #[error("config file is not valid TOML")]
    Parse(#[from] toml::de::Error),

    #[error("missing required field `port`")]
    MissingPort,

    #[error("`port` is not a valid u16: {0}")]
    InvalidPort(std::num::ParseIntError),
}
```

### Application code: contextual errors with `anyhow`

Binaries and top-level app code usually don't need callers to match on error kinds — they need good diagnostics. Use `anyhow::Result` and attach context.

```rust
use anyhow::{Context, Result};

fn run() -> Result<()> {
    let path = "config.toml";
    let config = load(path.as_ref())
        .with_context(|| format!("failed to load config from {path}"))?;
    start_server(&config).context("failed to start server")?;
    Ok(())
}

fn main() -> Result<()> {
    run() // anyhow prints the full context chain on error
}
```

**Rule of thumb:** `thiserror` in `lib.rs` and reusable crates, `anyhow` in `main.rs`/binaries. Don't expose `anyhow::Error` in a library's public API.

### Prefer combinators for simple transforms

`map`, `map_err`, `and_then`, `ok_or`, `unwrap_or_default`, and `?` express intent more clearly than a `match` for one-liners — but reach for `match` when each arm has real logic.

## Ownership & Borrowing

Most borrow-checker fights come from taking ownership when a borrow would do, or vice versa.

### Accept the most flexible type; return owned

Take `&str` over `&String`, `&[T]` over `&Vec<T>`, `impl AsRef<Path>` over `&Path` when ergonomic. Return owned `String`/`Vec<T>` so callers aren't tied to your internals.

```rust
// ✓ Accepts &str, &String, and string literals.
fn greeting(name: &str) -> String {
    format!("Hello, {name}!")
}
```

### Clone deliberately, not to silence the compiler

A `.clone()` added to make an error disappear often hides a design issue. First ask: can I restructure so the value is borrowed, moved once, or its lifetime shortened? If a clone is genuinely the simplest correct choice (small data, cold path), keep it — but do it on purpose.

### `Cow` when you clone only sometimes

`Cow<str>` lets a function borrow when it can and allocate only when it must mutate.

```rust
use std::borrow::Cow;

fn normalize(input: &str) -> Cow<'_, str> {
    if input.contains(' ') {
        Cow::Owned(input.replace(' ', "_")) // allocate only when needed
    } else {
        Cow::Borrowed(input)                // no allocation on the common path
    }
}
```

### Shared ownership: `Rc`/`Arc`, and interior mutability

- `Rc<T>` — single-threaded shared ownership. `Arc<T>` — thread-safe shared ownership.
- Need to mutate shared data? `RefCell<T>` (single-thread, runtime borrow checks) or `Mutex<T>`/`RwLock<T>` (multi-thread). Combine as `Arc<Mutex<T>>` for shared mutable state across threads — but prefer message passing (channels) when it fits.

Reach for these only when you actually share ownership; a plain `&mut T` or moving the value is cheaper and clearer.

## Async & Concurrency

Use async for I/O-bound work (network, disk, many concurrent connections). For CPU-bound work, prefer threads (`std::thread`, `rayon`) — async gives you nothing there and can starve the runtime.

### Don't block the async runtime

An `async fn` must never do long synchronous work or call blocking APIs — it stalls the whole executor thread. Use the async equivalent, or offload blocking work.

```rust
// ✗ Bad — std::fs and thread::sleep block the runtime thread.
async fn read_config() -> anyhow::Result<String> {
    std::thread::sleep(std::time::Duration::from_secs(1)); // blocks executor
    Ok(std::fs::read_to_string("config.toml")?)            // blocking I/O
}

// ✓ Good — async I/O, and offload unavoidable blocking work.
use tokio::fs;
async fn read_config() -> anyhow::Result<String> {
    let text = fs::read_to_string("config.toml").await?;   // async I/O
    // For a blocking CPU/library call, move it off the async threads:
    let parsed = tokio::task::spawn_blocking(move || heavy_parse(&text)).await??;
    Ok(parsed)
}
```

### Run futures concurrently, don't just `.await` in sequence

Awaiting one future after another is serial. Use `join!` for concurrent-and-all-must-succeed, `try_join!` to short-circuit on the first error, and `select!` to race.

```rust
use tokio::try_join;

// Both requests run concurrently; returns early if either errors.
let (user, posts) = try_join!(fetch_user(id), fetch_posts(id))?;
```

### Spawn tasks; move owned data in

`tokio::spawn` needs a `'static` future, so pass owned data (clone an `Arc`, move the value) rather than borrows. Share state with `Arc<Mutex<T>>` or, better, an actor/channel pattern (`tokio::sync::mpsc`).

```rust
let state = Arc::clone(&shared);
let handle = tokio::spawn(async move {
    let mut guard = state.lock().await; // tokio::sync::Mutex in async code
    guard.update();
});
handle.await?; // propagate panics/join errors
```

### Gotchas

- Use `tokio::sync::Mutex` (not `std::sync::Mutex`) when the lock is held across an `.await`. If it's never held across await, the std mutex is faster.
- Futures are lazy — they do nothing until `.await`ed or spawned.
- Keep `Send` in mind: a value held across `.await` must be `Send` for the future to run on a multi-threaded runtime.
- Add cancellation/timeouts with `tokio::time::timeout` and cancellation tokens for long-running tasks.

## API & Type Design

- **Make illegal states unrepresentable.** Use enums for mutually exclusive states; newtypes (`struct UserId(u64)`) to prevent mixing up values of the same primitive type.
- **Derive the standard traits** where they make sense: `#[derive(Debug, Clone, PartialEq, Eq, Hash)]`. Add `Default` when there's a sensible zero value.
- **Implement `From`/`TryFrom`** for conversions instead of ad-hoc `to_x`/`from_x` methods; this unlocks `?` and `.into()`.
- **Use iterators over index loops.** `iter().map().filter().collect()` is clearer and often faster than manual indexing, and avoids off-by-one and bounds bugs.
- **Prefer `impl Trait`** in argument and simple return positions to keep signatures light.
- **Keep `unsafe` tiny and justified.** Every `unsafe` block needs a `// SAFETY:` comment explaining why the invariants hold. Encapsulate it behind a safe API.

```rust
// Newtype prevents passing a raw u64 where a UserId is expected.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct UserId(pub u64);

// Iterator chain instead of an index loop.
let evens_squared: Vec<u64> = numbers
    .iter()
    .filter(|&&n| n % 2 == 0)
    .map(|&n| n * n)
    .collect();
```

## Testing

- Put unit tests in the same file under `#[cfg(test)] mod tests { use super::*; ... }`.
- Test **error paths**, not just success. Assert on the specific error variant where it matters.
- Use `#[should_panic(expected = "...")]` sparingly, only for code that is contractually allowed to panic.
- Integration tests go in `tests/`; each file is its own crate testing the public API.

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_valid_port() {
        assert_eq!(parse_port("8080").unwrap(), 8080);
    }

    #[test]
    fn rejects_non_numeric_port() {
        let err = parse_port("abc").unwrap_err();
        assert!(matches!(err, ConfigError::InvalidPort(_)));
    }
}
```

## Tooling Checklist

Run before considering a change done:

- `cargo fmt --all` — canonical formatting, no debate.
- `cargo clippy --all-targets -- -D warnings` — treat lints as errors; fix or `#[allow]` with a reason.
- `cargo test` — unit + integration tests.
- `cargo doc --no-deps` — confirm public items have doc comments (`///`) where useful.

## Quick Anti-Pattern Reference

| Smell | Prefer |
|-------|--------|
| `.unwrap()` / `.expect()` in library code | `?` + typed `Result` |
| `panic!` for recoverable errors | return an error variant |
| `.clone()` to appease the borrow checker | borrow, move once, or restructure |
| `String` parameter | `&str` / `impl AsRef<str>` |
| `&Vec<T>` parameter | `&[T]` |
| Index loop with `for i in 0..v.len()` | iterator chain |
| `Arc<Mutex<T>>` everywhere | message passing / plain ownership when possible |
| Stringly-typed IDs (`u64`, `String`) | newtypes (`struct UserId(u64)`) |
| `unsafe` without a `// SAFETY:` note | documented, encapsulated `unsafe` |
| Blocking call / `std::fs` inside `async fn` | async I/O or `spawn_blocking` |
| Serial `.await`, `.await`, `.await` | `join!` / `try_join!` for concurrency |
| `std::sync::Mutex` held across `.await` | `tokio::sync::Mutex` |
