# Smyle shopfloor demo data

Static, fully synthetic data for the TechEd 2026 Act 2 step in which Isabella adds Skalvion's shopfloor context. The files support the two placeholders on slide 5: a production pipeline and projected production capacity over time. They also provide proposed production lots for the handoff to Act 3.

**Start with `mes_synthetic_data.json`.** It contains the complete fixture and named objects that a file-backed skill or MCP can return. The CSVs contain the same core tables for visualization. Nothing needs a database, external service, vendor SDK or network connection.

## The modeled story

Morvanto needs MAT000-7B, the pre-cut jeans fabric component for the Smyle wristband. Skalvion has two accessory fabrication cells. One is committed to existing work; the other is currently idle and has future capacity after its existing reservations. Both are assumed qualified to cut and finish this material from approved denim laminate.

This is an explicit addition to the story: an electronics manufacturer must actually have an accessory conversion capability to solve a fabric-component shortage. The dataset assumes that capability, suitable tooling, staff qualifications and approved material equivalence. It does not assume that spare electronics assembly machinery can manufacture denim. No weaving, electronics assembly or complete smart-band production is modeled.

The material description, one-component-per-wristband relationship and first-week totals match the earlier `smyle_campaign_demo.json`. The local material number `SKL-DENIM-PC-07` maps to `MAT000-7B`; that mapping is a supplied synthetic assumption, not the output of a running Reltio or ontology service.

## The numbers the demo can show

| Measure | Oct 1–7 | Oct 8–14 | Full horizon |
|---|---:|---:|---:|
| Jeans-component requirement | 1,860 | 1,860 | 3,720 |
| Baseline supply | 1,000 | 1,000 | 2,000 |
| Additional components needed | **860** | **860** | **1,720** |
| Uncommitted Skalvion production capacity | 1,280 | 1,440 | 2,720 |
| Candidate capacity receivable at Morvanto during the window | **1,080** | **1,440** | **2,520** |
| Proposed recovery receipts | **860** | **860** | **1,720** |
| Delivery capacity beyond the proposed recovery | 220 | 580 | 800 |
| Uncovered requirement under the proposal | **0** | **0** | **0** |

Production capacity and receivable capacity differ because the modeled transfer takes one calendar day. The final day's 200 units of possible output would arrive outside the horizon. Unused capacity is an option, not inventory already produced. The proposal consists of ten daily lots and ends both weeks with zero residual material inventory; it does not consume all available capacity.

The first week retains the earlier fixture's 600 uncommitted components on hand plus 400 inbound. The 400 arrive on October 3. Week 2 adds a separate 600-unit receipt on October 8 and a 400-unit receipt on October 10. These exact receipt dates and the second week's demand/supply are new synthetic assumptions. Daily demand repeats the earlier jeans campaign's seven-day shape; this is a transparent scenario extension, not a trained demand forecast.

Without recovery, material availability first falls short on October 5. The proposed recovery starts production on October 2 and delivers its first lot on October 3. Every daily material requirement is covered after applying the one-day transfer lead time.

## Capacity and production assumptions

- The candidate cell has four operations: precision cutting → edge finishing → dimensional/visual inspection → pack and label. The inspection operation limits planning throughput to 40 good components per hour. Use the slowest operation's rate; do not add operation rates together.
- Staffed shifts run 08:00–16:00 every calendar day, including weekends, with a 12:00–13:00 break. Only the remaining seven shift hours are counted on October 1 because the demo clock is already 09:00.
- Existing order reservations, a one-hour target changeover on October 1, and one hour of maintenance on October 6 are deducted before new capacity is calculated. Existing jobs retain their capacity.
- The 40-good-units/hour rate includes normal performance and quality losses and is below the simulated historical rate of approximately 45.5 good units per scheduled hour. Do not apply OEE or the quality yield again to this already-net rate.
- A separate 98% planning yield determines the raw input needed for each proposed good-output quantity. Gross starts are rounded up per lot. Ten lots require 1,758 starts to target 1,720 good components.
- Each start uses 0.018 m² of denim laminate, including normal cutting waste. There are 60 m² uncommitted after existing jobs. The proposed lots require 31.644 m²; filling every available capacity slot would require 50.148 m². Raw material therefore supports both the proposal and the modeled capacity headroom.
- Quality release and packing are included before the 16:00 departure. Morvanto receives each lot at 08:00 the next calendar day. Requirements are due by the end of the stated date.
- Other components, final assembly and downstream logistics are assumed sufficient. This model supports a material-availability decision, not an end-to-end customer-delivery promise.

## File and response map

| Use | JSON path | CSV |
|---|---|---|
| Initial state: capacity unknown | `shopfloor_unavailable_response` | — |
| Plant, lines, qualified material and raw-stock readiness | `shopfloor_snapshot_response` | — |
| Production pipeline, WIP and operation status | `shopfloor_snapshot_response.pipeline_operations` | `pipeline_operations.csv` |
| Historical 15-minute counters | `shopfloor_timeseries_response.records` | `shopfloor_timeseries_15min.csv` |
| Daily observed output and OEE | `shopfloor_timeseries_response.daily_aggregates` | `shopfloor_daily_actuals.csv` |
| Free capacity and proposed output | `material_capacity_response.daily_capacity` | `capacity_projection_daily.csv` |
| Demand, receipts and cumulative coverage | `material_capacity_response.daily_material_balance` | `material_balance_daily.csv` |
| Weekly capacity summary | `material_capacity_response.weekly_summary` | `capacity_summary_weekly.csv` |
| Proposed production lots | `recovery_proposal_response.proposed_lots` | `proposed_recovery_lots.csv` |
| Decision/KPI summary | `material_capacity_response.decision_summary` | — |

The full-resolution history has 456 rows: seven complete shifts plus the current shift's first hour, at 15-minute intervals for two cells. There are 16 daily aggregate rows, eight pipeline nodes, 14 projection dates and ten proposed lots. Historical activity is on the comparable material `SKL-ACC-LINER-01`; it is not completed Smyle recovery production.

For a compact agent reply, use the snapshot or decision summary. The suggested `get_shopfloor_timeseries` route returns the 16 daily aggregate rows by default. Keep all 456 detailed rows available to the visualization code, or return only a requested cell/date range. Avoid placing the whole fixture in every agent response.

## Field meanings and calculation rules

| Field or family | Meaning |
|---|---|
| `as_of` | Frozen scenario clock. It is not the actual time the file was fetched. |
| `record_type` | Distinguishes simulated observations from projections and planning comparisons. |
| `interval_start`, `interval_end` | Half-open observation interval `[start, end)`; timestamps include the UTC offset. |
| `good_units`, `scrap_units`, `total_units` | Interval deltas at final inspection; good + scrap = total. Never sum the same units across process stages. |
| `scheduled_production_minutes` | Runtime plus unplanned downtime during assigned work. Excludes breaks and time without an order. |
| `unscheduled_idle_minutes` | Staffed time without an assigned order. It is not an equipment failure. |
| `availability_pct` | 100 × runtime / scheduled production minutes. |
| `performance_pct` | 100 × total units × ideal cycle seconds / runtime seconds. |
| `quality_pct` | 100 × good units / total units. |
| `oee_pct` | 100 × good units × ideal cycle seconds / scheduled seconds; equals availability × performance × quality when ratios are used. |
| Daily OEE | Recomputed from summed counts and durations, not an average of interval percentages. |
| `opening_wip_units`, `received_units`, `passed_units`, `scrap_units`, `closing_wip_units` | One-hour operation balance: opening + received = passed + scrap + closing. Adjacent operations reconcile transferred units. |
| `processing_units`, `queued_units` | Together equal closing WIP. Buffers are distinct between operations. |
| `planning_good_rate_per_hour` | Conservative net throughput for planning; not an instantaneous sensor reading. |
| `available_new_good_output_units` | Floor(net available minutes × 40 / 60), after commitments, break, maintenance and setup. |
| `proposed_recovery_good_output_units` | Portion of available capacity proposed for Smyle; do not stack it as additional supply on top of capacity. |
| `planned_start_units` | Ceiling(proposed good output / 0.98); used for raw-material allocation. |
| `planned_yield_loss_allowance_units` | Gross starts minus good-output target; an allowance, not observed scrap. |
| `expected_morvanto_receipt_date` | Production date + one calendar day. Capacity is available to Morvanto only on this receipt date. |
| `cumulative_baseline_supply_units` | Opening horizon inventory plus cumulative baseline receipts. Opening inventory appears once, not every day. |
| `cumulative_supply_with_recovery_units` | Baseline supply plus cumulative proposed recovery receipts. |
| `cumulative_shortfall_without_recovery_units` | Positive part of cumulative requirement minus cumulative baseline supply; it is a stock/backlog measure, so do not sum it over dates. |
| `projected_ending_inventory_units`, `projected_backlog_units` | Positive and negative sides of cumulative supply minus requirement; never both positive. |
| `null` in JSON / blank in CSV | Not applicable or unavailable, not zero. For example, OEE is undefined when no production was scheduled. |

OEE measures effectiveness during assigned production. It is not a measure of remaining free capacity. A lightly booked cell can have high OEE while still having spare staffed hours.

## Clock, sources and Act 3 handoff

The dataset is frozen at 2026-10-01 09:00 America/Los_Angeles to match the existing campaign fixture. Observations cover September 24 through that clock time; projections cover October 1–14. If the keynote needs different dates, shift both fixtures and every dependent timestamp together. Reading the file repeatedly returns identical data; it does not simulate streaming or update itself to the current date.

Observed line states and counters represent fabricated MES data. Demand and supply represent synthetic Morvanto planning data. Qualification, reservations, raw inventory and staffing are explicit planning assumptions. Capacity, proposed lots and recovery coverage are derived arithmetic. These sources are labeled separately in the JSON so the agent need not imply the MES itself knows campaign demand or has run an AI forecast.

All recovery lots are PROPOSED_NOT_RELEASED. No production order, transfer order or approval has been executed. Act 3 can use the same lot IDs, material mapping and decision summary to demonstrate the agent's approval/release/monitoring behavior.

The supported conclusion is: under the stated assumptions, Skalvion can cover the 860-unit material shortfall in the first week and the modeled 860-unit gap in the next week. The slide's broader phrase “all current and projected demand” should be scoped to this horizon. There is no modeled proof for all future Q4 demand.

## Provenance and validation

All plants, local IDs, rates, observations, raw-stock quantities, proposed lots and readiness assertions are fictional. The schema is vendor-neutral and does not reproduce or claim compatibility with an Oracle API. No actual Oracle system or other enterprise system was contacted. No BDC data product was created.

MES field selection follows general concepts described in SAP's [MES overview](https://www.sap.com/uk/resources/what-is-mes). OEE uses the availability/performance/quality relationship in [SAP's OEE calculations documentation](https://help.sap.com/docs/sap-digital-manufacturing/insights/oee-calculations). These references inform the concepts only; they do not supply or endorse any sample number, factory capability or manufacturing method here.

Generation checks confirm first-week compatibility with the earlier campaign fixture; interval time and quantity balances; operation WIP conservation; daily/weekly/lot totals; raw-material sufficiency; one-day transfer timing; capacity limits; and zero uncovered daily material requirements under the proposal. The JSON contains the validation summary and every explicit assumption.
