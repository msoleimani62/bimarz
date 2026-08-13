# BiMarz Phase 8 — Lifecycle Hardening

**Status:** validation complete; finalization pending
**Phase:** 8
**Project:** BiMarz
**Scope:** connection lifecycle, transactional startup, rollback, cleanup, engine ownership, GUI lifecycle, canonical outbound identity, security validation, and acceptance evidence

---

## 1. Purpose

Phase 8 hardens the complete BiMarz connection lifecycle.

The objective is to make startup, resource ownership, failure rollback, cleanup, engine-client lifecycle, GUI coordination, and lifecycle reporting behave as one consistent state transition.

The phase specifically addresses:

- Partial-resource acquisition during startup.
- Incomplete rollback after startup failures.
- Cleanup operations that could prevent other cleanup operations from running.
- Cleanup failures that were not sufficiently observable.
- Engine clients whose ownership boundary was implicit.
- GUI cleanup paths that could stop after an individual failure.
- Inconsistent active outbound identifiers across layers.
- Missing regression coverage for lifecycle failure paths.
- Dependency-locking and security-audit consistency.

Phase 8 is not considered finalized until the implementation, validation, repository checkpoint, tag, and final working-tree state have all been verified.

---

## 2. Scope

Phase 8 covers the following implementation and validation areas:

- Transactional connection startup.
- Startup rollback.
- Multi-resource cleanup.
- Cleanup failure reporting.
- Engine client ownership.
- Explicit engine client release.
- GUI worker cleanup.
- Canonical active outbound identity.
- Outbound creation and removal consistency.
- Lifecycle event reporting.
- Lifecycle regression tests.
- Cross-layer contract tests.
- Engine ownership tests.
- GUI lifecycle tests.
- Security workflow validation.
- Rust dependency lockfile tracking.
- Documentation and acceptance evidence.

---

## 3. Canonical Active Outbound

BiMarz defines one canonical active outbound tag:

`bimarz-active`

The same identity is required across the lifecycle components that operate on the active outbound.

The canonical tag is used by:

- Routing configuration.
- xray-core gRPC outbound creation.
- xray-core gRPC outbound removal.
- Connection lifecycle management.
- CLI operations.
- GUI operations.
- Startup rollback.
- Cleanup.

No lifecycle component should independently construct an alternative active-outbound identifier.

The purpose of this contract is to prevent configuration state and xray-core runtime state from referring to different outbound objects.

---

## 4. Transactional Startup

`ConnectionService.start()` is treated as a transactional lifecycle operation.

Resources acquired during startup are tracked as they become owned by the connection lifecycle.

If a later startup operation fails:

1. The original startup failure remains the primary failure.
2. Previously acquired resources are identified.
3. Rollback attempts to release every acquired resource.
4. A failure in one rollback operation does not prevent independent rollback operations.
5. Rollback failures are recorded and surfaced.
6. The connection is not reported as successfully active.
7. The service does not retain a partially initialized successful state.

The required behavior is therefore:

**startup succeeds completely, or the service returns to a non-active state while preserving failure evidence.**

---

## 5. Rollback Failure Model

Phase 8 distinguishes the primary startup failure from secondary rollback failures.

Example lifecycle:

1. Resource A is acquired.
2. Resource B is acquired.
3. Acquisition of resource C fails.
4. Rollback begins.
5. Resource B is released successfully.
6. Release of resource A fails.
7. The original C acquisition failure remains the primary startup failure.
8. The A cleanup failure is separately observable.
9. The connection is not considered active.

This prevents cleanup failures from masking the reason the startup transaction originally failed.

---

## 6. Cleanup Guarantees

`ConnectionService.cleanup()` performs best-effort cleanup across independent resources.

The cleanup contract requires:

- Independent cleanup operations are attempted even when another cleanup operation fails.
- Cleanup failures are not silently discarded.
- Resource ownership is released whenever possible.
- The resulting lifecycle state is not falsely reported as successful.
- Cleanup evidence remains available to callers and lifecycle observers.

Cleanup therefore distinguishes between:

- Complete cleanup.
- Partial cleanup.
- Cleanup failure.
- Rollback failure.

The implementation must preserve enough information to determine which cleanup operations were attempted and which operations failed.

---

## 7. Engine Client Ownership

`EngineService` owns the engine client used by the service lifecycle.

The ownership boundary is explicit.

`EngineService.close()` provides the lifecycle operation used to release the owned engine client.

The client must be released during:

- Normal cleanup.
- Failure-driven rollback.
- Other lifecycle termination paths that end the service's ownership period.

The ownership contract is covered by dedicated Phase 8 tests.

---

## 8. GUI Lifecycle

The GUI connection worker follows the same independent-cleanup principle.

A failure in one cleanup operation must not prevent unrelated resources from being released.

GUI cleanup therefore:

- Attempts independent cleanup operations.
- Continues after individual cleanup failures.
- Preserves cleanup failure information.
- Reports lifecycle failures.
- Releases the engine client when owned by the worker lifecycle.
- Attempts active outbound removal when required.

The Phase 8 GUI tests specifically exercise outbound removal, engine cleanup, and independent failure handling.

---

## 9. Lifecycle Events

Lifecycle failures are exposed through the event system.

The lifecycle event boundary provides observable information for failures including:

- Connection startup failure.
- Startup rollback failure.
- Cleanup failure.
- Active outbound removal failure.
- Engine client close failure.

Events provide observability but do not replace normal exception and error handling.

The primary operation failure must remain distinguishable from secondary cleanup failures.

---

## 10. Test Coverage

Phase 8 introduces dedicated test suites for the hardened lifecycle.

### 10.1 Lifecycle Regression Tests

File:

`tests/test_phase8_lifecycle.py`

Coverage includes:

- Successful lifecycle completion.
- Partial startup failure.
- Startup rollback.
- Multi-resource cleanup.
- Cleanup failure handling.
- Independent cleanup execution.
- Failure propagation.
- Lifecycle state consistency.

### 10.2 Contract Tests

File:

`tests/test_phase8_contracts.py`

These tests protect cross-layer contracts that must remain stable between the connection lifecycle, configuration, events, and supporting services.

### 10.3 Engine Service Tests

File:

`tests/test_phase8_engine_service.py`

Coverage includes:

- Engine client ownership.
- Explicit engine client closure.
- Engine cleanup behavior.
- Ownership release during lifecycle termination.

### 10.4 GUI Worker Tests

File:

`tests/test_phase8_gui_worker.py`

Coverage includes:

- GUI lifecycle cleanup.
- Active outbound removal.
- Engine client cleanup.
- Independent cleanup failure handling.

---

## 11. Validation Evidence

The following validation results are directly supported by the current validation output.

### 11.1 Python Test Suite

Command:

`python -m pytest -q`

Result:

- 252 passed.
- 0 failed.
- Test duration: approximately 10.51 seconds.

This includes the Phase 8 lifecycle, contract, engine-service, and GUI-worker test suites.

### 11.2 Rust Workspace Tests

Command:

`cargo test --workspace`

Result:

- 28 unit tests passed.
- 0 failed.
- 0 ignored.
- Rust doc-tests completed successfully.

The test output also contains:

`iptables: Failed to initialize nft: Permission denied`

The corresponding capability-probe test still passed.

This message is therefore treated as an environment capability warning rather than a Rust test failure.

### 11.3 Rust Clippy

Required command:

`cargo clippy --workspace --all-targets --all-features -- -D warnings`

Result:

- PASS.
- No warnings or errors were reported.
- The command completed successfully with `-D warnings`.

### 11.4 Git Whitespace Validation

Required command:

`git diff --cached --check`

Result:

- PASS.
- `git diff --cached --check` completed successfully.
- `git diff --check` completed successfully.
- No whitespace errors were reported.

---

## 12. Security Workflow

The security workflow validates the dependency graph represented by the repository lockfile.

Rust dependency auditing uses:

`cargo audit -f Cargo.lock`

Python dependency auditing uses:

`pip-audit`

Python source security scanning uses:

`bandit`

These tools are CI-only security tooling and are not runtime dependencies of BiMarz.

The Rust audit must target the tracked root `Cargo.lock` so that the audited dependency graph corresponds to the repository state.

---

## 13. Cargo.lock Policy

`Cargo.lock` is intentionally tracked.

The lockfile provides deterministic dependency resolution and allows the security workflow to audit the exact Rust dependency graph represented by the repository.

The root `.gitignore` therefore must not ignore:

`Cargo.lock`

The current Phase 8 change removes the previous ignore rule and adds the lockfile to the repository.

---

## 14. Documentation Consistency

Phase 8 documentation is distributed across:

- `README.md`
- `docs/INSTALL.md`
- `docs/PHASE-8-HARDENING.md`
- `CHANGELOG.md`

Documentation must describe the implementation state accurately.

In particular:

- Phase 8 must not be described as stable before finalization.
- Validation results must not be claimed without corresponding evidence.
- Finalization must not be inferred from passing tests alone.
- Repository state, commit, tag, and working-tree verification are part of finalization.

---

## 15. Acceptance Criteria

Phase 8 technical validation requires all of the following:

- Python tests pass completely.
- Rust workspace tests pass completely.
- Rust Clippy passes with `-D warnings`.
- Staged diff passes `git diff --cached --check`.
- Canonical active outbound identity is consistent.
- Startup rollback is transactional.
- Independent cleanup operations continue after individual failures.
- Cleanup failures are observable.
- Engine client ownership is explicit.
- Engine client cleanup is performed.
- GUI cleanup releases independent resources.
- Phase 8 lifecycle tests pass.
- Phase 8 contract tests pass.
- Phase 8 engine ownership tests pass.
- Phase 8 GUI worker tests pass.
- Security workflow targets the tracked lockfile.
- `Cargo.lock` is tracked.
- Documentation reflects the actual implementation state.

Technical validation alone does not finalize the phase.

---

## 16. Repository Evidence

The Phase 8 staged change currently contains the following paths:

- `.github/workflows/security.yml`
- `.gitignore`
- `CHANGELOG.md`
- `Cargo.lock`
- `README.md`
- `docs/INSTALL.md`
- `docs/PHASE-8-HARDENING.md`
- `orchestrator/bimarz/connection.py`
- `orchestrator/bimarz/events.py`
- `orchestrator/bimarz/gui/connection_worker.py`
- `orchestrator/bimarz/services/engine.py`
- `orchestrator/bimarz/xray_config.py`
- `pyproject.toml`
- `tests/test_cli.py`
- `tests/test_phase8_contracts.py`
- `tests/test_phase8_engine_service.py`
- `tests/test_phase8_gui_worker.py`
- `tests/test_phase8_lifecycle.py`
- `tests/test_platform_detect.py`
- `tests/test_xray_config.py`

The staged change contains 21 paths.

The previously observed staged diff summary was:

- 2,964 insertions.
- 94 deletions.

These figures are repository evidence from the validation checkpoint and should be rechecked before the final commit.

---

## 17. Finalization Workflow

Phase 8 finalization is a separate step from technical validation.

The finalization workflow requires:

1. Complete implementation inspection.
2. Complete staged-diff inspection.
3. Successful Python test validation.
4. Successful Rust test validation.
5. Successful Rust Clippy validation.
6. Successful staged whitespace validation.
7. Final documentation synchronization.
8. Verification of the security workflow.
9. Verification of dependency-lock consistency.
10. Final Git status inspection.
11. Creation of the Phase 8 stable commit.
12. Creation of the corresponding stable tag.
13. Verification that the tag points to the intended commit.
14. Verification that the working tree is clean.
15. Verification that the stable checkpoint is reproducible from Git history.

No stable tag or stable checkpoint should be created before all required validation steps have passed.

---

## 18. Current Phase State

Based on the final validation evidence currently supplied:

- Python test suite: PASS — 252 passed, 0 failed.
- Ruff: PASS.
- Ruff format check: PASS — 80 files already formatted.
- `pyproject.toml` validation: PASS — no broken requirements found.
- Rust workspace tests: PASS — 28 passed, 0 failed.
- Rust Clippy: PASS — `cargo clippy --workspace --all-targets --all-features -- -D warnings`.
- Staged whitespace validation: PASS — `git diff --cached --check`.
- Working-tree whitespace validation: PASS — `git diff --check`.
- Phase 8 dedicated tests: PASS as part of the full Python suite.
- Cargo.lock ownership and tracking: PASS.
- Security workflow lockfile target: PASS — `cargo audit -f Cargo.lock`.
- Documentation synchronization: completed for the current validation evidence.
- Stable commit: pending.
- Stable tag: pending.
- Tag verification: pending.
- Clean working tree after final commit: pending.

Therefore the correct current state is:

**Technical validation complete; Phase 8 finalization pending.**

Phase 8 must not be declared stable until the final commit, stable tag, tag verification, and clean working-tree verification have all been completed.
