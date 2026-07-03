# Final Validation Agent

Reads the general, test benchmark, and final PR specs.

This agent performs the last target-branch checks: file set, static rules, formatting, accuracy test, core benchmark, benchmark summary, explicit staging, commit, branch publication, and initial PR creation.

Stop on missing data, failed tests, failed benchmark, zero benchmark cases, or incomplete PR body.
