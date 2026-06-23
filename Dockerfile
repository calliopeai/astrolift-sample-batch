# astrolift-sample-batch fixture (spec 42, R6): cron + one-off task.
#
# Two non-HTTP, run-to-completion Python entrypoints share one image:
#   * chronicle.py — the cronjob entrypoint, and the default CMD below.
#   * seed.py      — the one-off task entrypoint; the task manifest overrides
#                    the command (command=["python", "seed.py"]).
#
# Stdlib-only jobs, so there is nothing to pip install. Build context is the
# repo root:
#
#   docker build -t astrolift-sample-batch .
#   docker run --rm astrolift-sample-batch              # one chronicle tick
#   docker run --rm astrolift-sample-batch python seed.py   # one seed run
FROM python:3.12-slim

# GIT_SHA is supplied by CI (--build-arg GIT_SHA=<sha>); defaults to "dev" for
# local builds so the image is still self-describing. BUILT_AT is the build
# timestamp. Both surface in the spec 42 §3.1 diagnostic "build" block via the
# matching env vars below.
ARG GIT_SHA=dev
ARG BUILT_AT=""

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    GIT_SHA=${GIT_SHA} \
    BUILT_AT=${BUILT_AT} \
    LOG_LEVEL=info

WORKDIR /app

# Just the three source files — no dependencies to install.
COPY _diagnostics.py chronicle.py seed.py ./

# Default command is the cronjob entrypoint. The one-off task manifest overrides
# this with command=["python", "seed.py"]; the cron manifest sets it explicitly
# to command=["python", "chronicle.py"] (== this default).
CMD ["python", "chronicle.py"]
