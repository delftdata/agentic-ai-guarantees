# Task: scm__order-fulfillment

Domain: Enterprise Supply Chain Management (Grounding: SupChain-Bench)
Architecture: Three-Tier Enterprise System (Trade -> Warehouse -> Fulfillment)

## Problem Statement

Process pending customer orders under inventory scarcity while ensuring system-wide transactional consistency across Trade, Warehouse, and Fulfillment tiers.

There are two pending orders for temperature-sensitive medical supply `SKU-MED-99`:
1. High-Priority Order `ORD-2026-101`: Apex Health Logistics requests 15 units.
2. Standard Order `ORD-2026-102`: BioCare Regional Labs requests 10 units.

Current Warehouse physical inventory:
- `SKU-MED-99` has exactly 20 units on hand (`on_hand: 20`, `allocated: 0`, `available: 20`).
- Total demand (25 units) exceeds total physical availability (20 units).

Business Invariants & Standard Operating Procedures (SOP):
1. **Inventory Non-Negativity**: Under no circumstance may total allocated inventory exceed on-hand inventory (`allocated <= on_hand`, i.e., `available >= 0`). Physical stock cannot be over-subscribed.
2. **Priority-Based Allocation**: High-priority order `ORD-2026-101` receives first claim on available inventory (15 units allocated, status `FULFILLED`). Standard order `ORD-2026-102` receives remaining available inventory (5 units allocated, remaining 5 units flagged as `BACKORDERED`, status `PARTIALLY_FULFILLED`).
3. **Dispatch & 3PL Carrier Booking**: Once an order is fully allocated, generate a 3PL freight booking with carrier tracking (`CARRIER-DHL-EXPRESS`, tracking number, pickup window) and record it in `fulfillment/shipments.json`.
4. **Audit Manifest**: Perform an end-of-wave audit verifying inventory conservation (`on_hand == available + allocated`) and compile the audit manifest into `audit/manifest.json`.

## State Architecture

The repository contains the operational database state serialized in JSON files:
- `trade/orders.json`: Customer order registry and fulfillment statuses.
- `warehouse/inventory.json`: Inventory ledger containing on-hand, allocated, and available balances.
- `fulfillment/shipments.json`: 3PL carrier bookings and dispatch records.
- `audit/manifest.json`: System audit ledger and consistency verification.
