# Munder Difflin Multi-Agent System — Design Notes & Reflection

## R1. Agent Workflow Explanation and Architecture Decisions

### Overview

The system uses five pydantic-ai agents organized in a fixed orchestration pipeline (not a dynamic router). The Orchestrator receives every customer request and drives a deterministic sequence of sub-agent calls through a single async tool: `handle_customer_request`.

### Why a Fixed Pipeline Instead of a Dynamic Router?

Customer requests at a paper supply company follow a predictable lifecycle: check stock → get a price → decide what's orderable → sell or restock. A dynamic router would add latency and unpredictability for no benefit — every valid request needs all four steps regardless of its surface form. A fixed pipeline also makes testing and auditing straightforward: each step is numbered and logged.

### Agent Design Decisions

**OrchestratorAgent** — entry point only. Its sole job is to receive customer text and call `handle_customer_request`. All business logic lives in the tool, not in the LLM. This prevents the orchestrator from improvising answers or skipping steps.

**InventoryAgent** — called up to three times per request (INQUIRY, proactive RESTOCK, BA-directed RESTOCK). A task-type routing prefix in every prompt (`TASK TYPE: INQUIRY / RESTOCK ORDER`) prevents the agent from accidentally running maintenance tools when the intent is a simple stock check.

**QuotingAgent** — enforces a three-step workflow in its system prompt: (1) check history once, (2) price each item, (3) consolidate. The loyalty discount (0–3%) is determined by `search_quote_history`, giving repeat customers a small benefit without complex loyalty logic.

**BusinessAdvisorAgent** — has no tools. It receives a structured text summary of inventory status and quote data, and outputs a JSON array with one action per item (`FINALIZE_ORDER`, `REORDER_STOCK`, or `CANNOT_FULFILL`). Keeping it tool-free ensures its decisions are based purely on what the pipeline explicitly hands it, preventing it from independently querying the DB.

**SalesAgent** — writes exactly one `sales` transaction per confirmed item. It uses `find_matching_item_by_name` for fuzzy name resolution so minor discrepancies between the customer's wording and the DB item name don't block a sale.

### Key Architectural Patterns

- **JSON-tagged outputs**: Every sub-agent is prompted to embed a named JSON array (e.g. `inventory_details: [...]`) in its free-text response. The pipeline extracts these with a regex + `json.loads` pass, giving a structured handoff between agents without requiring pydantic output models.
- **Proactive restock before quoting** (`_run_proactive_restock`): When stock is Insufficient and the customer has a deadline, the system automatically checks delivery feasibility and available cash, places a restock order, and re-queries stock before passing data to the QuotingAgent. This avoids quoting on phantom stock.
- **Delivery date override**: After a proactive restock, the confirmed arrival date is passed directly to the QuotingAgent to prevent it from recomputing the lead time from `as_of_date` (which would return the same-day or shorter value, ignoring when the stock actually arrives).
- **Four-pass item name resolution** (`find_matching_item_by_name`): Exact → substring → reverse substring → word-overlap with stop words (including "paper" to prevent false matches across paper product lines). This tolerates customer wording like "A4 printer paper" matching "A4 Paper" without ambiguity.

---

## R2. Evaluation Results — Strengths and Observations

### Test Run Summary (20 scenarios, April 2025)

All 20 test scenarios from `quote_requests_sample.csv` were processed successfully. The system correctly handled:

- **Mixed-status requests**: Requests containing a mix of Available, Insufficient, and catalog-missing items were partitioned correctly. Each item received the right action (FINALIZE, REORDER, or CANNOT_FULFILL) independently.
- **Proactive restock**: Requests with tight deadlines (e.g. April 10) triggered automatic restock checks. Items where supplier delivery would miss the deadline were correctly kept as Insufficient rather than restocked.
- **Cash guard**: The running cash balance check prevented over-committing funds when multiple items required restocking in the same request.
- **Unresolved item handling**: Items not in the catalog (e.g. "flyers", "tickets") were extracted but marked N/A without crashing the pipeline. The BA agent correctly assigned CANNOT_FULFILL to all N/A items.
- **Quantity parsing robustness**: Quantities like "10,000 sheets" and item names like `8.5"x11" colored paper` are parsed correctly by the regex extractor.

### Financial Outcomes

- Cash balance started at approximately $45,000 and fluctuated across requests as sales revenue came in and restock orders went out.
- Inventory value decreased as stock was sold, and increased when proactive restocks were placed.
- No request caused a negative cash balance — the cash guard held.

### Strengths

1. **Separation of concerns**: Each agent has a single well-defined responsibility. Adding a new agent type (e.g. a returns agent) would require adding one agent and one routing branch, not restructuring the pipeline.
2. **Deterministic pipeline**: The fixed orchestration order means behavior is predictable and debuggable. Logging at each step makes it straightforward to trace a failure.
3. **Graceful degradation**: Unrecognized items, parse failures, and deadline misses all produce informative customer-facing messages rather than crashes.

---

## R3. Improvement Suggestions

### Improvement 1 — Replace Regex Item Extraction with an LLM-based NER Step

The current item/quantity extractor uses a hand-crafted regex pattern. This works well for structured phrases like "200 sheets of A4 glossy paper" but fails for conversational phrasing like "I need some cardstock and about five hundred sheets of the glossy stuff". A dedicated extraction agent (or a structured output call to the LLM with a `List[ItemRequest]` response model) would handle free-form language more robustly. The extracted list could then be passed to `find_matching_item_by_name` exactly as today.

### Improvement 2 — Caching and Batching DB Calls in the QuotingAgent

Currently, the QuotingAgent calls `get_pricing_and_availability` once per item, and each call issues separate SQL queries for unit price, stock level, and supplier lead time. For a request with many line items, this multiplies latency linearly. A batch version of `get_pricing_and_availability` that accepts a list of item names and returns all rows in a single query would significantly reduce round-trips. Similarly, `search_quote_history` is called once per request — the result could be cached in the agent's context so it doesn't re-run if the orchestrator retries.

### Improvement 3 — Structured Output Models Instead of Regex JSON Extraction

The current pipeline uses regex + `json.loads` to extract named JSON arrays from free-text LLM output (e.g. `inventory_details: [...]`). This is fragile — a model that outputs slightly different whitespace or label casing will cause a parse failure. pydantic-ai supports typed `output_type` models; replacing free-text output with `output_type=List[InventoryItem]` for each sub-agent would make the handoffs between pipeline steps fully type-safe and eliminate the need for defensive regex parsing.
