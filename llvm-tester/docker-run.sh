#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# docker-run.sh  –  llvm-tester container entrypoint
# Source: CONTEXT.json → architecture.data_flow (steps 3 & 4)
#         CONTEXT.json → architecture.components[Validity Filter]
#         CONTEXT.json → architecture.components[Differential Tester]
#
# Stages:
#   1. Validity filtering: llvm-as + opt -passes=verify -disable-output on mutants_llm/ + mutants_grammar/
#   2. Differential testing: compile each valid mutant at -O0 vs -O2 and log mismatches
#
# TODO (Phase 2): implement actual logic below.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

VALID_DIR="${VALID_DIR:-/data/valid_mutants}"
INVALID_DIR="${INVALID_DIR:-/data/invalid_mutants}"
LOGS_DIR="${LOGS_DIR:-/data/logs}"
RESULTS_CSV="${LOGS_DIR}/results.csv"

echo "=== llvm-tester container started ==="
echo "VALID_DIR   : ${VALID_DIR}"
echo "INVALID_DIR : ${INVALID_DIR}"
echo "LOGS_DIR    : ${LOGS_DIR}"

mkdir -p "${VALID_DIR}" "${INVALID_DIR}" "${LOGS_DIR}"

# ── Stage 1: Validity Filtering ───────────────────────────────────────────────
# Iterates over llm and grammar mutants, validates them, and moves to valid/invalid.
# Logic matches filter_valid.py but implemented in Bash for the task.
echo "Starting Stage 1: Validity Filtering..."

for ll_file in /data/mutants_llm/*.ll /data/mutants_grammar/*.ll; do
    [ -e "$ll_file" ] || continue
    
    filename=$(basename "$ll_file")
    mutant_id="${filename%.ll}"
    echo "Processing $mutant_id..."
    
    IS_VALID=false
    ERROR_TYPE="null"
    VERIFIER_OUT=""
    
    # 1. llvm-as
    if llvm-as "$ll_file" -o /tmp/tmp.bc 2>/tmp/err.txt; then
        # 2. opt -passes=verify -disable-output
        if opt -S -passes=verify /tmp/tmp.bc -o /dev/null 2>>/tmp/err.txt; then
            IS_VALID=true
            ERROR_TYPE="null"
            VERIFIER_OUT="Verification successful."
            cp "$ll_file" "${VALID_DIR}/"
        else
            IS_VALID=false
            # Simple keyword check for Bash
            ERR=$(cat /tmp/err.txt)
            if echo "$ERR" | grep -iq "dominate\|phi"; then ERROR_TYPE="\"ssa\""
            elif echo "$ERR" | grep -iq "type\|pointer\|mismatch"; then ERROR_TYPE="\"type\""
            elif echo "$ERR" | grep -iq "terminate\|successor\|cfg"; then ERROR_TYPE="\"cfg\""
            else ERROR_TYPE="\"other\""; fi
            VERIFIER_OUT=$(echo "$ERR" | tr '\n' ' ' | sed 's/"/\\"/g')
            cp "$ll_file" "${INVALID_DIR}/"
        fi
    else
        IS_VALID=false
        ERROR_TYPE="\"syntax\""
        VERIFIER_OUT=$(cat /tmp/err.txt | tr '\n' ' ' | sed 's/"/\\"/g')
        cp "$ll_file" "${INVALID_DIR}/"
    fi
    
    # 3. Log to validity_logs.json
    CREATED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    LOG_ENTRY="{\"mutant_id\": \"$mutant_id\", \"is_valid\": $IS_VALID, \"error_type\": $ERROR_TYPE, \"verifier_output\": \"$VERIFIER_OUT\", \"created_at\": \"$CREATED_AT\"}"
    
    # Append to JSON list (naively)
    if [ ! -f "${LOGS_DIR}/validity_logs.json" ]; then
        echo "[$LOG_ENTRY]" > "${LOGS_DIR}/validity_logs.json"
    else
        # Remove last bracket, append comma and entry, add bracket back
        sed -i '$s/\]//' "${LOGS_DIR}/validity_logs.json"
        echo ",$LOG_ENTRY]" >> "${LOGS_DIR}/validity_logs.json"
    fi
    
    rm -f /tmp/tmp.bc /tmp/err.txt
done
echo "Stage 1 complete."

# ── Stage 2: Differential Testing ────────────────────────────────────────────
# Compiles each valid mutant at -O0 vs -O2 and logs mismatches to results.csv
echo "Starting Stage 2: Differential Testing..."

# Pre-emptive header check
if [ ! -f "$RESULTS_CSV" ]; then
    echo "mutant_id,baseline_level,target_level,is_mismatch,mismatch_type,runtime_ms_baseline,runtime_ms_target,created_at" > "$RESULTS_CSV"
fi

for valid_ll in "${VALID_DIR}"/*.ll; do
    [ -e "$valid_ll" ] || continue
    
    filename=$(basename "$valid_ll")
    mutant_id="${filename%.ll}"
    echo "Testing $mutant_id..."
    
    IS_MISMATCH=false
    MISMATCH_TYPE="null"
    RT_O0=""
    RT_O2=""
    
    # 1. Compile O0
    if clang -O0 "$valid_ll" -o /tmp/bin_O0 2>/dev/null; then
        # 2. Compile O2
        if clang -O2 "$valid_ll" -o /tmp/bin_O2 2>/dev/null; then
            # 3. Run and Time O0
            T_START=$(date +%s%N)
            if /tmp/bin_O0 > /tmp/out_O0.txt 2>/dev/null; then
                T_END=$(date +%s%N)
                RT_O0=$(( (T_END - T_START) / 1000000 ))
                
                # 4. Run and Time O2
                T_START=$(date +%s%N)
                if /tmp/bin_O2 > /tmp/out_O2.txt 2>/dev/null; then
                    T_END=$(date +%s%N)
                    RT_O2=$(( (T_END - T_START) / 1000000 ))
                    
                    # 5. Check output mismatch
                    if ! diff /tmp/out_O0.txt /tmp/out_O2.txt >/dev/null; then
                        IS_MISMATCH=true
                        MISMATCH_TYPE="\"wrong_output\""
                    fi
                else
                    IS_MISMATCH=true
                    MISMATCH_TYPE="\"crash\""
                fi
            else
                IS_MISMATCH=true
                MISMATCH_TYPE="\"crash\""
            fi
        else
            IS_MISMATCH=true
            MISMATCH_TYPE="\"unknown\""
        fi
    else
        IS_MISMATCH=true
        MISMATCH_TYPE="\"unknown\""
    fi
    
    # 6. Log to results.csv
    CREATED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "$mutant_id,-O0,-O2,$IS_MISMATCH,$MISMATCH_TYPE,$RT_O0,$RT_O2,$CREATED_AT" >> "$RESULTS_CSV"
    
    rm -f /tmp/bin_O0 /tmp/bin_O2 /tmp/out_O0.txt /tmp/out_O2.txt
done
echo "Stage 2 complete."

echo "=== llvm-tester finished ==="

