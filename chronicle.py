#!/usr/bin/env python3
"""chronicle.py — the cronjob entrypoint for astrolift-sample-batch (spec 42, R6).

A minimal, real batch job: on each scheduled run it appends a single
timestamped line to stdout (and, if ``CHRONICLE_LOG_PATH`` is set, to that
file as well), logs the spec 42 §3.1 diagnostic block, and exits 0.

This is what the manifest ``cron.toml`` invokes — ``kind="cronjob"`` with
``command=["python", "chronicle.py"]`` — and it is the image's default ``CMD``,
so ``docker run`` with no override runs a single chronicle tick to completion.

No HTTP server: the cronjob runs to completion every tick. The platform's
k8s CronJob controller schedules it (``schedule`` / ``concurrency_policy`` from
the manifest); success/failure is the process exit code.

Standard library only.
"""

from __future__ import annotations

import sys

import _diagnostics as diag

APP = "sample-batch"
KIND = "cronjob"


def write_chronicle_line(now_iso: str) -> str:
    """Build the chronicle line and append it to stdout + optional file.

    The line is the unit of real work this cronjob performs: a single
    append-only, timestamped record (host + commit so successive ticks are
    distinguishable in a shared log). Returns the line written.

    If ``CHRONICLE_LOG_PATH`` is set, the same line is appended there too, so
    the fixture can prove a mounted volume / writable path survives across
    scheduled runs. A failure to write the file is fatal (non-zero exit) rather
    than silently swallowed — a cronjob that can't write its log is not healthy,
    and the spec's "errors should never pass silently" rule applies.
    """
    line = f"{now_iso} chronicle tick host={diag.commit()} app={APP}"
    print(line, flush=True)

    import os

    log_path = os.environ.get("CHRONICLE_LOG_PATH")
    if log_path:
        # Append mode so every scheduled run accretes one line; create parent
        # dirs so a freshly-mounted empty volume works on the first tick.
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        print(
            f'level=info msg="appended chronicle line" path={log_path}',
            file=sys.stderr,
            flush=True,
        )
    return line


def main() -> int:
    diag.log_banner(APP, KIND)
    # Diagnostic block first so it is present even if the work below fails.
    block = diag.log_diagnostic_block(APP, KIND)
    write_chronicle_line(block["now"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
