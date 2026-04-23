import csv
import matplotlib.pyplot as plt
from collections import defaultdict
import os

# Read data
csv_path = 'mapf_result.csv'
rows = []
with open(csv_path, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        row['num_agents'] = int(row['num_agents'])
        row['solved'] = int(row['solved'])
        row['soc'] = int(row['soc'])
        row['makespan'] = int(row['makespan'])
        row['comp_time'] = int(row['comp_time'])
        rows.append(row)

# Group by map, solver, and num_agents
stats = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
for row in rows:
    map_name = row['map_name']
    solver = row['solver']
    n = row['num_agents']
    stats[map_name][solver][n].append(row)

# Get all maps in your results
all_maps = sorted(stats.keys())

# Metrics to plot
metrics = [
    ('solved', 'Solved Rate', False),
    ('soc', 'Sum of Costs (SOC)', False),
    ('makespan', 'Makespan', False),
    ('comp_time', 'Computation Time (ms)', True)
]

# Output directory
outdir = 'mapf_plots_by_map'
os.makedirs(outdir, exist_ok=True)

# Plot for each map
for map_name in all_maps:
    for metric, ylabel, ylog in metrics:
        plt.figure(figsize=(10,6))
        solvers = sorted(stats[map_name].keys())
        agent_counts = sorted(set(n for solver in solvers for n in stats[map_name][solver]))
        for solver in solvers:
            x = []
            y = []
            for n in agent_counts:
                group = stats[map_name][solver][n]
                if group:
                    vals = [r[metric] for r in group]
                    avg = sum(vals) / len(vals)
                    x.append(n)
                    y.append(avg)
            if x:
                plt.plot(x, y, marker='o', label=solver)
        plt.xlabel('Number of Agents')
        plt.ylabel(ylabel)
        plt.title(f'{ylabel} vs Number of Agents\n{map_name}')
        if ylog:
            plt.yscale('log')
        plt.legend()
        plt.grid(True, which='both', linestyle='--', alpha=0.5)
        plt.tight_layout()
        safe_map = map_name.replace('/', '_').replace(' ', '_')
        fname = f'{outdir}/{safe_map}_{metric}.png'
        plt.savefig(fname)
        plt.close()

print(f'Plots saved in {outdir}/ for each map and metric.')
