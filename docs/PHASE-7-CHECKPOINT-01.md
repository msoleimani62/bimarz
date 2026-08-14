# BiMarz — Phase 7 Checkpoint 01

## Status

Phase 7 VLESS profile/parser consolidation checkpoint.

Repository state at checkpoint:
- Branch: main
- Python: 3.13.14
- Rust: 1.97.1
- Project: BiMarz
- Architecture: Python orchestration + Rust engine-core
- Target protocol: VLESS + Reality + Vision
- Primary Python profile model: ServerProfile
- Canonical VLESS parser: bimarz.parsers.vless.parse_vless_link

This checkpoint is authoritative for the work completed before the next Phase 7 implementation batch.

Future agents MUST read this file before modifying any of the files listed in this checkpoint.

---

## 1. Phase 7 Objective Completed So Far

The VLESS parsing/profile architecture was consolidated around the existing ServerProfile model.

The previous dedicated VlessRealityOutbound model and subscription parser were removed.

The canonical architecture is now:

VLESS share link
    ->
bimarz.parsers.vless.parse_vless_link()
    ->
ServerProfile
    ->
ProfileService / ProfileStore / CLI / GUI / health-check / failover / engine
    ->
Rust engine-core VLESS builder
    ->
xray-core protobuf configuration

There must not be a second independent VLESS profile representation unless a future architectural decision explicitly introduces one.

---

## 2. Canonical Parser

Canonical parser:

orchestrator/bimarz/parsers/vless.py

Canonical function:

parse_vless_link(link: str) -> ServerProfile

The parser is now responsible for:

- parsing vless:// links
- validating the UUID
- validating the host
- validating the port
- applying the default port 443
- decoding URL-encoded query values
- validating Reality security
- validating Vision flow
- requiring the Reality public key
- extracting SNI
- using host as the SNI fallback
- extracting fingerprint
- extracting shortId
- extracting spiderX
- extracting transport type
- extracting path
- extracting host
- extracting serviceName
- extracting packetEncoding
- extracting mux
- extracting allowInsecure
- extracting ECH
- decoding the URI fragment as the profile remark
- generating a unique profile_id
- returning a ServerProfile

The parser is the single canonical VLESS share-link parser for the application.

Do not recreate the deleted subscription.py parser.

---

## 3. Supported VLESS Contract

The current Phase 7 parser intentionally supports only:

protocol = vless
security = reality
flow = xtls-rprx-vision
pbk = required

Constants currently defined in the parser:

REQUIRED_SECURITY = "reality"
REQUIRED_FLOW = "xtls-rprx-vision"
DEFAULT_PORT = 443
DEFAULT_FINGERPRINT = "chrome"
DEFAULT_NETWORK = "tcp"
DEFAULT_ENCRYPTION = "none"

Unsupported protocol/security/flow combinations are rejected explicitly.

This is intentional.

Do not silently accept unsupported security or flow combinations.

---

## 4. Parser Error Model

The canonical parser now defines:

VlessParseError
UnsupportedVlessError
MalformedVlessError

Hierarchy:

VlessParseError(ValueError)
    UnsupportedVlessError
    MalformedVlessError

Use these parser-specific exceptions when testing or handling parser failures.

Do not restore the old:

SubscriptionParseError
UnsupportedLinkError
MalformedLinkError

Those belonged to the deleted subscription implementation.

---

## 5. ServerProfile Is Canonical

The previous:

VlessRealityOutbound

dataclass was removed from:

orchestrator/bimarz/models.py

ServerProfile is now the canonical application-level profile model.

The VLESS parser returns ServerProfile directly.

The rest of the Python application already consumes ServerProfile through:

- ProfileService
- ProfileStore
- CLI
- GUI
- health-check
- failover
- connection management
- engine integration

Do not introduce VlessRealityOutbound again merely to represent parsed VLESS data.

---

## 6. Deleted Files

The following files were intentionally deleted:

orchestrator/bimarz/subscription.py
tests/test_subscription.py

These files represented the previous duplicate subscription/VLESS parsing architecture.

They were replaced by:

orchestrator/bimarz/parsers/vless.py
tests/unit/test_vless_parser.py

Do not restore the deleted files unless the architecture is explicitly redesigned and approved.

---

## 7. Rust Integration

The Rust VLESS builder remains the engine-side consumer of the Python profile outbound configuration.

Modified file:

engine-core/src/vless_builder.rs

The comments/documentation were updated from references to the removed VlessRealityOutbound model to references to the canonical ServerProfile outbound configuration.

The Rust VLESS builder itself remains responsible for converting the raw profile configuration into typed xray-core protobuf structures.

Relevant validated behavior includes:

- VLESS outbound creation
- tag validation
- address validation
- IPv4 address handling
- IPv6 address handling
- domain address handling
- UUID validation
- port validation
- public key decoding
- short ID decoding
- Reality configuration
- sender configuration
- proxy settings
- protobuf type names

No architectural change was made to replace the Rust builder.

---

## 8. VLESS Parser Test Coverage

The parser test file is:

tests/unit/test_vless_parser.py

Current parser test count:

24 passed

The tests cover:

- valid VLESS Reality Vision link
- profile remark extraction
- outbound protocol
- UUID
- address
- port
- Reality security
- Vision flow
- Reality public key
- SNI
- query parameter preservation
- fingerprint
- encryption
- default port
- fallback profile remark
- URL-encoded fragment
- URL-encoded query values
- host-to-SNI fallback
- unique generated profile IDs
- valid port boundaries
- UUID normalization
- empty link rejection
- missing UUID rejection
- invalid UUID rejection
- unsupported URI scheme rejection
- missing security rejection
- unsupported security rejection
- missing Vision flow rejection
- unsupported flow rejection
- missing public key rejection
- invalid port rejection
- malformed port syntax rejection

The parser test suite was executed directly with:

pytest -q tests/unit/test_vless_parser.py

Result:

24 passed

---

## 9. Full Python Test Suite

The complete Python test suite was executed after the parser/profile consolidation.

Command:

pytest -q

Result:

211 passed

No Python test failures were present at this checkpoint.

This result is important.

Future agents MUST NOT rerun the entire previous debugging cycle merely because the parser/profile architecture changed.

The full suite is currently green.

---

## 10. Ruff Validation

The following command was executed:

python -m ruff check .

Result:

All checks passed.

No Ruff errors remain from the current checkpoint.

---

## 11. Ruff Formatting Validation

The following command was executed:

python -m ruff format --check .

Result:

74 files already formatted

Formatting validation passed.

---

## 12. Git Whitespace Validation

The following command was executed:

git diff --check

Result:

No whitespace errors.

---

## 13. Rust Test Suite

The Rust engine test suite was executed with:

cargo test --manifest-path engine-core/Cargo.toml

Result:

28 passed
0 failed
0 ignored
0 measured
0 filtered out

Doc-tests:

0 passed
0 failed

Rust tests are green.

---

## 14. Known Environment Warning

During Rust tests, the environment produced:

iptables: Failed to initialize nft: Permission denied

The corresponding kill-switch capability probe test still passed.

This is an environment/capability limitation of the current Kali NetHunter/Termux execution environment, not a test failure.

The result was:

test killswitch::tests::probe_kernel_capability_does_not_panic ... ok

Do not treat this warning as a failed Rust test.

---

## 15. Rust Proto Generation

The Rust test/build process reported:

compiling 69 proto files

The engine-core test suite completed successfully after protobuf compilation.

---

## 16. Repository Changes In This Checkpoint

Current changed files:

M engine-core/src/vless_builder.rs
M orchestrator/bimarz/models.py
M orchestrator/bimarz/parsers/vless.py
D orchestrator/bimarz/subscription.py
D tests/test_subscription.py
M tests/unit/test_vless_parser.py

Diff summary at checkpoint:

6 files changed
274 insertions
307 deletions

The deletion count is expected because the duplicate subscription parser/model/test implementation was removed.

---

## 17. Files Already Reviewed In This Cycle

The following components were explicitly examined during this checkpoint:

engine-core/src/vless_builder.rs
orchestrator/bimarz/models.py
orchestrator/bimarz/parsers/vless.py
orchestrator/bimarz/services/profile.py
orchestrator/bimarz/profiles.py
orchestrator/bimarz/subscription.py
tests/unit/test_vless_parser.py
tests/test_subscription.py

Searches were also performed for:

VlessRealityOutbound
subscription
parse_vless_link
ServerProfile
Subscription
subscribe
subscription_url

The search confirmed that the canonical parser is now the VLESS parser module and that the old subscription implementation is no longer present.

---

## 18. Existing ServerProfile Consumers

The following application areas already depend on ServerProfile:

- GUI connection worker
- GUI profile table
- GUI main window
- process service
- health service
- engine service
- profile service
- profile store
- failover
- helpers
- connect command
- connection manager
- tests for profiles
- tests for process service
- tests for engine
- tests for connection
- tests for commands/services
- CLI-related profile handling

Therefore ServerProfile is not a parser-local abstraction.

It is the established application-wide profile contract.

---

## 19. Important Architectural Decision

The project now has one canonical representation for an imported VLESS profile:

ServerProfile

The parser should not produce a temporary duplicate model that is later converted into ServerProfile.

The canonical flow is:

parse_vless_link()
    ->
ServerProfile

This eliminates the previous duplicate architecture involving:

subscription.py
VlessRealityOutbound
tests/test_subscription.py

---

## 20. What Must NOT Be Repeated

Future agents MUST NOT:

1. Recreate subscription.py.
2. Recreate tests/test_subscription.py.
3. Recreate VlessRealityOutbound.
4. Create another independent VLESS parser.
5. Replace ServerProfile with a new parser-specific profile model without an explicit architectural decision.
6. Re-run the previous parser consolidation work unless new failures demonstrate that the current implementation is incorrect.
7. Treat the iptables permission warning as a Rust test failure.
8. Assume that a green parser test requires the old subscription tests to be restored.
9. Remove the explicit Reality/Reality public-key/Vision validation.
10. weaken parser validation merely to make unrelated legacy tests pass.

---

## 21. Current Validation Baseline

The authoritative validation baseline is:

Python:
211 passed

VLESS parser:
24 passed

Ruff:
All checks passed

Ruff format:
74 files already formatted

Git diff check:
Passed

Rust:
28 passed

Rust doc-tests:
0 tests, successful

Overall:

GREEN

---

## 22. Current Phase 7 Starting Point

The parser/profile consolidation work is complete and validated.

The next work should start from the current repository state.

The next agent should first inspect:

git status
git log -1
git diff --stat
git diff --check

Then read this checkpoint.

After that, only the newly supplied Phase 7 files/tasks should be investigated.

Do not repeat the completed parser consolidation unless the new task explicitly requires changing it.

---

## 23. Required First Step For The Next Agent

Before modifying code:

1. This checkpoint was created under the governance files that existed at that time.
2. Those historical governance files are no longer present in the current repository.
3. Read this checkpoint.
4. Inspect the current git status.
5. Inspect the current HEAD.
6. Run only targeted tests relevant to the new task first.
7. Expand validation only after the targeted change is implemented.
8. Preserve the current green baseline.

---

## 24. Checkpoint Creation Metadata

This checkpoint represents the repository state immediately after:

- VLESS parser consolidation
- ServerProfile consolidation
- removal of duplicate subscription parser
- removal of VlessRealityOutbound
- parser exception hierarchy introduction
- expanded VLESS parser test coverage
- Rust documentation update
- full Python test validation
- Ruff validation
- formatting validation
- git whitespace validation
- Rust test validation

The next development session should continue from this exact architectural state.

