

import os, csv, subprocess, tempfile, multiprocessing, collections, statistics

BUILD_DIR    = os.path.join(os.path.dirname(__file__), "build")
MAP_DIR      = os.path.join(os.path.dirname(__file__), "map")
OUT_CSV      = os.path.join(os.path.dirname(__file__), "results", "dense_results.csv")
AGENT_COUNTS = [40, 50, 60, 64]
INSTANCES    = 25

def run(args):
    n, seed = args
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        ins = f.name
        f.write(f"map_file=empty-8-8.map\nagents={n}\nseed={seed}\n"
                f"random_problem=1\nmax_timestep=1000\nmax_comp_time=30000\n")
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        res = f.name
    try:
        subprocess.run(
            f"{BUILD_DIR}/mapf -i {ins} -o {res} -s PIBT -L",
            shell=True, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, cwd=MAP_DIR
        )
        vals = {k: -1 for k in ["solved","soc","lb_soc",
                                 "makespan","lb_makespan","comp_time"]}
        try:
            for line in open(res):
                for k in vals:
                    if line.startswith(k + "="):
                        try: vals[k] = float(line.strip().split("=")[1])
                        except Exception: pass
        except Exception:
            pass
    finally:
        for p in [ins, res]:
            try: os.unlink(p)
            except Exception: pass
    return (n, seed, vals["solved"], vals["soc"], vals["lb_soc"],
            vals["makespan"], vals["lb_makespan"], vals["comp_time"])

if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    jobs = [(n, s + 1) for n in AGENT_COUNTS for s in range(INSTANCES)]
    total = len(jobs)
    workers = multiprocessing.cpu_count()
    print(f"Dense test — {total} jobs across {workers} cores")
    print(f"Output: {OUT_CSV}")

    with open(OUT_CSV, "w", newline="") as f:
        csv.writer(f).writerow(["num_agents","instance","solved","soc","lb_soc",
                                 "makespan","lb_makespan","comp_time"])

    success = collections.defaultdict(int)
    total_count = collections.defaultdict(int)
    comp_times = collections.defaultdict(list)
    soc_ratios = collections.defaultdict(list)
    ms_ratios  = collections.defaultdict(list)
    done = 0

    with multiprocessing.Pool(workers) as pool:
        with open(OUT_CSV, "a", newline="") as f:
            w = csv.writer(f)
            for row in pool.imap_unordered(run, jobs):
                w.writerow(row); f.flush()
                n = row[0]
                total_count[n] += 1
                if row[2] == 1:
                    success[n] += 1
                    if row[7] > 0: comp_times[n].append(row[7])
                    if row[4] > 0: soc_ratios[n].append(row[3] / row[4])
                    if row[6] > 0: ms_ratios[n].append(row[5] / row[6])
                done += 1
                print(f"  [{done}/{total}] agents={n}, solved={int(row[2])}, "
                      f"comp_time={row[7]:.0f}ms", flush=True)

  
    print("\nDense test summary vs paper Table 2:")
    print(f"  {'|A|':>4}  {'rate':>6}  {'paper':>6}  "
          f"{'avg_ms':>8}  {'soc/lb':>8}  {'ms/lb':>8}")
    paper = {40: (0.96, 0.21, 3.15, 3.46),
             50: (0.84, 1.43, 7.38, 6.94),
             60: (1.00, 2.16, 12.25, 7.86),
             64: (1.00, 3.16, 21.55, 10.01)}
    for n in sorted(total_count):
        rate   = success[n] / total_count[n]
        avg_ms = statistics.mean(comp_times[n]) if comp_times[n] else -1
        soc    = statistics.mean(soc_ratios[n]) if soc_ratios[n] else -1
        ms     = statistics.mean(ms_ratios[n])  if ms_ratios[n]  else -1
        p      = paper.get(n, ("?","?","?","?"))
        print(f"  {n:>4}  {rate:>6.2f}  {p[0]:>6}  "
              f"{avg_ms:>8.2f}  {soc:>8.2f}  {ms:>8.2f}")
    print(f"\nDone. Results saved to {OUT_CSV}")
