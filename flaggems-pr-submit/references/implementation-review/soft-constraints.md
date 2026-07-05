# Implementation Review Soft Constraints

- Preserve target operator behavior while adapting generated code to the current FlagGems project style.
- Review duplicate or dead generated functions and remove only code that is unrelated to the target operator or provably unused.
- Ensure wrapper dtype guards and unsupported dtype behavior match the implemented kernel and tests.
- Preserve useful generated comments while removing comments that describe stale hardcoded assumptions.
- Accuracy tests must validate meaningful reference behavior, including NaN or statistical behavior when the operator semantics require it.
- Benchmark repair must preserve custom Benchmark subclasses or input generation needed for complex operator shapes.
- Repair visible semantic issues in accuracy tests and benchmarks before execution instead of waiting for runtime failures.
