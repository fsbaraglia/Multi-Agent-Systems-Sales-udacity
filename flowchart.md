# Munder Difflin Multi-Agent System — Flow Diagram

```mermaid
flowchart TD
    START([Customer Request\n+ request_date]) --> ORCH[Orchestrator Agent\ngpt-4.1-mini]

    ORCH -->|calls handle_customer_request| PIPE

    subgraph PIPE [handle_customer_request Pipeline]
        direction TB

        S1[Step 1-4\nNormalize · Extract Deadline\nClassify Type · Detect Mood] --> S5

        S5[Step 5\nExtract items + quantities\nvia regex] --> S5a{Item in catalog?}
        S5a -->|Yes| RESOLVED[Resolved items list]
        S5a -->|No| UNRESOLVED[Unresolved → N/A queue]

        RESOLVED --> S6

        subgraph S6 [Step 6 — InventoryAgent INQUIRY]
            INV_CHK[check_stock_levels\nper resolved item] --> INV_JSON[inventory_details JSON\nAvailable / Insufficient / N/A]
        end

        S6 --> S7[Step 7\nParse inventory_details]
        UNRESOLVED --> S7a[Step 7a\nAppend unresolved as N/A\nno restock possible]
        S7 --> S7a

        S7a --> S7b{Any Insufficient?}

        S7b -->|No| S8
        S7b -->|Yes| RESTOCK

        subgraph RESTOCK [Step 7b — Proactive Restock]
            direction TB
            RS1[Qty × 1.1 buffer] --> RS2[get_supplier_delivery_date]
            RS2 --> RS3{Delivery ≤ deadline?}
            RS3 -->|No| RS_SKIP[Keep Insufficient]
            RS3 -->|Yes| RS4[Check cash balance]
            RS4 --> RS5{Cash sufficient?}
            RS5 -->|No| RS_SKIP
            RS5 -->|Yes| RS6[InventoryAgent RESTOCK ORDER\nplace_stock_order]
            RS6 --> RS7[Re-check stock via get_stock_level\nUpdate status + delivery date]
        end

        RESTOCK --> S8

        subgraph S8 [Step 8 — QuotingAgent]
            direction TB
            Q1[quote_history\none call per request] --> Q2[get_pricing_and_availability\nper item]
            Q2 --> Q3[apply_commission_and_discount\n5% commission\n+ loyalty discount 0-3%\n+ mood discount 0-2%]
            Q3 --> Q4[quote_details JSON]
        end

        S8 --> S10

        subgraph S10 [Step 10 — BusinessAdvisorAgent]
            direction TB
            BA1[Receives inventory_details\n+ quote_details\n+ customer deadline] --> BA2{Per-item decision}
            BA2 -->|Available + stock OK| BA_FIN[FINALIZE_ORDER]
            BA2 -->|Insufficient + delivery OK| BA_RES[REORDER_STOCK]
            BA2 -->|N/A or deadline missed| BA_CAN[CANNOT_FULFILL]
        end

        S10 --> S11[Step 11\nParse business_analysis_details]

        S11 --> ROUTE{Route by action}

        ROUTE -->|FINALIZE_ORDER| SALES
        ROUTE -->|REORDER_STOCK| REINV
        ROUTE -->|CANNOT_FULFILL| CANNOTFULFILL[Build cannot-fulfill message]

        subgraph SALES [Step 11b — SalesAgent]
            SA1[finalize_order\nper item\nunit_price × qty = total] --> SA2[Sales transaction\ncreate_transaction type=sales]
        end

        subgraph REINV [Step 11c — InventoryAgent RESTOCK ORDER]
            RI1[place_stock_order\nper item] --> RI2[Stock transaction\ncreate_transaction type=stock_orders]
        end

        SALES --> S12[Step 12\nAssemble final response]
        REINV --> S12
        CANNOTFULFILL --> S12
    end

    PIPE --> ORCH
    ORCH -->|formats customer response| END([Final Response\nto Customer])

    subgraph MOOD [detect_customer_mood]
        M1[Polite keywords +1\nEnthusiasm keywords +2\nFrustration keywords -1] --> M2[Score → extra discount\n≥3: 2.0%\n2: 1.5%\n1: 1.0%\n≤0: 0%]
    end

    S1 -.->|mood score| MOOD
    MOOD -.->|mood_discount| S8

    subgraph FUZZY [find_matching_item_by_name]
        F1[1. Exact match] --> F2[2. req in item substring]
        F2 --> F3[3. item in req substring]
        F3 --> F4[4. Word-overlap score\nexcluding 'paper']
        F4 --> F5{Match found?}
        F5 -->|Yes| F6[Resolved item name]
        F5 -->|No| F7[None → N/A]
    end

    S5 -.->|per candidate| FUZZY

    subgraph DB [SQLite — munder_difflin.db]
        DB1[(inventory\nitem_name · unit_price\ncurrent_stock · min_stock)]
        DB2[(quote_requests\n+ quotes)]
        DB3[(transactions\nstock_orders · sales)]
    end

    INV_CHK -.-> DB1
    Q1 -.-> DB2
    Q2 -.-> DB1
    SA2 -.-> DB3
    RI2 -.-> DB3
    RS6 -.-> DB3
    RS7 -.-> DB3
```

---

## Agent Hierarchy

```mermaid
graph TD
    ORCH([Orchestrator Agent]) -->|handle_customer_request| INV[Inventory Agent]
    ORCH -->|handle_customer_request| QUOT[Quoting Agent]
    ORCH -->|handle_customer_request| BA[Business Advisor Agent]
    ORCH -->|handle_customer_request| SALES[Sales Agent]

    INV -->|INQUIRY| INV_T1[check_stock_levels\ncheck_reorder_status\nget_full_inventory_report\ncheck_delivery_timeline]
    INV -->|RESTOCK ORDER| INV_T2[place_stock_order\ncheck_cash_balance\nget_company_financials]
    QUOT --> Q_T[get_pricing_and_availability\nquote_history\napply_commission_and_discount]
    BA --> BA_T[No tools — text analysis only\nOutputs business_analysis_details JSON]
    SALES --> S_T[finalize_order]
```

---

## Key Decision Points

| Decision | Location | Outcome |
|---|---|---|
| Item in catalog? | Step 5 — `find_matching_item_by_name` | Resolved → inventory check / Unresolved → N/A |
| Sufficient stock? | Step 7 — inventory_details | Available → quote / Insufficient → proactive restock attempt |
| Delivery ≤ deadline? | Step 7b — proactive restock | Yes → try restock / No → keep Insufficient |
| Cash sufficient? | Step 7b — cash check before restock | Yes → place order / No → keep Insufficient |
| BA action? | Step 10 — BusinessAdvisorAgent | FINALIZE → SalesAgent / REORDER → InventoryAgent / CANNOT → message |
| Mood score? | Step 4 — `detect_customer_mood` | Extra discount 0–2% added to quoting agent |

## Pricing Formula

```
final_unit_price = unit_price × 1.05 × (1 − loyalty_discount − mood_discount)
```
