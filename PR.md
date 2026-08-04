# Stabilize runtime process management and doctor gRPC diagnostics

This update improves BiMarz runtime reliability by fixing critical issues in
Xray process lifecycle management, temporary configuration handling, and
environment diagnostics.

## Highlights

### Xray Runtime Configuration

- Generated Xray configuration is now written to a dedicated runtime file before process startup.
- Process factories now receive configuration file paths instead of raw JSON content.
- Runtime directories are automatically cleaned when startup fails.
- Temporary runtime resources are properly removed during shutdown.

This makes process startup safer and closer to the real xray-core execution model.

### Process Lifecycle Improvements

- Improved temporary directory ownership and cleanup flow.
- Prevented leaked runtime files after failed startup attempts.
- Simplified process creation through cleaner dependency injection paths.
- Improved resource handling during stop and failure scenarios.

### Doctor Service Improvements

- Fixed gRPC diagnostic flow to use endpoint strings consistently.
- Removed incorrect engine client creation during health checks.
- Preserved explicit timeout values passed by callers.
- Improved separation between TCP availability checks and gRPC response checks.
- Updated doctor tests to match the new probing architecture.

Diagnostic flow:

1. Verify xray binary availability.
2. Validate stored profiles.
3. Check kill-switch state.
4. Verify TCP connectivity.
5. Probe gRPC service availability.

### Code Quality

- Simplified cleanup logic using safer resource handling.
- Reduced Ruff static analysis warnings.
- Updated tests for the new architecture.
- Improved consistency and formatting.

## Validation

```bash
pytest -q
ruff check orchestrator tests --output-format=concise
```

### Result

- 97 tests passed
- Ruff checks passed
