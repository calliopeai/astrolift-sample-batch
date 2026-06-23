# astrolift-sample-batch

Cron + one-off-task fixture for the Astrolift validation campaign
([spec 42](../../specs/42-sample-fixtures.md), R6). Two **minimal, real Python
batch jobs** — no HTTP server; each runs to completion — sharing one image:

| Entrypoint | Workload kind | Manifest | What it does |
|---|---|---|---|
| `chronicle.py` | `cronjob` (k8s CronJob) | `manifests/cron.toml` | Appends one timestamped line per scheduled tick; the image's default `CMD`. |
| `seed.py` | `task` (one-shot `batch/v1` Job) | `manifests/task.toml` | A one-off "seed/migrate" job: runs a few named steps once, exits 0. |

This repo is the home of two coverage-matrix cells (spec 42 §6): **cronjob** and
**task (one-off)**.

## Topology

```
        ┌──────────────────────────────┐        ┌──────────────────────────────┐
        │  CronJob  (cron.toml)        │        │  Job  (task.toml)            │
        │  schedule = "0 * * * *"      │        │  completions=1, backoffLimit=0│
        │  concurrency_policy = forbid │        │  one-shot, not rescheduled    │
        │  command = python chronicle.py│       │  command = python seed.py     │
        └──────────────┬───────────────┘        └──────────────┬───────────────┘
                       │ every hour                             │ on demand
                       ▼                                        ▼
            appends a timestamped line                 runs 5 migrate steps,
            to stdout (+ optional file),               logs the diagnostic
            logs the diagnostic block,                 block, exits 0
            exits 0
```

Both are **non-HTTP, run-to-completion** jobs. There is no `/health` or `/debug`
endpoint — instead, per spec 42 §3.1 ("non-HTTP fixtures log the same diagnostic
block to stdout on each run"), each run prints the diagnostic block to stdout.

## The diagnostic block (spec 42 §3.1)

On every run, both entrypoints:

1. Log a **structured startup banner** to **stderr**:
   ```
   level=info msg="starting astrolift-sample-batch" app=sample-batch version=<sha> kind=<cronjob|task> hostname=<pod> bindings=none
   ```
2. Print the **diagnostic block** to **stdout** as one JSON object:
   ```json
   {
     "app": "sample-batch",
     "version": "<git-sha>",
     "kind": "cronjob",
     "hostname": "<pod>",
     "now": "<iso-8601-utc>",
     "env_seen": ["GIT_SHA", "HOSTNAME", "LOG_LEVEL"],
     "build": { "image": "docker.io/calliopeai/astrolift-sample-batch", "built_at": "<iso>", "commit": "<git-sha>" }
   }
   ```
   `env_seen` is an **allow-list** of non-secret keys that are present — the
   full environment is never dumped, so platform-injected secrets are never
   echoed. No managed services are attached, so the HTTP variant's `bindings`
   object and `uptime_s` (a batch job's lifetime *is* the run) are omitted.

Then each does its specific work:

- **`chronicle.py`** prints its **timestamped tick line** to stdout *after* the
  block — this line is the cronjob's actual product:
  ```
  2026-06-23T01:10:16Z chronicle tick host=<sha> app=sample-batch
  ```
  So a consumer reads the diagnostic block as the **first JSON object** on
  stdout; the tick line follows. If `CHRONICLE_LOG_PATH` is set, the same line
  is also appended to that file (handy for proving a mounted volume persists
  across scheduled runs).
- **`seed.py`** logs its 5 migrate steps to **stderr** (its stdout is the pure
  diagnostic block) and exits 0.

## Run it locally

```sh
docker build -t astrolift-sample-batch .

# Default CMD — one chronicle cronjob tick, to completion:
docker run --rm astrolift-sample-batch

# Command override — one seed/migrate task run:
docker run --rm astrolift-sample-batch python seed.py
```

Or without Docker (stdlib only, no dependencies):

```sh
GIT_SHA=dev python3 chronicle.py
GIT_SHA=dev python3 seed.py
```

### Environment

| Var | Used by | Effect |
|---|---|---|
| `GIT_SHA` | both | Reported as `version` / `build.commit`. Baked into the image by CI; defaults to `dev`. |
| `BUILT_AT` | both | Reported as `build.built_at`. Set by CI. |
| `LOG_LEVEL` | both | Reported in `env_seen`. Defaults to `info` in the image. |
| `CHRONICLE_LOG_PATH` | `chronicle.py` | If set, each tick line is also appended to this file. |

## Manifests

Authored against the grounded backend schema (spec 42 §4; verified against
`astrolift_manifest/parser.py`).

- **`manifests/cron.toml`** — `[[workloads]]` `kind="cronjob"`. The parser
  **requires** `schedule` for a cronjob, and `concurrency_policy` must be one of
  `{forbid, queue, replace}`; both are set explicitly (`"0 * * * *"`, `forbid`).
  The container sets `command=["python","chronicle.py"]`.
- **`manifests/task.toml`** — top-level `[[tasks]]` shorthand. The parser
  desugars this into a `kind="task"` workload — a bare `batch/v1` Job
  (`completions=1`, `backoffLimit=0`) with **no schedule and no concurrency
  policy**. The container is implicitly `is_primary`, `port=0`,
  `healthcheck="none"`; `command=["python","seed.py"]`.

`image_ref` in both points at the pre-built Docker Hub image; deploy pins the
deterministic `main-<sha7>` tag (no platform build this increment, spec 42 §5).

## Image build / publish

`.github/workflows/build.yml` builds and pushes
`docker.io/calliopeai/astrolift-sample-batch` tagged `main-<sha7>` **and**
`latest` on every push to `main`, using the org-level
`DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` secrets (mirrors
`astrolift-agents/.github/workflows/build-images.yml`). The short SHA and build
timestamp are passed as `GIT_SHA` / `BUILT_AT` build-args and surface in the
diagnostic `build` block.

## Variant → matrix-cell map (spec 42 §6)

| Variant | Gamut cell |
|---|---|
| `manifests/cron.toml` | cronjob |
| `manifests/task.toml` | task (one-off) |
