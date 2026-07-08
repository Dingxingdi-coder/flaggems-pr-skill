# Implementation Review Soft Constraints

- Preserve target operator behavior while adapting generated code to the current FlagGems project style.
- Do not depend on resolver or extraction scripts to infer special per-operator naming, alias, reference, or wrapper relationships; inspect and document those relationships when they affect implementation scope after the main agent has resolved identity metadata.
- Missing structured metadata that blocks resolver or extraction is a main-agent source-metadata gate. At this stage, report any remaining identity metadata gaps instead of silently relying on script defaults.
- Review duplicate or dead generated functions and remove only code that is unrelated to the target operator or provably unused.
- Ensure wrapper dtype guards and unsupported dtype behavior match the implemented kernel and tests.
- Preserve useful generated comments while removing comments that describe stale hardcoded assumptions.
- Benchmark repair must preserve custom Benchmark subclasses or input generation needed for complex operator shapes.
- Repair missing target tests and benchmarks in the generated worktree with real operator coverage rather than adding script-side fixtures.
- Repair visible semantic issues in accuracy tests and benchmarks before execution instead of waiting for runtime failures.
- For fused or custom operators, keep only implementations with a concrete downstream model or framework use case and document that use case before PR submission.
- For inplace operators, preserve PyTorch return-alias semantics and device behavior when adding or reusing implementation paths.
- Do not leave temporary debug instrumentation in operator implementations, tests, or benchmarks.
- Remove unimplemented public wrappers instead of registering or exporting them.
