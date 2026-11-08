#!/bin/bash
# E13 improvement portfolio driver — serial, checkpointed, setsid-safe
D=/home/joey123230/ICCAD_A/Agent/paper_exp/e13_rank_comparison
FR=/home/joey123230/ICCAD_A/final_release_100/final_release_100
LOG="$D/improve_runs/driver.log"
while read -r CASE VAR WT; do
  [ -z "$CASE" ] && continue
  OUTLOG="$D/improve_runs/$CASE.$VAR.stdout.log"
  if [ -f "$OUTLOG" ] && grep -q "__JOB_END__" "$OUTLOG"; then echo "skip $CASE.$VAR" >> "$LOG"; continue; fi
  ln -sfn "$FR/$CASE" "$WT/testcase/$CASE"
  [ -f "$FR/$CASE/${CASE}_out.v" ] && mv "$FR/$CASE/${CASE}_out.v" "$D/improve_runs/$CASE.stale.$$.v"
  echo "run $CASE.$VAR start $(date -Is) load=$(cut -d' ' -f1 /proc/loadavg)" >> "$LOG"
  ( cd "$WT" && ABC_BIN=/home/joey123230/ICCAD_A/abc/abc PYTHONHASHSEED=0 \
      timeout 2400 /home/joey123230/ICCAD_A/Agent/.venv/bin/python scripts/run_local.py "testcase/$CASE" ) > "$OUTLOG" 2>&1
  RC=$?
  if [ -f "$FR/$CASE/${CASE}_out.v" ]; then mv "$FR/$CASE/${CASE}_out.v" "$D/improve_runs/${CASE}_out.$VAR.v"; fi
  echo "__JOB_END__ rc=$RC" >> "$OUTLOG"
  echo "run $CASE.$VAR end rc=$RC $(date -Is)" >> "$LOG"
done < "$D/improve_jobs.txt"
echo "=== improve driver done $(date -Is)" >> "$LOG"
