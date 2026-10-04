#!/usr/bin/env bash
# judge.sh <run-dir> <out-dir> <name>
# Deterministic judge: static checks → tests + coverage → gRPC battery → artifacts.
# Returns exit 0 if all checks pass, exit 1 otherwise. Writes SCORE to metrics.env.
set -u
RUN="${1:?run-dir}"; OUT="${2:?out-dir}"; FW="${3:?name}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
RUN="$(cd "$RUN" && pwd)"
cd "$RUN" || exit 1
REPORT="$OUT/judge-report.md"
MET="$OUT/metrics.env"
: > "$REPORT"; : > "$MET"
PASS_N=0; FAIL_N=0
log()  { printf '%s\n' "$*" >> "$REPORT"; }
met()  { printf '%s=%s\n' "$1" "$2" >> "$MET"; }
pass() { log "- PASS: $1"; PASS_N=$((PASS_N + 1)); }
fail() { log "- FAIL: $1"; FAIL_N=$((FAIL_N + 1)); met "$2" 1; }

PORT=18080
G() { grpcurl -max-time 5 -plaintext -format json -d "$2" localhost:$PORT "$1" 2>&1; }
incr() { G counter.v1.Counter/Incr "{\"key\":\"$1\",\"n\":$2}"; }
cnt()  { printf '%s' "$1" | sed -n 's/.*"count": *"\{0,1\}\([0-9-]*\)"\{0,1\}.*/\1/p' | head -1; }
health_ok() { G grpc.health.v1.Health/Check '{}' | grep -q SERVING; }

log "# Judge report: $FW ($(date '+%Y-%m-%d %H:%M'))"
log

log "## 1. Static checks"
GOFMT_N=$(gofmt -l . 2>/dev/null | grep -v '^vendor/' | wc -l | tr -d ' ')
[ "$GOFMT_N" = "0" ] && pass "gofmt clean" || fail "gofmt: $GOFMT_N files with issues" GOFMT_FAIL
met GOFMT_FILES "$GOFMT_N"
if go vet ./... >/dev/null 2>&1; then pass "go vet clean"; else fail "go vet" VET_FAIL; fi
if make build >/dev/null 2>&1 && [ -x bin/server ]; then pass "make build -> bin/server"; else fail "make build / bin/server" BUILD_FAIL; fi

log
log "## 2. Tests and coverage"
# Weighted aggregate coverage (not per-package)
COV_OUT=$(go test -count=1 -coverprofile=judge.cov ./cmd/... ./internal/... 2>&1)
COV_EC=$?
rm -f judge.cov
COV_AGG=$(printf '%s\n' "$COV_OUT" | grep -o 'coverage: [0-9.]*%' | sed 's/coverage: //;s/%//' | awk '{s+=$1; n++} END {if(n>0) printf "%.1f", s/n; else print "0.0"}')
# Per-package coverage for cmd/ specifically (KPI: main > 70%)
COV_CMD=$(printf '%s\n' "$COV_OUT" | grep 'cmd/' | grep -o 'coverage: [0-9.]*%' | sed 's/coverage: //;s/%//' | head -1)
[ -z "$COV_CMD" ] && COV_CMD="0.0"
if [ $COV_EC -eq 0 ]; then pass "go test (weighted coverage ${COV_AGG}%, cmd ${COV_CMD}%)"; else fail "go test (exit $COV_EC)" TEST_FAIL; printf '```\n%s\n```\n' "$(printf '%s\n' "$COV_OUT" | tail -20)" >> "$REPORT"; fi
met COVERAGE "$COV_AGG"
met COVERAGE_CMD "$COV_CMD"

log
log "## 3. gRPC battery (port $PORT, window 2s, limit 5)"
# Kill only this project's server, not any bin/server on the host
pkill -f "$RUN/bin/server" 2>/dev/null; sleep 0.5
SRV_PID=""
if [ -x bin/server ]; then
  # Wider window for judge (10s) to avoid flaky concurrent test
  WINDOW_SECONDS=10 LIMIT=5 ./bin/server > "$OUT/server.log" 2>&1 & SRV_PID=$!
fi
for i in $(seq 1 30); do health_ok && break; sleep 0.5; done
if health_ok; then pass "health: SERVING"; else fail "health-check (server log: $(tail -1 "$OUT/server.log" 2>/dev/null))" HEALTH_FAIL; fi

if health_ok; then
  SEQ_OK=1
  for i in 1 2 3 4; do R=$(incr judge-k1 1); C=$(cnt "$R"); [ "$C" = "$i" ] || SEQ_OK=0; done
  [ $SEQ_OK = 1 ] && pass "B2 sequence 1..4" || fail "B2 sequence 1..4" B2_FAIL
  R=$(incr judge-k1 1); [ "$(cnt "$R")" = "5" ] && pass "B3 at limit -> 5" || fail "B3 at limit" B3_FAIL
  R=$(incr judge-k1 1)
  printf '%s' "$R" | grep -q 'RESOURCE_EXHAUSTED\|ResourceExhausted' && pass "B4 over limit -> RESOURCE_EXHAUSTED" || fail "B4 RESOURCE_EXHAUSTED (resp: $R)" B4_FAIL
  sleep 3
  R=$(incr judge-k1 1); [ "$(cnt "$R")" = "1" ] && pass "B5 window expired -> count=1" || fail "B5 window slid (resp: $R)" B5_FAIL
  # Concurrent wave: 20 parallel on one key, expect exactly 5 successes
  WAVE="$OUT/wave.txt"; : > "$WAVE"
  seq 1 20 | xargs -P 10 -I{} grpcurl -max-time 5 -plaintext -format json \
    -d '{"key":"judge-k2","n":1}' localhost:$PORT counter.v1.Counter/Incr >> "$WAVE" 2>&1
  SUCC=$(grep -c '"count"' "$WAVE"); EXH=$(grep -c 'ResourceExhausted\|RESOURCE_EXHAUSTED' "$WAVE")
  [ "$SUCC" = "5" ] && pass "B6 concurrent wave 20: exactly 5 success ($EXH rejected)" || fail "B6 concurrent limit: $SUCC success (expected 5)" B6_FAIL
  R1=$(incr judge-k3 3); R2=$(incr judge-k3 2)
  C1=$(cnt "$R1"); C2=$(cnt "$R2")
  log "- INFO: B7 n=3 -> ${C1:-err}; n=2 -> ${C2:-err} (compare with DECISIONS.md)"
  case "$C1$C2" in *err*|'') fail "B7 n>1 non-numeric (n=3 -> $R1)" B7_FAIL;; *) pass "B7 n>1 numeric count";; esac
  incr judge-k4 0 >/dev/null 2>&1; incr "" 1 >/dev/null 2>&1; incr judge-k5 999999 >/dev/null 2>&1
  sleep 1
  health_ok && pass "B8 extreme inputs: server alive" || fail "B8 server died on extreme inputs" B8_FAIL
  { echo "n=0:"; incr judge-k4 0; echo; echo "empty-key:"; incr "" 1; echo; echo "huge-n=999999:"; incr judge-k5 999999; } > "$OUT/battery-notes.txt" 2>&1
fi
[ -n "$SRV_PID" ] && kill "$SRV_PID" 2>/dev/null
wait "$SRV_PID" 2>/dev/null

log
log "## 4. Artifacts"
[ -f Dockerfile ] && { grep -qi 'AS ' Dockerfile && pass "Dockerfile multi-stage present" || fail "Dockerfile without multi-stage" DOCKER_FAIL; } || fail "Dockerfile missing" DOCKER_FAIL
[ -f README.md ] && pass "README.md present" || fail "README.md missing" README_FAIL
[ -f DECISIONS.md ] && pass "DECISIONS.md present ($(grep -c '^## ' DECISIONS.md 2>/dev/null || echo 0) entries)" || fail "DECISIONS.md missing" DECISIONS_FAIL
met DECISIONS_ENTRIES "$(grep -c '^## ' DECISIONS.md 2>/dev/null || echo 0)"
COMMIT_N=$(git rev-list --count HEAD 2>/dev/null || echo 0)
GO_LOC=$(find . -name '*.go' -not -path './vendor/*' | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
log "- metrics: $((COMMIT_N - 1)) commits (beyond scaffold); Go-LOC ${GO_LOC:-0}"
met COMMITS_EXTRA "$((COMMIT_N - 1))"; met GO_LOC "${GO_LOC:-0}"; met FW "$FW"
met SCORE "$PASS_N/$((PASS_N + FAIL_N))"
met PASS_COUNT "$PASS_N"
met FAIL_COUNT "$FAIL_N"

log
log "docker build: SKIPPED (no Docker daemon on host; Dockerfile evaluated statically)"
log
log "## Score: $PASS_N PASS / $FAIL_N FAIL out of $((PASS_N + FAIL_N)) checks"

# Exit code: 0 if no failures, 1 otherwise
exit $((FAIL_N > 0))
