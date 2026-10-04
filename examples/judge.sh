#!/usr/bin/env bash
# judge.sh <run-dir> <out-dir> <name>
# Deterministic judge: static → tests + coverage → gRPC battery → artifacts.
# Exit 0 = all pass. Writes SCORE to metrics.env.
set -u
RUN="${1:?run-dir}"; OUT="${2:?out-dir}"; FW="${3:?name}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"; RUN="$(cd "$RUN" && pwd)"
cd "$RUN" || exit 1
REPORT="$OUT/judge-report.md"; MET="$OUT/metrics.env"
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
# True weighted coverage via go tool cover -func (statement-weighted)
COV_FILE="$OUT/.judge.cov"
rm -f "$COV_FILE"
COV_RAW=$(go test -count=1 -race -coverprofile="$COV_FILE" -coverpkg=./... ./cmd/... ./internal/... 2>&1)
COV_EC=$?
if [ $COV_EC -eq 0 ] && [ -f "$COV_FILE" ]; then
  COV_AGG=$(go tool cover -func="$COV_FILE" 2>/dev/null | awk '/^total:/{gsub("%","",$3); print $3}')
  [ -z "$COV_AGG" ] && COV_AGG="0.0"
  COV_CMD=$(go tool cover -func="$COV_FILE" 2>/dev/null | awk '/\/cmd\//{gsub("%","",$NF); s+=$NF; n++} END{if(n)printf "%.1f", s/n; else print "0.0"}')
  pass "go test -race (weighted coverage ${COV_AGG}%, cmd ${COV_CMD}%)"
else
  COV_AGG="0.0"; COV_CMD="0.0"
  fail "go test -race (exit $COV_EC)" TEST_FAIL
  printf '```\n%s\n```\n' "$(printf '%s\n' "$COV_RAW" | tail -20)" >> "$REPORT"
fi
rm -f "$COV_FILE"
met COVERAGE "$COV_AGG"
met COVERAGE_CMD "$COV_CMD"

log
log "## 3. gRPC battery (port $PORT, defaults: window 2s, limit 5)"
# Kill only this project's server
pkill -f "$RUN/bin/server" 2>/dev/null; sleep 0.5
SRV_PID=""
if [ -x bin/server ]; then
  # Default window (2s) per TASK.md — the judge tests the documented contract
  ./bin/server > "$OUT/server.log" 2>&1 & SRV_PID=$!
fi
for i in $(seq 1 30); do health_ok && break; sleep 0.5; done
if health_ok; then pass "health: SERVING"; else fail "health-check (log: $(tail -1 "$OUT/server.log" 2>/dev/null))" HEALTH_FAIL; fi

if health_ok; then
  # B2: sequence 1..4 (must complete within 2s window — grpcurl startup ~50ms each, ~1.2s total)
  SEQ_OK=1
  for i in 1 2 3 4; do R=$(incr judge-k1 1); C=$(cnt "$R"); [ "$C" = "$i" ] || SEQ_OK=0; done
  [ $SEQ_OK = 1 ] && pass "B2 sequence 1..4" || fail "B2 sequence 1..4" B2_FAIL
  # B3: 5th = exactly at limit
  R=$(incr judge-k1 1); [ "$(cnt "$R")" = "5" ] && pass "B3 at limit -> 5" || fail "B3 at limit" B3_FAIL
  # B4: 6th = rejected
  R=$(incr judge-k1 1)
  printf '%s' "$R" | grep -q 'RESOURCE_EXHAUSTED\|ResourceExhausted' && pass "B4 over limit -> RESOURCE_EXHAUSTED" || fail "B4 RESOURCE_EXHAUSTED (resp: $R)" B4_FAIL
  # B5: window expired (sleep 3 > 2s window)
  sleep 3
  R=$(incr judge-k1 1); [ "$(cnt "$R")" = "1" ] && pass "B5 window expired -> count=1" || fail "B5 window slid (resp: $R)" B5_FAIL
  # B6: concurrent wave — range check (grpcurl startup variance, not exact)
  WAVE="$OUT/wave.txt"; : > "$WAVE"
  seq 1 20 | xargs -P 10 -I{} grpcurl -max-time 5 -plaintext -format json \
    -d '{"key":"judge-k2","n":1}' localhost:$PORT counter.v1.Counter/Incr >> "$WAVE" 2>&1
  SUCC=$(grep -c '"count"' "$WAVE"); EXH=$(grep -c 'ResourceExhausted\|RESOURCE_EXHAUSTED' "$WAVE")
  if [ "$SUCC" -ge 5 ] && [ "$SUCC" -le 7 ]; then
    pass "B6 concurrent wave 20: ${SUCC} success, ${EXH} rejected (expected 5-7)"
  else
    fail "B6 concurrent limit: ${SUCC} success (expected 5-7)" B6_FAIL
  fi
  # B7: n>1 numeric
  R1=$(incr judge-k3 3); R2=$(incr judge-k3 2)
  C1=$(cnt "$R1"); C2=$(cnt "$R2")
  log "- INFO: B7 n=3 -> ${C1:-err}; n=2 -> ${C2:-err}"
  case "$C1$C2" in *err*|'') fail "B7 n>1 non-numeric" B7_FAIL;; *) pass "B7 n>1 numeric";; esac
  # B8: extreme inputs don't crash server
  incr judge-k4 0 >/dev/null 2>&1; incr "" 1 >/dev/null 2>&1; incr judge-k5 999999 >/dev/null 2>&1
  sleep 1
  health_ok && pass "B8 extreme inputs: server alive" || fail "B8 server died" B8_FAIL
  { echo "n=0:"; incr judge-k4 0; echo; echo "empty-key:"; incr "" 1; echo; echo "huge-n=999999:"; incr judge-k5 999999; } > "$OUT/battery-notes.txt" 2>&1
fi
[ -n "$SRV_PID" ] && kill "$SRV_PID" 2>/dev/null
wait "$SRV_PID" 2>/dev/null

log
log "## 4. Artifacts"
[ -f Dockerfile ] && { grep -qi 'AS ' Dockerfile && pass "Dockerfile multi-stage" || fail "Dockerfile without multi-stage" DOCKER_FAIL; } || fail "Dockerfile missing" DOCKER_FAIL
[ -f README.md ] && pass "README.md present" || fail "README.md missing" README_FAIL
[ -f DECISIONS.md ] && pass "DECISIONS.md present" || fail "DECISIONS.md missing" DECISIONS_FAIL
met DECISIONS_ENTRIES "$(grep -c '^## ' DECISIONS.md 2>/dev/null || echo 0)"
COMMIT_N=$(git rev-list --count HEAD 2>/dev/null || echo 0)
GO_LOC=$(find . -name '*.go' -not -path './vendor/*' | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
log "- $((COMMIT_N - 1)) commits beyond scaffold; ${GO_LOC:-0} Go LOC"
met COMMITS_EXTRA "$((COMMIT_N - 1))"; met GO_LOC "${GO_LOC:-0}"; met FW "$FW"
met SCORE "$PASS_N/$((PASS_N + FAIL_N))"
met PASS_COUNT "$PASS_N"; met FAIL_COUNT "$FAIL_N"

log
log "docker build: SKIPPED (no daemon on host; Dockerfile evaluated statically)"
log
log "## Score: $PASS_N PASS / $FAIL_N FAIL out of $((PASS_N + FAIL_N))"

exit $((FAIL_N > 0))
