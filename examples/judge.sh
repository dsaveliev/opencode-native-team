#!/usr/bin/env bash
# judge.sh <run-dir> <out-dir> <fw-name>
# Единый судья bake-off: статика -> тесты -> батарея grpcurl -> артефакты.
set -u
RUN="${1:?run-dir}"; OUT="${2:?out-dir}"; FW="${3:?fw}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
RUN="$(cd "$RUN" && pwd)"
cd "$RUN" || exit 1
REPORT="$OUT/judge-report.md"
MET="$OUT/metrics.env"
: > "$REPORT"; : > "$MET"
log()  { printf '%s\n' "$*" >> "$REPORT"; }
met()  { printf '%s=%s\n' "$1" "$2" >> "$MET"; }
pass() { log "- PASS: $1"; }
fail() { log "- FAIL: $1"; met "$2" 1; }

PORT=18080
G() { grpcurl -max-time 5 -plaintext -format json -d "$2" localhost:$PORT "$1" 2>&1; }
incr() { G counter.v1.Counter/Incr "{\"key\":\"$1\",\"n\":$2}"; }
cnt()  { printf '%s' "$1" | sed -n 's/.*"count": *"\{0,1\}\([0-9-]*\)"\{0,1\}.*/\1/p' | head -1; }
health_ok() { G grpc.health.v1.Health/Check '{}' | grep -q SERVING; }

log "# Judge report: $FW ($(date '+%Y-%m-%d %H:%M'))"
log

log "## 1. Статика и сборка"
GOFMT_N=$(gofmt -l . 2>/dev/null | grep -v '^vendor/' | wc -l | tr -d ' ')
[ "$GOFMT_N" = "0" ] && pass "gofmt чист" || fail "gofmt: файлов с проблемами $GOFMT_N" GOFMT_FAIL
met GOFMT_FILES "$GOFMT_N"
if go vet ./... >/dev/null 2>&1; then pass "go vet чист"; else fail "go vet" VET_FAIL; fi
if make build >/dev/null 2>&1 && [ -x bin/server ]; then pass "make build -> bin/server"; else fail "make build / bin/server" BUILD_FAIL; fi

log
log "## 2. Тесты и покрытие"
TEST_OUT=$(go test -race -cover ./... 2>&1); TEST_EC=$?
COV=$(printf '%s\n' "$TEST_OUT" | grep -o 'coverage: [0-9.]*%' | tail -1 | grep -o '[0-9.]*' || echo "0")
if [ $TEST_EC -eq 0 ]; then pass "go test -race зелёные (coverage ${COV}%)"; else fail "go test -race (exit $TEST_EC)" TEST_FAIL; printf '```\n%s\n```\n' "$(printf '%s\n' "$TEST_OUT" | tail -20)" >> "$REPORT"; fi
met COVERAGE "${COV:-0}"

log
log "## 3. Батарея grpcurl (порт $PORT, окно 2с, лимит 5)"
pkill -f 'bin/server' 2>/dev/null; sleep 0.5
SRV_PID=""
if [ -x bin/server ]; then
  ./bin/server > "$OUT/server.log" 2>&1 & SRV_PID=$!
fi
for i in $(seq 1 30); do health_ok && break; sleep 0.5; done
if health_ok; then pass "health: SERVING"; else fail "health-check (лог сервера: $(tail -1 "$OUT/server.log" 2>/dev/null))" HEALTH_FAIL; fi

if health_ok; then
  # B2: четыре инкремента ниже лимита -> 1..4
  SEQ_OK=1
  for i in 1 2 3 4; do R=$(incr bake-k1 1); C=$(cnt "$R"); [ "$C" = "$i" ] || SEQ_OK=0; done
  [ $SEQ_OK = 1 ] && pass "B2 последовательность 1..4 по ключу" || fail "B2 последовательность 1..4" B2_FAIL
  # B3: пятый — ровно на лимите, разрешён
  R=$(incr bake-k1 1); [ "$(cnt "$R")" = "5" ] && pass "B3 пятый инкремент (ровно лимит) -> 5" || fail "B3 ровно на лимите" B3_FAIL
  # B4: шестой — RESOURCE_EXHAUSTED
  R=$(incr bake-k1 1)
  printf '%s' "$R" | grep -q 'RESOURCE_EXHAUSTED\|ResourceExhausted' && pass "B4 сверх лимита -> RESOURCE_EXHAUSTED" || fail "B4 RESOURCE_EXHAUSTED (ответ: $R)" B4_FAIL
  # B5: окно истекло -> снова можно, count сброшен
  sleep 3
  R=$(incr bake-k1 1); [ "$(cnt "$R")" = "1" ] && pass "B5 окно истекло -> count=1" || fail "B5 окно скользнуло (ответ: $R)" B5_FAIL
  # B6: 20 параллельных на один ключ -> ровно 5 успехов (инвариант окна/лимита)
  WAVE="$OUT/wave.txt"; : > "$WAVE"
  seq 1 20 | xargs -P 10 -I{} grpcurl -plaintext -format json \
    -d '{"key":"bake-k2","n":1}' localhost:$PORT counter.v1.Counter/Incr >> "$WAVE" 2>&1
  SUCC=$(grep -c '"count"' "$WAVE"); EXH=$(grep -c 'ResourceExhausted\|RESOURCE_EXHAUSTED' "$WAVE")
  [ "$SUCC" = "5" ] && pass "B6 параллельная волна 20: успехов ровно 5 (отказов $EXH)" || fail "B6 конкурентный лимит: успехов $SUCC из 20 (ожидалось 5)" B6_FAIL
  # B7: n>1 — самосогласованность (значения фиксируем для сверки с DECISIONS.md)
  R1=$(incr bake-k3 3); R2=$(incr bake-k3 2)
  C1=$(cnt "$R1"); C2=$(cnt "$R2")
  log "- INFO: B7 n=3 -> ${C1:-err}; n=2 -> ${C2:-err} (сверить с DECISIONS.md)"
  case "$C1$C2" in *err*|'') fail "B7 n>1 нечисловой ответ (n=3 -> $R1)" B7_FAIL;; *) pass "B7 n>1 возвращает числовой count";; esac
  # B8: экстремальные входы не роняют сервер
  incr bake-k4 0 >/dev/null 2>&1; incr "" 1 >/dev/null 2>&1; incr bake-k5 999999 >/dev/null 2>&1
  sleep 1
  health_ok && pass "B8 экстремальные входы: сервер жив" || fail "B8 сервер умер на экстремальных входах" B8_FAIL
  log "- INFO: поведение n=0/пустой ключ/huge-n — в $OUT/battery-notes (сверить с DECISIONS.md)"
  { echo "n=0:"; incr bake-k4 0; echo; echo "empty-key:"; incr "" 1; echo; echo "huge-n:"; incr bake-k5 1; } > "$OUT/battery-notes.txt" 2>&1
fi
[ -n "$SRV_PID" ] && kill "$SRV_PID" 2>/dev/null
wait "$SRV_PID" 2>/dev/null

log
log "## 4. Артефакты"
[ -f Dockerfile ] && { grep -qi 'AS ' Dockerfile && pass "Dockerfile multi-stage присутствует" || fail "Dockerfile без multi-stage" DOCKER_FAIL; } || fail "Dockerfile отсутствует" DOCKER_FAIL
[ -f README.md ] && pass "README.md присутствует" || fail "README.md отсутствует" README_FAIL
[ -f DECISIONS.md ] && pass "DECISIONS.md присутствует ($(grep -c '^## ' DECISIONS.md 2>/dev/null || echo 0) записей)" || fail "DECISIONS.md отсутствует" DECISIONS_FAIL
met DECISIONS_ENTRIES "$(grep -c '^## ' DECISIONS.md 2>/dev/null || echo 0)"
COMMIT_N=$(git rev-list --count HEAD 2>/dev/null || echo 0)
GO_LOC=$(find . -name '*.go' -not -path './vendor/*' | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
log "- метрики: коммитов $((COMMIT_N - 1)) (сверх scaffold); Go-LOC ${GO_LOC:-0}"
met COMMITS_EXTRA "$((COMMIT_N - 1))"; met GO_LOC "${GO_LOC:-0}"
met FW "$FW"
log
log "docker build: SKIPPED (docker недоступен на хосте; Dockerfile оценён статически)"
log
log "Итог judge: сбоев секций — см. metrics.env (все *_FAIL)"
cp "$MET" "$OUT/metrics.env"
echo "JUDGE DONE: $FW"
