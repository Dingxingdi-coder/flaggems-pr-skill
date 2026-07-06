# Implementation Review Checklist

Create a task for each item and complete them in order:

- Locate the target implementation, accuracy test, benchmark, and registration-adjacent files.
- Check for duplicate or dead generated functions and identify only code that is unrelated to the target operator or provably unused.
- Check wrapper dtype guards and unsupported dtype behavior against the implemented kernel and tests.
- Check generated comments for stale hardcoded assumptions.
- Check accuracy tests for meaningful reference behavior, including NaN or statistical behavior when the operator semantics require it.
- Check benchmark subclasses and input generation before changing benchmark code.
- For fused or custom operators, check for a concrete downstream model or framework use case.
- For inplace operators, check PyTorch return-alias semantics and device behavior.
