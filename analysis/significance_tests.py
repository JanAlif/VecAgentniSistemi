"""
Statistical analysis of corridor penalty results.

Reads the per-algorithm JSON files produced by pogema-toolbox in each
experiment folder, then runs paired t-tests comparing the baseline
Follower against each Follower+Corridor variant.

For each (map, num_agents) configuration, reports the mean, percentage
delta, t-statistic, and p-value. The paired t-test is appropriate
because the same set of seeds is used for both conditions.

Significance markers:
  *   : p < 0.05
  **  : p < 0.01
  *** : p < 0.001

Usage:
    python3 analysis/significance_tests.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ttest_rel


EXPERIMENT_FOLDERS = [
    "experiments/06-corridor-warehouse",
    "experiments/07-corridor-mazes",
    "experiments/08-corridor-ood",
]

BASELINE_NAME = "Follower"


def load_folder_data(folder: Path) -> pd.DataFrame:
    """Read all *.json result files in folder, return a unified DataFrame."""
    rows = []
    for jf in sorted(folder.glob("*.json")):
        try:
            with open(jf) as f:
                data = json.load(f)
        except Exception as e:
            print(f"[!] Could not read {jf.name}: {e}")
            continue

        if not isinstance(data, list):
            continue

        for entry in data:
            metrics = entry.get("metrics", {})
            grid = entry.get("env_grid_search", {})
            row = {
                "algorithm": entry.get("algorithm"),
                "num_agents": grid.get("num_agents"),
                "seed": grid.get("seed"),
                "map_name": grid.get("map_name"),
                "avg_throughput": metrics.get("avg_throughput"),
            }
            rows.append(row)

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def sig_marker(p: float) -> str:
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


def analyze_folder(folder: Path) -> None:
    df = load_folder_data(folder)
    if df.empty:
        print(f"\n[!] No JSON data found in {folder}\n")
        return

    print(f"\n{'=' * 110}")
    print(f"Folder: {folder.name}")
    print("=" * 110)

    if BASELINE_NAME not in df["algorithm"].unique():
        print(f"[!] Baseline '{BASELINE_NAME}' not found.")
        print(f"[!] Algorithms in data: {df['algorithm'].unique().tolist()}")
        return

    modified_algos = [a for a in df["algorithm"].unique() if a != BASELINE_NAME]

    has_maps = df["map_name"].notna().any() and df["map_name"].nunique() > 1
    group_keys = (["map_name"] if has_maps else []) + ["num_agents"]

    if has_maps:
        header = f"{'Map':<26} {'Agents':>7} {'Variant':<28} {'Baseline':>10} {'Variant':>10} {'Δ %':>7} {'t':>8} {'p-value':>10} {'sig':>4} {'n':>3}"
    else:
        header = f"{'Agents':>7} {'Variant':<28} {'Baseline':>10} {'Variant':>10} {'Δ %':>7} {'t':>8} {'p-value':>10} {'sig':>4} {'n':>3}"
    print(header)
    print("-" * len(header))

    for keys, group in df.groupby(group_keys):
        if not isinstance(keys, tuple):
            keys = (keys,)

        if has_maps:
            map_label = str(keys[0])
            n_agents = keys[1]
        else:
            map_label = None
            n_agents = keys[0]

        base = group[group["algorithm"] == BASELINE_NAME].sort_values("seed")
        base_vals = base["avg_throughput"].to_numpy()
        if len(base_vals) < 3:
            continue

        for mod in modified_algos:
            mod_rows = group[group["algorithm"] == mod].sort_values("seed")
            mod_vals = mod_rows["avg_throughput"].to_numpy()
            if len(mod_vals) != len(base_vals) or len(mod_vals) < 3:
                continue

            delta_pct = 100.0 * (mod_vals.mean() - base_vals.mean()) / base_vals.mean()
            t_stat, p_val = ttest_rel(base_vals, mod_vals)
            # Sign of t reflects (baseline - variant). Flip so positive t = variant better.
            t_stat = -t_stat

            if has_maps:
                print(
                    f"{map_label:<26} {int(n_agents):>7} {mod:<28} "
                    f"{base_vals.mean():>10.3f} {mod_vals.mean():>10.3f} "
                    f"{delta_pct:>+6.2f}% {t_stat:>+8.3f} {p_val:>10.4f} "
                    f"{sig_marker(p_val):>4} {len(base_vals):>3}"
                )
            else:
                print(
                    f"{int(n_agents):>7} {mod:<28} "
                    f"{base_vals.mean():>10.3f} {mod_vals.mean():>10.3f} "
                    f"{delta_pct:>+6.2f}% {t_stat:>+8.3f} {p_val:>10.4f} "
                    f"{sig_marker(p_val):>4} {len(base_vals):>3}"
                )

    print()


def main() -> None:
    here = Path(__file__).resolve().parent.parent
    for rel in EXPERIMENT_FOLDERS:
        folder = here / rel
        if not folder.exists():
            print(f"[!] Skipping missing folder: {folder}")
            continue
        analyze_folder(folder)

    print("\nLegend: * p<0.05, ** p<0.01, *** p<0.001, ns = not significant")
    print("Paired t-test (two-sided), n = number of seeds.")
    print("Δ % = (variant_mean - baseline_mean) / baseline_mean × 100")
    print("Positive Δ % with significant p means the variant outperforms baseline.\n")


if __name__ == "__main__":
    main()