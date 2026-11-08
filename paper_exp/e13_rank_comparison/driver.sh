#!/usr/bin/env bash
# E13 full calibration driver — submitted version cdcf9af, rules mode, strictly serial.
# Resumable: a case whose calib_runs/testNNN.stdout.log ends with the final
# "#END <n_expected>" frame is skipped. Outputs written through the testcase
# symlink into final_release_100 are MOVED to calib_runs/ right after each run.
set -u

CALIB=/home/joey123230/ICCAD_A/calib_cdcf9af
E13=/home/joey123230/ICCAD_A/Agent/paper_exp/e13_rank_comparison
RUNS=$E13/calib_runs
FINAL=/home/joey123230/ICCAD_A/final_release_100/final_release_100
PY=/home/joey123230/ICCAD_A/Agent/.venv/bin/python
ABC=/home/joey123230/ICCAD_A/abc/abc

mkdir -p "$RUNS"
echo "=== driver start $(date -Is) load=$(cut -d' ' -f1 /proc/loadavg)" >> "$RUNS/driver.log"

# -- step 1: symlink the 100 final cases into the worktree (skip existing) --
for i in $(seq -w 1 100); do
  c="test$i"
  if [ ! -e "$CALIB/testcase/$c" ]; then
    ln -s "$FINAL/$c" "$CALIB/testcase/$c"
  fi
done

# move run artifacts out of the shared final dir / worktree root
harvest() {
  local c="$1"
  if [ -f "$FINAL/$c/${c}_out.v" ]; then
    mv "$FINAL/$c/${c}_out.v" "$RUNS/${c}_out.v"
  fi
  if [ -f "$CALIB/$c.log" ]; then
    mv "$CALIB/$c.log" "$RUNS/$c.agent.log"
  fi
}

# -- step 2: run each case sequentially --
for i in $(seq -w 1 100); do
  c="test$i"
  LOG="$RUNS/$c.stdout.log"
  exp=$(grep -c . "$FINAL/$c/prompt.txt")

  if [ -f "$LOG" ]; then
    lastend=$(tail -n 3 "$LOG" | grep -Eo '^#END [0-9]+$' | tail -1 | awk '{print $2}')
    if [ "${lastend:-x}" = "$exp" ]; then
      harvest "$c"
      echo "skip $c (complete, $exp frames) $(date -Is)" >> "$RUNS/driver.log"
      continue
    fi
  fi

  echo "run  $c start $(date -Is) load=$(cut -d' ' -f1 /proc/loadavg)" >> "$RUNS/driver.log"
  t0=$SECONDS
  ( cd "$CALIB" && env ABC_BIN="$ABC" PYTHONHASHSEED=0 \
      timeout 2400 "$PY" scripts/run_local.py "testcase/$c" ) \
      > "$LOG.partial" 2> "$RUNS/$c.stderr.log"
  rc=$?
  echo "$rc" > "$RUNS/$c.rc"
  mv "$LOG.partial" "$LOG"
  harvest "$c"
  echo "run  $c end   rc=$rc dur=$((SECONDS-t0))s $(date -Is) load=$(cut -d' ' -f1 /proc/loadavg)" >> "$RUNS/driver.log"
done

echo "=== driver done $(date -Is)" >> "$RUNS/driver.log"
