# Implementation Review Soft Constraints

- Preserve target operator behavior while adapting generated code to the current FlagGems project style.
- Review duplicate or dead generated functions and remove only code that is unrelated to the target operator or provably unused.
- Ensure wrapper dtype guards and unsupported dtype behavior match the implemented kernel and tests.
- Preserve useful generated comments while removing comments that describe stale hardcoded assumptions.
- Benchmark repair must preserve custom Benchmark subclasses or input generation needed for complex operator shapes.
- Repair visible semantic issues in accuracy tests and benchmarks before execution instead of waiting for runtime failures.
- For fused or custom operators, keep only implementations with a concrete downstream model or framework use case and document that use case before PR submission.
- For inplace operators, preserve PyTorch return-alias semantics and device behavior when adding or reusing implementation paths.
- Do not leave temporary debug instrumentation in operator implementations, tests, or benchmarks.
- Remove unimplemented public wrappers instead of registering or exporting them.
