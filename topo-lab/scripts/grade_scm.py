"""Evaluation oracle for Supply Chain Management (SCM) benchmark runs.

Evaluates transactional and domain invariants across Trade, Warehouse,
and Fulfillment tiers following the SupChain-Bench schema:
1. Inventory conservation: on_hand == allocated + available
2. Non-negativity / No over-allocation: allocated <= on_hand and available >= 0
3. Order 101 fulfillment & 3PL carrier dispatch consistency
4. Order 102 allocation & backorder consistency (checks for Lost Update)
5. Cross-tier ledger consistency: sum(orders.allocated_qty) == warehouse.allocated

Usage:
  python scripts/grade_scm.py runs/<run_dir>
  python scripts/grade_scm.py --all
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
TASK_ID = "scm__order-fulfillment"


def evaluate_run(run_dir: Path) -> dict:
    trace_path = run_dir / "trace.json"
    if not trace_path.exists():
        return {"error": f"no trace.json in {run_dir}"}

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    after_dir = run_dir / "files_after"
    repo_dir = TASKS_DIR / TASK_ID / "repo"

    def read_json_state(rel_path: str):
        target = after_dir / rel_path
        if not target.exists():
            target = repo_dir / rel_path
        if not target.exists():
            return None
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            return None

    orders = read_json_state("trade/orders.json")
    inventory = read_json_state("warehouse/inventory.json")
    shipments = read_json_state("fulfillment/shipments.json")
    manifest = read_json_state("audit/manifest.json")

    invariants = {}

    # Invariant 1: Inventory Conservation
    if inventory and "SKU-MED-99" in inventory:
        inv = inventory["SKU-MED-99"]
        invariants["inv_conservation"] = (
            inv.get("on_hand", 0) == inv.get("allocated", 0) + inv.get("available", 0)
        )
    else:
        invariants["inv_conservation"] = False

    # Invariant 2: Non-Negativity & No Over-allocation
    if inventory and "SKU-MED-99" in inventory:
        inv = inventory["SKU-MED-99"]
        invariants["no_overallocation"] = (
            inv.get("allocated", 0) <= inv.get("on_hand", 0)
            and inv.get("available", 0) >= 0
            and inv.get("allocated", 0) <= 20
        )
    else:
        invariants["no_overallocation"] = False

    # Invariant 3: Order 101 Fulfilled & Dispatched
    if orders and "ORD-2026-101" in orders:
        ord1 = orders["ORD-2026-101"]
        shp_list = shipments.get("shipments", []) if shipments else []
        has_shipment = any(s.get("order_id") == "ORD-2026-101" for s in shp_list)
        invariants["order_101_dispatched"] = (
            ord1.get("allocated_qty") == 15
            and ord1.get("status") in ("ALLOCATED", "DISPATCHED")
            and has_shipment
        )
    else:
        invariants["order_101_dispatched"] = False

    # Invariant 4: Order 102 Preserved (No Lost Update / WAW)
    if orders and "ORD-2026-102" in orders:
        ord2 = orders["ORD-2026-102"]
        # Under correct conflict-ordered execution, ORD-102 gets the remaining 5 units
        # and 5 units are backordered.
        invariants["order_102_allocated"] = (
            ord2.get("allocated_qty") == 5
            and ord2.get("backordered_qty") == 5
            and ord2.get("status") in ("ALLOCATED", "PARTIALLY_FULFILLED")
        )
    else:
        invariants["order_102_allocated"] = False

    # Invariant 5: Cross-Tier Ledger Match
    if orders and inventory and "SKU-MED-99" in inventory:
        sum_allocated_orders = sum(
            o.get("allocated_qty", 0) for o in orders.values()
            if isinstance(o, dict) and o.get("sku") == "SKU-MED-99"
        )
        wh_allocated = inventory["SKU-MED-99"].get("allocated", 0)
        invariants["cross_tier_ledger_match"] = (
            sum_allocated_orders == wh_allocated
        )
    else:
        invariants["cross_tier_ledger_match"] = False

    passed = sum(1 for v in invariants.values() if v)
    total = len(invariants)
    resolved = (passed == total)

    # Anomaly counts from trace
    overwrite_events = trace.get("overwrite_events", [])
    nodes = trace.get("nodes", [])
    stale_reads = sum(
        1 for n in nodes for r in n.get("reads", [])
        if r.get("writer") and r["writer"] != "__seed__"
    )
    node_errors = sum(1 for n in nodes if n.get("status") != "success")

    return {
        "run": run_dir.name,
        "topology": trace.get("topology"),
        "agent": trace.get("agent"),
        "mock": trace.get("mock"),
        "wall_s": trace.get("wall_s"),
        "cost_usd": trace.get("total_cost_usd"),
        "write_conflicts": len(overwrite_events),
        "stale_reads": stale_reads,
        "node_errors": node_errors,
        "invariants_passed": f"{passed}/{total}",
        "score": round(passed / total, 2),
        "resolved": "yes" if resolved else "no",
        "details": invariants,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", nargs="?", type=Path)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    if args.all:
        runs = sorted(ROOT.glob(f"runs/{TASK_ID}*"))
        if not runs:
            print("No SCM runs found.")
            return
        print(f"| run | topology | wall (s) | cost ($) | write conflicts | stale reads | invariants | resolved |")
        print(f"|---|---|---|---|---|---|---|---|")
        for r in runs:
            res = evaluate_run(r)
            if "error" in res:
                continue
            print(f"| {res['run']} | {res['topology']} | {res['wall_s']} | {res['cost_usd']} | {res['write_conflicts']} | {res['stale_reads']} | {res['invariants_passed']} | {res['resolved']} |")
    elif args.run_dir:
        res = evaluate_run(args.run_dir)
        print(json.dumps(res, indent=2))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
