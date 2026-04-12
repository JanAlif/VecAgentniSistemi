#!/bin/bash
###############################################################################
# reproduce_results.sh
#
# Reproduces results from "Lifelong MAPF in Large-Scale Warehouses" (AAAI-21)
# Run from the RHCR project root directory.
#
# Reproducible:  Table 1, Table 2, Table 3a, Section 5.3
# Skipped:       Table 3b (WHCA segfaults on sorting map)
#                Table 3c (CBS solver not in build)
###############################################################################
set -e

BINARY="./build/lifelong"
KIVA_MAP="./maps/kiva.map"
SORTING_MAP="./maps/sorting_map.grid"
OUTPUT_DIR="./reproduction_results"

NUM_SEEDS=3
SEEDS=(0 1 2)
SIMULATION_TIME=5000
CUTOFF_TIME=60
SCREEN=1
W_INF=1073741823

mkdir -p "${OUTPUT_DIR}"

###############################################################################
# parse_output: stdout → "throughput,avg_runtime_per_episode"
###############################################################################
parse_output() {
    local f="$1"
    python3 -c "
import re, statistics
with open('${f}') as fh:
    lines = fh.readlines()
rts = []
tasks = []
for line in lines:
    m = re.match(r'\w+:(Succeed|Failed),([\d.e+-]+)', line)
    if m: rts.append(float(m.group(2)))
    m2 = re.match(r'(\d+) tasks has been finished', line)
    if m2: tasks.append(int(m2.group(1)))
total = sum(tasks)
tp = total / ${SIMULATION_TIME}
avg_rt = statistics.mean(rts) if rts else 0
print(f'{tp:.4f},{avg_rt:.6f},{total},{len(rts)}')
"
}

###############################################################################
# run_one: single seed
###############################################################################
run_one() {
    local label="$1" map="$2" scen="$3" k="$4" solver="$5"
    local hw="$6" pw="$7" seed="$8" extra="$9"
    local d="${OUTPUT_DIR}/raw/${label}/seed${seed}"
    mkdir -p "${d}"
    local cmd="${BINARY} -m ${map} --scenario=${scen} -k ${k} --solver=${solver} \
        --simulation_window=${hw} --planning_window=${pw} \
        --simulation_time=${SIMULATION_TIME} -t ${CUTOFF_TIME} \
        -d ${seed} -s ${SCREEN} -o ${d}/exp ${extra}"
    if eval ${cmd} > "${d}/stdout.txt" 2>&1; then
        parse_output "${d}/stdout.txt"
    else
        echo "FAILED,0,0,0"
    fi
}

###############################################################################
# run_config: all seeds → one-line aggregated result
###############################################################################
run_config() {
    local label="$1" map="$2" scen="$3" k="$4" solver="$5"
    local hw="$6" pw="$7" extra="$8"
    local res=()
    for seed in "${SEEDS[@]}"; do
        res+=("$(run_one "${label}" "${map}" "${scen}" "${k}" "${solver}" \
            "${hw}" "${pw}" "${seed}" "${extra}")")
    done
    python3 -c "
import statistics
raw = '''$(printf '%s\n' "${res[@]}")'''.strip().split('\n')
tps, rts = [], []
for r in raw:
    p = r.split(',')
    if p[0]=='FAILED': continue
    tps.append(float(p[0])); rts.append(float(p[1]))
if not tps:
    print('  ${label}: FAILED')
else:
    tp=statistics.mean(tps); ts=statistics.stdev(tps) if len(tps)>1 else 0
    rt=statistics.mean(rts); rs=statistics.stdev(rts) if len(rts)>1 else 0
    print(f'  ${label}: tp={tp:.2f}±{ts:.2f}  rt={rt:.4f}±{rs:.4f}  (n={len(tps)})')
" | tee -a "${OUTPUT_DIR}/results.txt"
}

###############################################################################
echo "============================================================" | tee "${OUTPUT_DIR}/results.txt"
echo " RHCR Reproduction — $(date)" | tee -a "${OUTPUT_DIR}/results.txt"
echo " Seeds=${NUM_SEEDS} SimTime=${SIMULATION_TIME}" | tee -a "${OUTPUT_DIR}/results.txt"
echo "============================================================" | tee -a "${OUTPUT_DIR}/results.txt"

# =========================================================================
# TABLE 1: Fulfillment Warehouse — PBS, w=20, h=5 vs HE/RDP h=1
# =========================================================================
# if [ -f "${KIVA_MAP}" ]; then
#     echo "" | tee -a "${OUTPUT_DIR}/results.txt"
#     echo "=== TABLE 1: Fulfillment (PBS) ===" | tee -a "${OUTPUT_DIR}/results.txt"
#     echo "Paper: RHCR 2.33/3.56/4.55 | HE 2.17/3.33/4.35 | RDP 2.19/3.41/4.50" | tee -a "${OUTPUT_DIR}/results.txt"
#     for m in 60 100 140; do
#         echo "  --- m=${m} ---" | tee -a "${OUTPUT_DIR}/results.txt"
#         run_config "t1_RHCR_m${m}" "${KIVA_MAP}" KIVA ${m} PBS 5 20 \
#             "--potential_function=IC --potential_threshold=1 --prioritize_start=1"
#         run_config "t1_HE_m${m}" "${KIVA_MAP}" KIVA ${m} PBS 1 ${W_INF} \
#             "--hold_endpoints=1 --prioritize_start=1"
#         run_config "t1_RDP_m${m}" "${KIVA_MAP}" KIVA ${m} PBS 1 ${W_INF} \
#             "--dummy_path=1 --prioritize_start=1"
#     done
# fi

# =========================================================================
# TABLE 2: Sorting Center — PBS, h=5, w∈{5,10,20,∞}, m∈{400..1000}
# =========================================================================
if [ -f "${SORTING_MAP}" ]; then
    echo "" | tee -a "${OUTPUT_DIR}/results.txt"
    echo "=== TABLE 2: Sorting (PBS) ===" | tee -a "${OUTPUT_DIR}/results.txt"
    echo "Paper: m=400,w5→12.27 w∞→12.46 | m=700,w5→20.69 w∞→21.30 | m=1000,w5→27.95" | tee -a "${OUTPUT_DIR}/results.txt"
    #for m in 400 500 600 700 800 900 1000; do
    for m in 1000; do
        echo "  --- m=${m} ---" | tee -a "${OUTPUT_DIR}/results.txt"
        for w in 5 10 20 ${W_INF}; do
            wl=$( [ ${w} -eq ${W_INF} ] && echo "inf" || echo "${w}" )
            run_config "t2_PBS_w${wl}_m${m}" "${SORTING_MAP}" SORTING ${m} PBS 5 ${w} \
                "--potential_function=IC --potential_threshold=1 --prioritize_start=1"
        done
    done
fi

# =========================================================================
# TABLE 3a: Sorting Center — ECBS subopt=1.1, h=5, w∈{5,∞}, m∈{100..600}
# =========================================================================
# if [ -f "${SORTING_MAP}" ]; then
#     echo "" | tee -a "${OUTPUT_DIR}/results.txt"
#     echo "=== TABLE 3a: Sorting (ECBS 1.1) ===" | tee -a "${OUTPUT_DIR}/results.txt"
#     echo "Paper: m=100,w5→3.19 w∞→3.16 | m=400,w5→12.03 w∞→12.28 | m=600,w5→17.28" | tee -a "${OUTPUT_DIR}/results.txt"
#     for m in 100 200 300 400 500 600; do
#         echo "  --- m=${m} ---" | tee -a "${OUTPUT_DIR}/results.txt"
#         for w in 5 ${W_INF}; do
#             wl=$( [ ${w} -eq ${W_INF} ] && echo "inf" || echo "${w}" )
#             run_config "t3a_ECBS_w${wl}_m${m}" "${SORTING_MAP}" SORTING ${m} ECBS 5 ${w} \
#                 "--suboptimal_bound=1.1 --potential_function=IC --potential_threshold=1 --prioritize_start=1"
#         done
#     done
# fi

# =========================================================================
# NOTE: Table 3b (WHCA/CA*) SKIPPED — segfaults on sorting_map.grid
# NOTE: Table 3c (CBS) SKIPPED — solver not available in build
# =========================================================================

# =========================================================================
# Section 5.3: Dynamic Bounded Horizons — ECBS 1.5, KIVA, 60 agents
# =========================================================================
# if [ -f "${KIVA_MAP}" ]; then
#     echo "" | tee -a "${OUTPUT_DIR}/results.txt"
#     echo "=== Section 5.3: Dynamic Horizons ===" | tee -a "${OUTPUT_DIR}/results.txt"
#     echo "Paper: dyn→2.10/0.35s | w=5→1.72/0.07s | w=10→2.02/0.17s" | tee -a "${OUTPUT_DIR}/results.txt"
#     run_config "s53_dyn_w5_p60" "${KIVA_MAP}" KIVA 60 ECBS 5 5 \
#         "--suboptimal_bound=1.5 --potential_function=IC --potential_threshold=60 --prioritize_start=1"
#     run_config "s53_fix_w5" "${KIVA_MAP}" KIVA 60 ECBS 5 5 \
#         "--suboptimal_bound=1.5 --potential_function=NONE --potential_threshold=0 --prioritize_start=1"
#     run_config "s53_fix_w10" "${KIVA_MAP}" KIVA 60 ECBS 5 10 \
#         "--suboptimal_bound=1.5 --potential_function=NONE --potential_threshold=0 --prioritize_start=1"
# fi

echo "" | tee -a "${OUTPUT_DIR}/results.txt"
echo "============================================================" | tee -a "${OUTPUT_DIR}/results.txt"
echo " DONE — see ${OUTPUT_DIR}/results.txt" | tee -a "${OUTPUT_DIR}/results.txt"
echo "============================================================" | tee -a "${OUTPUT_DIR}/results.txt"