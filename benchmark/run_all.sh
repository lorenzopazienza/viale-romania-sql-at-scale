#!/usr/bin/env bash
# Runs every experiment in order and writes results/*.json and results/plans/*.txt.
# Assumes big_10m and the tiers exist (make data). Takes about 30 minutes on 2 vCPU.
set -euo pipefail
cd "$(dirname "$0")"
python3 04_scaling.py
python3 05_correlated_vs_window.py
python3 explain_plans.py
python3 06_index_design.py
python3 07_anti_joins.py
python3 08_trigger_cost.py
python3 09_storage.py
