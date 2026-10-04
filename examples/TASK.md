# Assignment: sliding-counter (gRPC, Go)

Design and implement a gRPC service `sliding-counter` in Go — an event counter
with a sliding window and per-key rate limiting.

## Contract (mandatory, exact)

proto3, package `counter.v1`, service `Counter`:

```proto
message IncrRequest { string key = 1; int64 n = 2; }
message IncrResponse { int64 count = 1; }
service Counter { rpc Incr(IncrRequest) returns (IncrResponse); }
```

- Enable gRPC server reflection and standard `grpc.health.v1.Health`.
- Configuration via environment: `PORT` (default `18080`),
  `WINDOW_SECONDS` (default `2`), `LIMIT` (default `5`).

## Behavior

- `Incr` registers events for key `key` within a sliding window of
  `WINDOW_SECONDS` seconds and returns `count` — the number of events for the
  key within the active window.
- At most `LIMIT` events per key within the window; requests exceeding the limit
  return gRPC status `RESOURCE_EXHAUSTED`.

All behavioral ambiguities are your decisions. Record each one in `DECISIONS.md`:
one entry per ambiguity, format "question — decision — rationale".

## Deliverables

1. Go module; `make build` produces `bin/server`; `make run` starts it;
   `make test` runs tests.
2. `go test -race ./...` green; concurrent scenarios required.
3. `go vet` and `gofmt` clean.
4. `Dockerfile` multi-stage (build + minimal runtime).
5. `README.md`: build, run, test, all environment variables.
6. Atomic git commits throughout; final result on branch `main`.

## Process

Work as a team: planning before code, task decomposition, implementation,
testing, review. Preserve process artifacts (plan, decomposition) in the
repository alongside the code.
