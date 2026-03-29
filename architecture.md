## System Architecture Overview

The **Munder Difflin Multi-Agent System** is a pydantic-ai based pipeline for a fictional paper supply company. It automates the end-to-end handling of customer requests: from item extraction and stock checking to quoting, restocking, and sales finalization.

The system uses **5 agents** organized in a fixed orchestration pipeline — not a dynamic router. The Orchestrator receives every customer request and drives a deterministic sequence of sub-agent calls through the `handle_customer_request` tool.

**Model**: `gpt-4.1-mini` via OpenAI-compatible provider
**Database**: SQLite (`munder_difflin.db`) via SQLAlchemy
**Framework**: pydantic-ai (`Agent`, `RunContext`, `Tool`)

---

## Agent Roles and Responsibilities

### OrchestratorAgent
- **Primary Role**: Entry point and pipeline coordinator
- **System Prompt**: Enforces customer-facing formatting rules (confirmed / restocked / cannot-fulfill sections); prohibits direct answers
- **Tool**: `handle_customer_request(customer_request, as_of_date)` — the entire pipeline runs inside this single async tool
- **Responsibilities**:
  - Receives raw customer requests from `run_test_scenarios()`
  - Calls `handle_customer_request` which drives all downstream agents
  - Formats the final customer-facing response using the output template

### InventoryAgent
- **Primary Role**: Stock level checking and stock purchase orders
- **System Prompt**: Defines three task types (INQUIRY / RESTOCK ORDER / MAINTENANCE) to prevent proactive maintenance from running when not needed
- **Tools**:
  - `check_stock_levels(item_name, as_of_date)` → `get_stock_level()`
  - `check_reorder_status(item_name, as_of_date)` → reads `inventory` table min_stock_level
  - `get_full_inventory_report(as_of_date)` → `get_all_inventory()`
  - `check_delivery_timeline(item_name, quantity, order_date)` → `get_supplier_delivery_date()`
  - `get_company_financials(as_of_date)` → `generate_financial_report()`
  - `check_cash_balance(as_of_date)` → `get_cash_balance()`
  - `place_stock_order(item_name, quantity, price, order_date)` → `create_transaction()` with type `stock_orders`
- **Called twice per insufficient-stock request**: once in Step 7b (proactive restock before quoting) and once in Step 11c (BA-directed restock orders)

### QuotingAgent
- **Primary Role**: Pricing, discount calculation, and quote generation
- **System Prompt**: Enforces a 3-step workflow — check history once, process each item, consolidate
- **Tools**:
  - `get_pricing_and_availability(item_name, quantity, as_of_date)` → reads `inventory` table + `get_stock_level()` + `get_supplier_delivery_date()`
  - `quote_history(customer_request)` → `search_quote_history()` (keyword-based search across `quotes` + `quote_requests` tables)
  - `apply_commission_and_discount(base_quote, discount)` → applies fixed 5% commission + variable loyalty discount (0–3%)
- **Pricing**: final price = `unit_price × 1.05 × (1 - loyalty_discount)`

### BusinessAdvisorAgent
- **Primary Role**: Per-item fulfillment decision making
- **System Prompt**: Defines three mutually exclusive actions per item based on status and delivery feasibility
- **No tools** — operates purely on text input (inventory summary + quote output)
- **Decision rules**:
  - `FINALIZE_ORDER`: status = Available AND current_stock ≥ qty_requested
  - `REORDER_STOCK`: status = Insufficient AND supplier delivery ≤ customer deadline
  - `CANNOT_FULFILL`: status = N/A OR delivery would miss deadline
- **Output**: JSON array `business_analysis_details` with one object per item

### SalesAgent
- **Primary Role**: Record confirmed sales transactions
- **System Prompt**: Clarifies that `price` = unit price (not total); tool computes total internally
- **Tool**:
  - `finalize_order(item_name, quantity, price, order_date)` → `create_transaction()` with type `sales`; uses `find_matching_item_by_name()` for fuzzy name resolution

---

## Request Processing Pipeline (`handle_customer_request`)

Each customer request flows through these steps in sequence:

| Step | Description |
|------|-------------|
| **1** | Normalize request text to lowercase |
| **2** | Extract customer deadline via regex (e.g. "by April 15, 2025") |
| **3** | Detect request type: `is_inquiry`, `is_quote`, `is_purchase` via keyword matching |
| **5** | Extract `(quantity, item_name)` pairs via regex; resolve item names via `find_matching_item_by_name()`; collect unresolved items |
| **6** | Call **InventoryAgent** (TASK TYPE: INQUIRY) for all resolved items |
| **7** | Parse `inventory_details` JSON from agent output |
| **7a** | Append unresolved items as `status: N/A` — no restock possible |
| **7b** | For Insufficient items: check delivery feasibility (restock qty = qty×1.1), check cash balance per item, place restock orders via InventoryAgent (TASK TYPE: RESTOCK ORDER), re-check stock, update delivery dates |
| **8** | Call **QuotingAgent** with items + delivery date overrides for restocked items |
| **9** | Parse `quote_details` JSON from quoting agent output |
| **10** | Call **BusinessAdvisorAgent** with inventory summary + quote output + customer deadline |
| **11a** | Parse `business_analysis_details` JSON from BA agent output |
| **11b** | Route `FINALIZE_ORDER` items → **SalesAgent** |
| **11c** | Route `REORDER_STOCK` items → **InventoryAgent** (TASK TYPE: RESTOCK ORDER) |
| **12** | Assemble final response from sales result + reorder result + cannot-fulfill list |

---

## Item Name Resolution (`find_matching_item_by_name`)

Four-pass fuzzy matching against the `inventory` table:
1. **Exact match** (case-insensitive)
2. **req in item** substring (e.g. "streamers" → "Party streamers")
3. **item in req** substring (e.g. "Poster paper" in "colorful poster paper")
4. **Word-overlap scoring** — stop words include `"paper"` to prevent false matches across all paper items

Returns `None` if no match — unresolved items become N/A entries.

---

## Proactive Restock Logic (Step 7b)

Triggered automatically when inventory is `Insufficient` and a customer deadline exists:

1. Restock quantity = `floor(qty_requested × 1.1)` (+10% buffer)
2. Supplier delivery date calculated via `get_supplier_delivery_date(as_of_date, qty)`
3. Customer delivery date = supplier arrival (same day — stock already on hand by then)
4. Cash check: `unit_price × qty ≤ cash_balance` (running balance decremented per item)
5. Affordable items ordered via InventoryAgent; stock re-checked via `get_stock_level()`
6. `estimated_delivery_date` in `inventory_details` set to `customer_delivery_date` for restocked items
7. Quoting agent receives delivery date overrides to avoid recomputing from `as_of_date`

---

## Database Schema

| Table | Purpose |
|-------|---------|
| `transactions` | All stock orders and sales (id, item_name, transaction_type, units, price, transaction_date) |
| `inventory` | Reference catalog: item_name, category, unit_price, current_stock, min_stock_level |
| `quote_requests` | Historical customer requests loaded from `quote_requests.csv` |
| `quotes` | Historical quote records loaded from `quotes.csv` (joined with quote_requests for search) |

**Cash balance** = `SUM(sales.price) − SUM(stock_orders.price)` up to `as_of_date`
**Stock level** = `SUM(stock_orders.units) − SUM(sales.units)` up to `as_of_date`

---

## Key Data Files

| File | Purpose |
|------|---------|
| `quote_requests_sample.csv` | 20 test scenarios processed by `run_test_scenarios()` |
| `quote_requests.csv` | Historical requests loaded into DB for quote history search |
| `quotes.csv` | Historical quotes with pricing and metadata |
| `test_results.csv` | Output: per-request results written after each run |

---

## Supplier Delivery Lead Times

| Order Quantity | Lead Time |
|----------------|-----------|
| ≤ 10 units | Same day |
| 11–100 units | 1 day |
| 101–1,000 units | 4 days |
| > 1,000 units | 7 days |

---

## Pricing Formula

```
final_unit_price = unit_price × 1.05 × (1 − loyalty_discount)
```

- `unit_price`: from `inventory` table
- `1.05`: fixed 5% sales commission
- `loyalty_discount`: 0.0–0.03 (based on quote history)
