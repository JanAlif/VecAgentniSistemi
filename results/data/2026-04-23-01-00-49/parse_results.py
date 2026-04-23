import csv
from collections import defaultdict

# Read the CSV file
csv_path = 'mapf_result.csv'
rows = []
with open(csv_path, 'r') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Convert numeric fields
for row in rows:
    row['num_agents'] = int(row['num_agents'])
    row['solved'] = int(row['solved'])
    row['soc'] = int(row['soc'])
    row['makespan'] = int(row['makespan'])
    row['comp_time'] = int(row['comp_time'])

# Get unique solvers
solvers = sorted(set(row['solver'] for row in rows))
agent_counts = sorted(set(row['num_agents'] for row in rows))

# Build summary statistics
summary_stats = defaultdict(lambda: {'solved': [], 'soc': [], 'makespan': [], 'comp_time': []})
for row in rows:
    key = (row['solver'], row['num_agents'])
    summary_stats[key]['solved'].append(row['solved'])
    summary_stats[key]['soc'].append(row['soc'])
    summary_stats[key]['makespan'].append(row['makespan'])
    summary_stats[key]['comp_time'].append(row['comp_time'])

# Create HTML table
html_output = """<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { background-color: white; padding: 20px; border-radius: 8px; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 30px; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #2196F3; color: white; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        h1, h2 { color: #333; }
        .stats { margin: 15px 0; }
        .stats p { margin: 5px 0; }
    </style>
</head>
<body>
    <div class="container">
    <h1>MAPF Results Summary</h1>
    <div class="stats">
        <p><strong>Total records:</strong> """ + str(len(rows)) + """</p>
        <p><strong>Unique solvers:</strong> """ + str(', '.join(solvers)) + """</p>
        <p><strong>Agent count range:</strong> """ + str(min(agent_counts)) + """ - """ + str(max(agent_counts)) + """</p>
    </div>
    
    <h2>Summary by Solver and Agent Count</h2>
    <table>
        <tr>
            <th>Solver</th>
            <th>Num Agents</th>
            <th>Avg Solved Rate</th>
            <th>Avg SOC</th>
            <th>Avg Makespan</th>
            <th>Avg Comp Time (ms)</th>
            <th>Max Comp Time (ms)</th>
            <th>Min Comp Time (ms)</th>
        </tr>
"""

# Add summary rows sorted by solver and agent count
for (solver, num_agents) in sorted(summary_stats.keys()):
    stats = summary_stats[(solver, num_agents)]
    avg_solved = sum(stats['solved']) / len(stats['solved']) if stats['solved'] else 0
    avg_soc = sum(stats['soc']) / len(stats['soc']) if stats['soc'] else 0
    avg_makespan = sum(stats['makespan']) / len(stats['makespan']) if stats['makespan'] else 0
    avg_time = sum(stats['comp_time']) / len(stats['comp_time']) if stats['comp_time'] else 0
    max_time = max(stats['comp_time']) if stats['comp_time'] else 0
    min_time = min(stats['comp_time']) if stats['comp_time'] else 0
    
    html_output += f"""        <tr>
            <td>{solver}</td>
            <td>{num_agents}</td>
            <td>{avg_solved:.2f}</td>
            <td>{avg_soc:.2f}</td>
            <td>{avg_makespan:.2f}</td>
            <td>{avg_time:.2f}</td>
            <td>{max_time:.2f}</td>
            <td>{min_time:.2f}</td>
        </tr>
"""

html_output += """    </table>
    
    <h2>Detailed Results (Sample - First 500 rows)</h2>
    <table>
        <tr>
"""

# Add header row
columns = ['map_name', 'scen_num', 'num_agents', 'solver', 'solved', 'soc', 'lb_soc', 'makespan', 'lb_makespan', 'comp_time']
for col in columns:
    html_output += f"<th>{col}</th>"
html_output += """</tr>
"""

# Add first 500 data rows
for i, row in enumerate(rows[:500]):
    html_output += "        <tr>\n"
    for col in columns:
        html_output += f"            <td>{row[col]}</td>\n"
    html_output += "        </tr>\n"

if len(rows) > 500:
    html_output += f"""        <tr>
            <td colspan="{len(columns)}" style="text-align: center; font-style: italic;">... and {len(rows) - 500} more rows</td>
        </tr>
"""

html_output += """    </table>
    </div>
</body>
</html>
"""

# Save HTML file
with open('mapf_results_table.html', 'w') as f:
    f.write(html_output)

# Create markdown summary
markdown_output = "# MAPF Results Summary\n\n"
markdown_output += f"**Total records:** {len(rows)}\n\n"
markdown_output += f"**Unique solvers:** {', '.join(solvers)}\n\n"
markdown_output += f"**Agent count range:** {min(agent_counts)} - {max(agent_counts)}\n\n"

markdown_output += "## Summary Statistics by Solver and Agent Count\n\n"
markdown_output += "| Solver | Num Agents | Avg Solved | Avg SOC | Avg Makespan | Avg Time (ms) | Max Time | Min Time |\n"
markdown_output += "|--------|-----------|-----------|---------|-------------|--------------|---------|----------|\n"

for (solver, num_agents) in sorted(summary_stats.keys()):
    stats = summary_stats[(solver, num_agents)]
    avg_solved = sum(stats['solved']) / len(stats['solved']) if stats['solved'] else 0
    avg_soc = sum(stats['soc']) / len(stats['soc']) if stats['soc'] else 0
    avg_makespan = sum(stats['makespan']) / len(stats['makespan']) if stats['makespan'] else 0
    avg_time = sum(stats['comp_time']) / len(stats['comp_time']) if stats['comp_time'] else 0
    max_time = max(stats['comp_time']) if stats['comp_time'] else 0
    min_time = min(stats['comp_time']) if stats['comp_time'] else 0
    
    markdown_output += f"| {solver} | {num_agents} | {avg_solved:.2f} | {avg_soc:.2f} | {avg_makespan:.2f} | {avg_time:.2f} | {max_time} | {min_time} |\n"

# Save markdown file
with open('mapf_results_summary.md', 'w') as f:
    f.write(markdown_output)

# Save sorted CSV
with open('mapf_results_formatted.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    # Sort by solver and num_agents
    sorted_rows = sorted(rows, key=lambda r: (r['solver'], int(r['num_agents']), int(r['scen_num'])))
    writer.writerows(sorted_rows)

