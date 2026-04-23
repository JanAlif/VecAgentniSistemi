

import os
import re
import glob
import csv
import subprocess
import tempfile
import multiprocessing
from itertools import product
from datetime import datetime, timedelta, timezone

WORKERS      = multiprocessing.cpu_count()  
MAX_TIMESTEP = 1000         
MAX_COMP_TIME= 30000        
SOLVERS = [
    "PIBT",
    "HCA",
    "PIBT_PLUS",
    "PushAndSwap",
    "PushAndSwap --no-compress",
]
MAP_NAMES = [
    "empty-8-8.map",
    "random-32-32-20.map",
    "empty-48-48.map",
    "random-64-64-20.map",
    "warehouse-20-40-10-2-2.map",
    "Berlin_1_256.map",
    "Paris_1_256.map",
    "den520d.map",
    "ost003d.map",
    # "brc202d.map",   # uncomment + set MAX_TIMESTEP=2000
]


def get_date_str():
    return datetime.now(timezone(timedelta(hours=+9), "JST")).strftime("%Y-%m-%d-%H-%M-%S")

def read_result(path):
    patterns = {
        "solved":       re.compile(r"solved=(-?\d+)"),
        "soc":          re.compile(r"soc=(-?\d+)"),
        "lb_soc":       re.compile(r"lb_soc=(-?\d+)"),
        "makespan":     re.compile(r"makespan=(-?\d+)"),
        "lb_makespan":  re.compile(r"lb_makespan=(-?\d+)"),
        "comp_time":    re.compile(r"comp_time=(-?\d+)"),
    }
    vals = {k: -1 for k in patterns}
    try:
        with open(path) as f:
            for row in f:
                for k, pat in patterns.items():
                    m = pat.match(row)
                    if m:
                        vals[k] = int(m.group(1))
    except FileNotFoundError:
        pass
    return (vals["solved"], vals["soc"], vals["lb_soc"],
            vals["makespan"], vals["lb_makespan"], vals["comp_time"])


def run_one(args):
    """Worker: run a single (solver, map, scen_num, num_agents) combo."""
    solver, map_name, scen_num, num_agents, starts_goals_str = args
    command = os.path.join("..", "build", "mapf")

   
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                     delete=False) as ins_f:
        ins_path = ins_f.name
        ins_f.write(f'map_file={map_name}\n')
        ins_f.write(f'agents={num_agents}\n')
        ins_f.write(f'seed=0\n')
        ins_f.write(f'random_problem=0\n')
        ins_f.write(f'max_timestep={MAX_TIMESTEP}\n')
        ins_f.write(f'max_comp_time={MAX_COMP_TIME}\n')
        ins_f.write('\n'.join(starts_goals_str[:num_agents]) + '\n')

    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as res_f:
        res_path = res_f.name

    try:
        subprocess.run(
            f"{command} -i {ins_path} -o {res_path} -s {solver} -L",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        result = read_result(res_path)
    finally:
        os.unlink(ins_path)
        try:
            os.unlink(res_path)
        except FileNotFoundError:
            pass

    return (map_name, scen_num, num_agents, solver, *result)


def build_jobs():
    """Parse all .scen files and return list of job args."""
    r_scen      = re.compile(r"\d+\t.+\.map\t\d+\t\d+\t(\d+)\t(\d+)\t(\d+)\t(\d+)\t.+")
    r_scen_file = re.compile(r"benchmark/(.+)\-random\-(\d+)\.scen")

    jobs = []
    for scen_file in sorted(glob.glob("benchmark/*.scen")):
        m = re.match(r_scen_file, scen_file)
        if not m:
            continue
        map_name = f"{m.group(1)}.map"
        scen_num = int(m.group(2))
        if map_name not in MAP_NAMES:
            continue

        starts_goals = []
        with open(scen_file) as f:
            for row in f:
                m2 = re.match(r_scen, row)
                if m2:
                    starts_goals.append(
                        f"{m2.group(1)},{m2.group(2)},{m2.group(3)},{m2.group(4)}"
                    )

        for solver in SOLVERS:
            for n in range(10, len(starts_goals) + 1, 10):
                jobs.append((solver, map_name, scen_num, n, starts_goals))

    return jobs


if __name__ == "__main__":
    output_dir = os.path.join("..", "..", "data", get_date_str())
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "result.csv")

    print(f"Output: {output_file}")
    print(f"Workers: {WORKERS} (out of {multiprocessing.cpu_count()} cores)")

    jobs = build_jobs()
    total = len(jobs)
    print(f"Total jobs: {total}")

    header = ["map_name","scen_num","num_agents","solver",
              "solved","soc","lb_soc","makespan","lb_makespan","comp_time"]

    with open(output_file, "w", newline="") as f:
        csv.writer(f).writerow(header)

    done = 0
    with multiprocessing.Pool(processes=WORKERS) as pool:
        with open(output_file, "a", newline="") as f:
            writer = csv.writer(f)
            for row in pool.imap_unordered(run_one, jobs, chunksize=4):
                writer.writerow(row)
                f.flush()          # write after every result so nothing is lost
                done += 1
                if done % 100 == 0 or done == total:
                    pct = 100 * done / total
                    print(f"  [{done}/{total}] {pct:.1f}% complete", flush=True)

    print(f"\nDone. Results saved to {output_file}")
