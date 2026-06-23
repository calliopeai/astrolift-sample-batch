#!/usr/bin/env python3
"""seed.py — the one-off task entrypoint for astrolift-sample-batch (spec 42, R6).

A minimal, real one-shot "seed/migrate" job: it logs the spec 42 §3.1
diagnostic block, runs a short simulated migration (a few named steps), and
exits 0. It is not rescheduled — it runs to completion once.

This is what the manifest ``task.toml`` invokes via the top-level ``[[tasks]]``
shorthand (``command=["python", "seed.py"]``), which the backend parser
desugars into a ``kind="task"`` workload — a bare ``batch/v1`` Job
(``completions=1``, ``backoffLimit=0``), with no schedule and no concurrency
policy (see ``_desugar_task`` in ``astrolift_manifest/parser.py``).

No HTTP server: the task runs to completion and the Job controller tracks
success/failure via the exit code.

Standard library only.
"""

from __future__ import annotations

import sys
import time

import _diagnostics as diag

APP = "sample-batch"
KIND = "task"

# The simulated "migration" — a fixed, ordered list of named steps. Real
# enough to look like a seed/migrate job in logs, cheap enough to finish in
# well under a second. Each step sleeps briefly so the run has observable
# duration without delaying the campaign's VERIFY step.
STEPS: tuple[str, ...] = (
    "connect",
    "create schema",
    "apply migrations",
    "seed reference data",
    "verify row counts",
)


def run_migration() -> int:
    """Run the simulated seed/migrate steps, logging each, return the count.

    Logs one structured line per step to stderr so the task's progress is
    visible in the pod log stream. Returns the number of steps completed so
    the caller can report it.
    """
    for i, step in enumerate(STEPS, start=1):
        print(
            f'level=info msg="seed step" step={i}/{len(STEPS)} action={step!r}',
            file=sys.stderr,
            flush=True,
        )
        # A short pause per step so the job has a realistic, observable
        # duration. Total well under one second.
        time.sleep(0.05)
    return len(STEPS)


def main() -> int:
    diag.log_banner(APP, KIND)
    # Diagnostic block first so it is present even if a step below fails.
    diag.log_diagnostic_block(APP, KIND)
    completed = run_migration()
    print(
        f'level=info msg="seed complete" steps_completed={completed} status=ok',
        file=sys.stderr,
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
