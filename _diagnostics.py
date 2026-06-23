"""Shared diagnostic block for the astrolift-sample-batch fixtures (spec 42 §3.1).

The two entrypoints in this repo are non-HTTP, run-to-completion jobs:

  * ``chronicle.py`` — the cronjob entrypoint (manifest ``kind="cronjob"``).
  * ``seed.py``      — the one-off task entrypoint (manifest ``[[tasks]]``).

Spec 42 §3.1 says non-HTTP fixtures (cronjob / task / agent / worker) "log the
same diagnostic block to stdout on each run" as the HTTP ``GET /debug`` surface.
Both entrypoints emit byte-identical block shapes, so the logic lives here once
rather than being copy-pasted — there are two real callers of a non-trivial,
contract-defined block, which is the point at which a shared helper earns its
keep.

Standard library only: these jobs carry no third-party dependencies.
"""

from __future__ import annotations

import json
import os
import socket
import sys
from datetime import datetime, timezone

# The image this repo publishes (spec 42 §3.2; built + pushed by
# .github/workflows/build.yml). Reported in the diagnostic "build" block.
IMAGE = "docker.io/calliopeai/astrolift-sample-batch"

# Environment variables we are willing to report as "seen" in the diagnostic
# block. We deliberately enumerate an allow-list rather than dump os.environ,
# so secrets injected by the platform are never echoed back (spec 42 §3.1:
# "non-secret keys + presence of binding keys, values redacted"). These
# fixtures attach no managed services, so there are no binding keys to add.
NON_SECRET_ENV_KEYS: tuple[str, ...] = (
    "LOG_LEVEL",
    "GIT_SHA",
    "HOSTNAME",
    "ENV",
    # chronicle.py honours this to also append its line to a file (see module
    # docstring there); reported so operators can confirm it was wired.
    "CHRONICLE_LOG_PATH",
)


def commit() -> str:
    """Build commit reported as ``version`` / ``build.commit``.

    Populated from the ``GIT_SHA`` build-arg baked into the image by the
    Dockerfile; falls back to ``"dev"`` for local runs so the block is always
    self-describing.
    """
    return os.environ.get("GIT_SHA") or "dev"


def now_iso() -> str:
    """Current instant as an RFC 3339 / ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def diagnostic_block(app: str, kind: str) -> dict:
    """Build the spec 42 §3.1 diagnostic block for a non-HTTP fixture.

    ``app`` is the fixture name (e.g. ``"sample-batch"``); ``kind`` is the
    manifest workload kind this entrypoint runs as (``"cronjob"`` for
    chronicle, ``"task"`` for seed). ``uptime_s`` and ``bindings`` from the
    HTTP variant are omitted: a batch job's lifetime is the run itself, and no
    managed services are attached. The shape is otherwise the HTTP ``/debug``
    payload.
    """
    seen = sorted(k for k in NON_SECRET_ENV_KEYS if k in os.environ)
    return {
        "app": app,
        "version": commit(),
        "kind": kind,
        "hostname": socket.gethostname(),
        "now": now_iso(),
        "env_seen": seen,
        "build": {
            "image": IMAGE,
            "built_at": os.environ.get("BUILT_AT", ""),
            "commit": commit(),
        },
    }


def log_diagnostic_block(app: str, kind: str) -> dict:
    """Emit the diagnostic block to stdout as one pretty-printed JSON object.

    Printed to stdout (not stderr) so it lands in the pod log stream that the
    platform's VERIFY step reads. Returns the block so callers can reuse the
    already-computed values (e.g. the ``now`` timestamp) without recomputing.
    """
    block = diagnostic_block(app, kind)
    # flush so the block is visible even if the job exits immediately after.
    print(json.dumps(block, indent=2), flush=True)
    return block


def log_banner(app: str, kind: str) -> None:
    """Structured startup banner (spec 42 §3.1), logged at boot to stderr.

    Mirrors the ``level=info msg=...`` banner the HTTP fixtures log so the very
    first log line of every run identifies app, version, kind, hostname, and
    that no managed-service bindings are attached.
    """
    print(
        f'level=info msg="starting astrolift-{app}" '
        f"app={app} version={commit()} kind={kind} "
        f"hostname={socket.gethostname()} bindings=none",
        file=sys.stderr,
        flush=True,
    )
