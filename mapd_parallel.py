
import os
import re
import csv
import subprocess
import tempfile
import multiprocessing
from itertools import product
from datetime import datetime, timedelta, timezone

WORKERS       = multiprocessing.cpu_count()
MAX_TIMESTEP  = 3000
MAX_COMP_TIME = 30000
SOLVERS       = ["PIBT", "TP"]
MAP_NAMES     = ["warehouse.map"]
TASK_FREQS    = [0.2, 0.5, 1, 2, 5, 10]
NUM_AGENTS    = [10, 20, 30, 40, 50]
TASK_NUM      = 500
REPEAT_NUM    = 100

def get_date_str():
    return datetime.now(timezone(timedelta(hours=+9), "JST")).strftime("%Y-%m-%d-%H-%M-%S")

def read_result(path):
    patterns = {
        "solved":       re.compile(r"solved=(-?\d+)"),
        "service_time": re.compile(r"service_time=(.+)"),
        "makespan":     re.compile(r"makespan=(-?\d+)"),
        "comp_time":    re.compile(r"comp_time=(-?\d+)"),
    }
    vals = {"solved": -1, "service_time": -1.0, "makespan": -1, "comp_time": -1}
    try:
        with open(path) as f:
            for row in f:
                for k, pat in patterns.items():
                    m = pat.match(row)
                    if m:
                        vals[k] = float(m.group(1)) if k == "service_time" \
                                  else int(m.group(1))
    except FileNotFoundError:
        pass
    return (vals["solved"], vals["service_time"],
            vals["makespan"], vals["comp_time"])


def run_one(args):
    """Worker: run a single (solver, map, task_freq, num_agents, seed) combo."""
    solver, map_name, task_frequency, num_agents, seed = args
    command = os.path.join("..", "build", "mapd")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                     delete=False) as ins_f:
        ins_path = ins_f.name
        ins_f.write(f'map_file={map_name}\n')
        ins_f.write(f'agents={num_agents}\n')
        ins_f.write(f'seed={seed}\n')
        ins_f.write(f'task_frequency={task_frequency}\n')
        ins_f.write(f'task_num={TASK_NUM}\n')
        ins_f.write(f'max_timestep={MAX_TIMESTEP}\n')
        ins_f.write(f'max_comp_time={MAX_COMP_TIME}\n')
        ins_f.write('specify_pickup_deliv_locs=1\n')

    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as res_f:
        res_path = res_f.name

    try:
        subprocess.run(
            f"{command} -i {ins_path} -o {res_path} -s {solver} -d -L",
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

    return (map_name, seed, num_agents, solver,
            task_frequency, TASK_NUM, *result)


if __name__ == "__main__":
    output_dir = os.path.join("..", "..", "data", get_date_str())
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "result_mapd.csv")

    jobs = list(product(SOLVERS, MAP_NAMES, TASK_FREQS, NUM_AGENTS,
                        range(REPEAT_NUM)))
    total = len(jobs)

    print(f"Output  : {output_file}")
    print(f"Workers : {WORKERS} cores")
    print(f"Jobs    : {total}  "
          f"({len(SOLVERS)} solvers × {len(TASK_FREQS)} freqs × "
          f"{len(NUM_AGENTS)} agent-counts × {REPEAT_NUM} seeds)")

    header = ["map_name","seed","num_agents","solver","task_frequency",
              "task_num","solved","service_time","makespan","comp_time"]

    with open(output_file, "w", newline="") as f:
        csv.writer(f).writerow(header)

    done = 0
    with multiprocessing.Pool(processes=WORKERS) as pool:
        with open(output_file, "a", newline="") as f:
            writer = csv.writer(f)
            for row in pool.imap_unordered(run_one, jobs, chunksize=4):
                writer.writerow(row)
                f.flush()
                done += 1
                if done % 100 == 0 or done == total:
                    pct = 100 * done / total
                    print(f"  [{done}/{total}] {pct:.1f}% complete", flush=True)

    print(f"\nDone. Results saved to {output_file}")
