# Implementation Review Checklist

Use this checklist to enrich your workflow todos and verify the work:

- Locate the target implementation, accuracy test, benchmark, and registration-adjacent files.
- Before repairing implementation, tests, or benchmarks, branch on `IS_ATEN`. For `IS_ATEN=true`, confirm the resolved target has an exact `torch.ops.aten` schema. For `IS_ATEN=false`, confirm the prompt provides an explicitly documented fused/custom target, public API, and PyTorch reference expression. If the required target evidence is missing, block immediately, report the evidence and closest candidate schemas or references for human repair, and do not retarget to the nearest ATen schema automatically.
- Check for duplicate or dead generated functions and identify only code that is unrelated to the target operator or provably unused.
- Check wrapper dtype guards and unsupported dtype behavior against the implemented kernel and tests.
- Check generated comments for stale hardcoded assumptions.
- Check special-function or numerically sensitive kernels for unexplained numeric constants and boundary-value behavior.
- Check public wrappers for unimplemented stubs before registering or exporting them.
- Check accuracy tests for meaningful reference behavior, including NaN or statistical behavior when the operator semantics require it.
- Check benchmark subclasses and input generation before changing benchmark code.
- For fused or custom operators, check for a concrete downstream model or framework use case.
- For inplace operators, check PyTorch return-alias semantics and device behavior.
