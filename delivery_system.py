"""
FastBox Logistics Simulator
===========================

Small delivery simulation used for demonstration and teaching.
"""

# Copied from original

import json
import math
import csv
import random
import sys
import os

# 1.  UTILITIES

def euclidean(p1, p2):
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


# 2.  LOAD & NORMALISE JSON


def load_data(filepath):
   
    with open(filepath, "r") as f:
        raw = json.load(f)

    # ── normalise warehouses ──────────────────
    raw_wh = raw["warehouses"]
    if isinstance(raw_wh, dict):
        warehouses = raw_wh                          # already {id: [x,y]}
    else:
        warehouses = {w["id"]: w["location"] for w in raw_wh}

    # ── normalise agents ─────────────────────
    raw_ag = raw["agents"]
    if isinstance(raw_ag, dict):
        agents = raw_ag                              # already {id: [x,y]}
    else:
        agents = {a["id"]: a["location"] for a in raw_ag}

    # ── normalise packages ───────────────────
    packages = []
    for p in raw["packages"]:
        packages.append({
            "id":          p["id"],
            "warehouse":   p.get("warehouse") or p.get("warehouse_id"),
            "destination": p["destination"]
        })

    return warehouses, agents, packages



# 3.  AGENT–PACKAGE ASSIGNMENT


def assign_packages(warehouses, agents, packages):
  
    assignments = {agent_id: [] for agent_id in agents}

    for pkg in packages:
        wh_location = warehouses[pkg["warehouse"]]

        # Find the agent nearest to this warehouse
        nearest_agent = min(
            agents,
            key=lambda aid: euclidean(agents[aid], wh_location)
        )
        assignments[nearest_agent].append(pkg)

    return assignments


# 4.  DELIVERY SIMULATION

def simulate_deliveries(warehouses, agents, assignments, add_delays=False):
    
    results = {}

    for agent_id, pkgs in assignments.items():
        current_pos = list(agents[agent_id])  # start position (mutable copy)
        total_dist  = 0.0
        log         = []
        total_delay = 0

        for pkg in pkgs:
            wh_loc   = warehouses[pkg["warehouse"]]
            dest_loc = pkg["destination"]

            # leg 1: agent → warehouse
            d1 = euclidean(current_pos, wh_loc)
            # leg 2: warehouse → destination
            d2 = euclidean(wh_loc, dest_loc)

            total_dist  += d1 + d2
            current_pos  = list(dest_loc)   # agent ends at delivery point

            # BONUS: random delay (0–30 minutes)
            delay = random.randint(0, 30) if add_delays else 0
            total_delay += delay

            log.append({
                "package":        pkg["id"],
                "warehouse":      pkg["warehouse"],
                "dist_to_wh":     round(d1, 2),
                "dist_to_dest":   round(d2, 2),
                "delay_minutes":  delay
            })

        n = len(pkgs)
        results[agent_id] = {
            "packages_delivered": n,
            "total_distance":     round(total_dist, 2),
            # efficiency = average distance per package (lower is better)
            "efficiency":         round(total_dist / n, 2) if n > 0 else 0,
            "log":                log,
            "delay_minutes":      total_delay
        }

    return results


# 5.  REPORT GENERATION

def generate_report(results):
   
    # Best agent = lowest efficiency among agents who delivered something
    active = {aid: r for aid, r in results.items() if r["packages_delivered"] > 0}
    best_agent = min(active, key=lambda aid: active[aid]["efficiency"]) if active else None

    report = {}
    for agent_id, r in results.items():
        report[agent_id] = {
            "packages_delivered": r["packages_delivered"],
            "total_distance":     r["total_distance"],
            "efficiency":         r["efficiency"]
        }
        if r["delay_minutes"]:
            report[agent_id]["delay_minutes"] = r["delay_minutes"]

    report["best_agent"] = best_agent
    return report


def save_report(report, output_path="report.json"):
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  ✔  Report saved → {output_path}")


# 6.  BONUS – ASCII ROUTE VISUALISER

def ascii_map(warehouses, agents, packages, grid_size=20):
    all_x = [c[0] for c in list(warehouses.values()) + list(agents.values())
             + [p["destination"] for p in packages]]
    all_y = [c[1] for c in list(warehouses.values()) + list(agents.values())
             + [p["destination"] for p in packages]]

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)

    def scale(val, lo, hi, size):
        if hi == lo:
            return size // 2
        return int((val - lo) / (hi - lo) * (size - 1))

    canvas = [["·"] * grid_size for _ in range(grid_size)]

    for wid, loc in warehouses.items():
        c = scale(loc[0], min_x, max_x, grid_size)
        r = grid_size - 1 - scale(loc[1], min_y, max_y, grid_size)
        canvas[r][c] = "W"

    for aid, loc in agents.items():
        c = scale(loc[0], min_x, max_x, grid_size)
        r = grid_size - 1 - scale(loc[1], min_y, max_y, grid_size)
        canvas[r][c] = "A"

    for pkg in packages:
        c = scale(pkg["destination"][0], min_x, max_x, grid_size)
        r = grid_size - 1 - scale(pkg["destination"][1], min_y, max_y, grid_size)
        canvas[r][c] = "D"

    print("\n  ASCII Map  (W=Warehouse  A=Agent  D=Destination)")
    print("  " + "─" * (grid_size * 2))
    for row in canvas:
        print("  " + " ".join(row))
    print("  " + "─" * (grid_size * 2) + "\n")


# 7.  BONUS – EXPORT TOP PERFORMER TO CSV

def export_top_performer(report, results, output_path="top_performer.csv"):
    best = report["best_agent"]
    if best is None:
        print("  ⚠  No deliveries; CSV not written.")
        return

    fieldnames = ["package", "warehouse", "dist_to_wh", "dist_to_dest", "delay_minutes"]
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for entry in results[best]["log"]:
            writer.writerow(entry)

    print(f"  ✔  Top performer ({best}) log → {output_path}")


# 8.  MAIN

def run(input_file, output_file="report.json", show_map=True, add_delays=False):

    print(f"\n{'═'*55}")
    print(f"  FastBox Simulator  |  {os.path.basename(input_file)}")
    print(f"{'═'*55}")

    # Step 1 – Parse JSON
    warehouses, agents, packages = load_data(input_file)
    print(f"  Warehouses : {len(warehouses)}  |  Agents : {len(agents)}  |  Packages : {len(packages)}")

    # Step 2 – Assign packages to nearest agent
    assignments = assign_packages(warehouses, agents, packages)
    for aid, pkgs in assignments.items():
        ids = [p["id"] for p in pkgs]
        print(f"    {aid} → {ids if ids else '(no packages)'}")

    # Step 3 – Simulate deliveries
    results = simulate_deliveries(warehouses, agents, assignments, add_delays=add_delays)

    # Step 4 – Generate & save report
    report = generate_report(results)
    save_report(report, output_file)

    # Print summary
    print(f"\n  {'Agent':<6} {'Delivered':>10} {'Distance':>12} {'Efficiency':>12}")
    print(f"  {'─'*44}")
    for aid, r in report.items():
        if aid == "best_agent":
            continue
        star = " ★" if aid == report["best_agent"] else ""
        print(f"  {aid:<6} {r['packages_delivered']:>10} {r['total_distance']:>12.2f} {r['efficiency']:>12.2f}{star}")
    print(f"\n  Best Agent : {report['best_agent']}")

    # BONUS – ASCII map
    if show_map:
        ascii_map(warehouses, agents, packages)

    # BONUS – CSV export
    export_top_performer(report, results)

    return report


# 9.  ENTRY POINT

if __name__ == "__main__":

    input_path = sys.argv[1] if len(sys.argv) > 1 else "data.json"

    if not os.path.exists(input_path):
        print(f"Error: '{input_path}' not found.")
        sys.exit(1)

    run(input_path, output_file="report.json", show_map=True, add_delays=True)
