import pandas as pd
import numpy as np
import os
import sys
import time
import dotenv
import ast
from sqlalchemy.sql import text
from datetime import datetime, timedelta
from typing import Dict, List, Union
from sqlalchemy import create_engine, Engine

# Create an SQLite database
db_engine = create_engine("sqlite:///munder_difflin.db")

# List containing the different kinds of papers 
paper_supplies = [
    # Paper Types (priced per sheet unless specified)
    {"item_name": "A4 paper",                         "category": "paper",        "unit_price": 0.05},
    {"item_name": "Letter-sized paper",              "category": "paper",        "unit_price": 0.06},
    {"item_name": "Cardstock",                        "category": "paper",        "unit_price": 0.15},
    {"item_name": "Colored paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Glossy paper",                     "category": "paper",        "unit_price": 0.20},
    {"item_name": "Matte paper",                      "category": "paper",        "unit_price": 0.18},
    {"item_name": "Recycled paper",                   "category": "paper",        "unit_price": 0.08},
    {"item_name": "Eco-friendly paper",               "category": "paper",        "unit_price": 0.12},
    {"item_name": "Poster paper",                     "category": "paper",        "unit_price": 0.25},
    {"item_name": "Banner paper",                     "category": "paper",        "unit_price": 0.30},
    {"item_name": "Kraft paper",                      "category": "paper",        "unit_price": 0.10},
    {"item_name": "Construction paper",               "category": "paper",        "unit_price": 0.07},
    {"item_name": "Wrapping paper",                   "category": "paper",        "unit_price": 0.15},
    {"item_name": "Glitter paper",                    "category": "paper",        "unit_price": 0.22},
    {"item_name": "Decorative paper",                 "category": "paper",        "unit_price": 0.18},
    {"item_name": "Letterhead paper",                 "category": "paper",        "unit_price": 0.12},
    {"item_name": "Legal-size paper",                 "category": "paper",        "unit_price": 0.08},
    {"item_name": "Crepe paper",                      "category": "paper",        "unit_price": 0.05},
    {"item_name": "Photo paper",                      "category": "paper",        "unit_price": 0.25},
    {"item_name": "Uncoated paper",                   "category": "paper",        "unit_price": 0.06},
    {"item_name": "Butcher paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Heavyweight paper",                "category": "paper",        "unit_price": 0.20},
    {"item_name": "Standard copy paper",              "category": "paper",        "unit_price": 0.04},
    {"item_name": "Bright-colored paper",             "category": "paper",        "unit_price": 0.12},
    {"item_name": "Patterned paper",                  "category": "paper",        "unit_price": 0.15},

    # Product Types (priced per unit)
    {"item_name": "Paper plates",                     "category": "product",      "unit_price": 0.10},  # per plate
    {"item_name": "Paper cups",                       "category": "product",      "unit_price": 0.08},  # per cup
    {"item_name": "Paper napkins",                    "category": "product",      "unit_price": 0.02},  # per napkin
    {"item_name": "Disposable cups",                  "category": "product",      "unit_price": 0.10},  # per cup
    {"item_name": "Table covers",                     "category": "product",      "unit_price": 1.50},  # per cover
    {"item_name": "Envelopes",                        "category": "product",      "unit_price": 0.05},  # per envelope
    {"item_name": "Sticky notes",                     "category": "product",      "unit_price": 0.03},  # per sheet
    {"item_name": "Notepads",                         "category": "product",      "unit_price": 2.00},  # per pad
    {"item_name": "Invitation cards",                 "category": "product",      "unit_price": 0.50},  # per card
    {"item_name": "Flyers",                           "category": "product",      "unit_price": 0.15},  # per flyer
    {"item_name": "Party streamers",                  "category": "product",      "unit_price": 0.05},  # per roll
    {"item_name": "Decorative adhesive tape (washi tape)", "category": "product", "unit_price": 0.20},  # per roll
    {"item_name": "Paper party bags",                 "category": "product",      "unit_price": 0.25},  # per bag
    {"item_name": "Name tags with lanyards",          "category": "product",      "unit_price": 0.75},  # per tag
    {"item_name": "Presentation folders",             "category": "product",      "unit_price": 0.50},  # per folder

    # Large-format items (priced per unit)
    {"item_name": "Large poster paper (24x36 inches)", "category": "large_format", "unit_price": 1.00},
    {"item_name": "Rolls of banner paper (36-inch width)", "category": "large_format", "unit_price": 2.50},

    # Specialty papers
    {"item_name": "100 lb cover stock",               "category": "specialty",    "unit_price": 0.50},
    {"item_name": "80 lb text paper",                 "category": "specialty",    "unit_price": 0.40},
    {"item_name": "250 gsm cardstock",                "category": "specialty",    "unit_price": 0.30},
    {"item_name": "220 gsm poster paper",             "category": "specialty",    "unit_price": 0.35},
]

# Given below are some utility functions you can use to implement your multi-agent system

def generate_sample_inventory(paper_supplies: list, coverage: float = 0.4, seed: int = 137) -> pd.DataFrame:
    """
    Generate inventory for exactly a specified percentage of items from the full paper supply list.

    This function randomly selects exactly `coverage` × N items from the `paper_supplies` list,
    and assigns each selected item:
    - a random stock quantity between 200 and 800,
    - a minimum stock level between 50 and 150.

    The random seed ensures reproducibility of selection and stock levels.

    Args:
        paper_supplies (list): A list of dictionaries, each representing a paper item with
                               keys 'item_name', 'category', and 'unit_price'.
        coverage (float, optional): Fraction of items to include in the inventory (default is 0.4, or 40%).
        seed (int, optional): Random seed for reproducibility (default is 137).

    Returns:
        pd.DataFrame: A DataFrame with the selected items and assigned inventory values, including:
                      - item_name
                      - category
                      - unit_price
                      - current_stock
                      - min_stock_level
    """
    # Ensure reproducible random output
    np.random.seed(seed)

    # Calculate number of items to include based on coverage
    num_items = int(len(paper_supplies) * coverage)

    # Randomly select item indices without replacement
    selected_indices = np.random.choice(
        range(len(paper_supplies)),
        size=num_items,
        replace=False
    )

    # Extract selected items from paper_supplies list
    selected_items = [paper_supplies[i] for i in selected_indices]

    # Construct inventory records
    inventory = []
    for item in selected_items:
        inventory.append({
            "item_name": item["item_name"],
            "category": item["category"],
            "unit_price": item["unit_price"],
            "current_stock": np.random.randint(200, 800),  # Realistic stock range
            "min_stock_level": np.random.randint(50, 150)  # Reasonable threshold for reordering
        })

    # Return inventory as a pandas DataFrame
    return pd.DataFrame(inventory)

def init_database(db_engine: Engine, seed: int = 137) -> Engine:    
    """
    Set up the Munder Difflin database with all required tables and initial records.

    This function performs the following tasks:
    - Creates the 'transactions' table for logging stock orders and sales
    - Loads customer inquiries from 'quote_requests.csv' into a 'quote_requests' table
    - Loads previous quotes from 'quotes.csv' into a 'quotes' table, extracting useful metadata
    - Generates a random subset of paper inventory using `generate_sample_inventory`
    - Inserts initial financial records including available cash and starting stock levels

    Args:
        db_engine (Engine): A SQLAlchemy engine connected to the SQLite database.
        seed (int, optional): A random seed used to control reproducibility of inventory stock levels.
                              Default is 137.

    Returns:
        Engine: The same SQLAlchemy engine, after initializing all necessary tables and records.

    Raises:
        Exception: If an error occurs during setup, the exception is printed and raised.
    """
    try:
        # ----------------------------
        # 1. Create an empty 'transactions' table schema
        # ----------------------------
        transactions_schema = pd.DataFrame({
            "id": [],
            "item_name": [],
            "transaction_type": [],  # 'stock_orders' or 'sales'
            "units": [],             # Quantity involved
            "price": [],             # Total price for the transaction
            "transaction_date": [],  # ISO-formatted date
        })
        transactions_schema.to_sql("transactions", db_engine, if_exists="replace", index=False)

        # Set a consistent starting date
        initial_date = datetime(2025, 1, 1).isoformat()

        # ----------------------------
        # 2. Load and initialize 'quote_requests' table
        # ----------------------------
        quote_requests_df = pd.read_csv("quote_requests.csv")
        quote_requests_df["id"] = range(1, len(quote_requests_df) + 1)
        quote_requests_df.to_sql("quote_requests", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 3. Load and transform 'quotes' table
        # ----------------------------
        quotes_df = pd.read_csv("quotes.csv")
        quotes_df["request_id"] = range(1, len(quotes_df) + 1)
        quotes_df["order_date"] = initial_date

        # Unpack metadata fields (job_type, order_size, event_type) if present
        if "request_metadata" in quotes_df.columns:
            quotes_df["request_metadata"] = quotes_df["request_metadata"].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) else x
            )
            quotes_df["job_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("job_type", ""))
            quotes_df["order_size"] = quotes_df["request_metadata"].apply(lambda x: x.get("order_size", ""))
            quotes_df["event_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("event_type", ""))

        # Retain only relevant columns
        quotes_df = quotes_df[[
            "request_id",
            "total_amount",
            "quote_explanation",
            "order_date",
            "job_type",
            "order_size",
            "event_type"
        ]]
        quotes_df.to_sql("quotes", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 4. Generate inventory and seed stock
        # ----------------------------
        inventory_df = generate_sample_inventory(paper_supplies, seed=seed)

        # Seed initial transactions
        initial_transactions = []

        # Add a starting cash balance via a dummy sales transaction
        initial_transactions.append({
            "item_name": None,
            "transaction_type": "sales",
            "units": None,
            "price": 50000.0,
            "transaction_date": initial_date,
        })

        # Add one stock order transaction per inventory item
        for _, item in inventory_df.iterrows():
            initial_transactions.append({
                "item_name": item["item_name"],
                "transaction_type": "stock_orders",
                "units": item["current_stock"],
                "price": item["current_stock"] * item["unit_price"],
                "transaction_date": initial_date,
            })

        # Commit transactions to database
        pd.DataFrame(initial_transactions).to_sql("transactions", db_engine, if_exists="append", index=False)

        # Save the inventory reference table
        inventory_df.to_sql("inventory", db_engine, if_exists="replace", index=False)

        return db_engine

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def create_transaction(
    item_name: str,
    transaction_type: str,
    quantity: int,
    price: float,
    date: Union[str, datetime],
) -> int:
    """
    This function records a transaction of type 'stock_orders' or 'sales' with a specified
    item name, quantity, total price, and transaction date into the 'transactions' table of the database.

    Args:
        item_name (str): The name of the item involved in the transaction.
        transaction_type (str): Either 'stock_orders' or 'sales'.
        quantity (int): Number of units involved in the transaction.
        price (float): Total price of the transaction.
        date (str or datetime): Date of the transaction in ISO 8601 format.

    Returns:
        int: The ID of the newly inserted transaction.

    Raises:
        ValueError: If `transaction_type` is not 'stock_orders' or 'sales'.
        Exception: For other database or execution errors.
    """
    try:
        # Convert datetime to ISO string if necessary
        date_str = date.isoformat() if isinstance(date, datetime) else date

        # Validate transaction type
        if transaction_type not in {"stock_orders", "sales"}:
            raise ValueError("Transaction type must be 'stock_orders' or 'sales'")

        # Prepare transaction record as a single-row DataFrame
        transaction = pd.DataFrame([{
            "item_name": item_name,
            "transaction_type": transaction_type,
            "units": quantity,
            "price": price,
            "transaction_date": date_str,
        }])

        # Insert the record into the database
        transaction.to_sql("transactions", db_engine, if_exists="append", index=False)

        # Fetch and return the ID of the inserted row
        result = pd.read_sql("SELECT last_insert_rowid() as id", db_engine)
        return int(result.iloc[0]["id"])

    except Exception as e:
        print(f"Error creating transaction: {e}")
        raise

def get_all_inventory(as_of_date: str) -> Dict[str, int]:
    """
    Retrieve a snapshot of available inventory as of a specific date.

    This function calculates the net quantity of each item by summing 
    all stock orders and subtracting all sales up to and including the given date.

    Only items with positive stock are included in the result.

    Args:
        as_of_date (str): ISO-formatted date string (YYYY-MM-DD) representing the inventory cutoff.

    Returns:
        Dict[str, int]: A dictionary mapping item names to their current stock levels.
    """
    # SQL query to compute stock levels per item as of the given date
    query = """
        SELECT
            item_name,
            SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END) as stock
        FROM transactions
        WHERE item_name IS NOT NULL
        AND transaction_date <= :as_of_date
        GROUP BY item_name
        HAVING stock > 0
    """

    # Execute the query with the date parameter
    result = pd.read_sql(query, db_engine, params={"as_of_date": as_of_date})

    # Convert the result into a dictionary {item_name: stock}
    return dict(zip(result["item_name"], result["stock"]))

def get_stock_level(item_name: str, as_of_date: Union[str, datetime]) -> pd.DataFrame:
    """
    Retrieve the stock level of a specific item as of a given date.

    This function calculates the net stock by summing all 'stock_orders' and 
    subtracting all 'sales' transactions for the specified item up to the given date.

    Args:
        item_name (str): The name of the item to look up.
        as_of_date (str or datetime): The cutoff date (inclusive) for calculating stock.

    Returns:
        pd.DataFrame: A single-row DataFrame with columns 'item_name' and 'current_stock'.
    """
    # Convert date to ISO string format if it's a datetime object
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # SQL query to compute net stock level for the item
    stock_query = """
        SELECT
            item_name,
            COALESCE(SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END), 0) AS current_stock
        FROM transactions
        WHERE item_name = :item_name
        AND transaction_date <= :as_of_date
    """

    # Execute query and return result as a DataFrame
    return pd.read_sql(
        stock_query,
        db_engine,
        params={"item_name": item_name, "as_of_date": as_of_date},
    )

def get_supplier_delivery_date(input_date_str: str, quantity: int) -> str:
    """
    Estimate the supplier delivery date based on the requested order quantity and a starting date.

    Delivery lead time increases with order size:
        - ≤10 units: same day
        - 11–100 units: 1 day
        - 101–1000 units: 4 days
        - >1000 units: 7 days

    Args:
        input_date_str (str): The starting date in ISO format (YYYY-MM-DD).
        quantity (int): The number of units in the order.

    Returns:
        str: Estimated delivery date in ISO format (YYYY-MM-DD).
    """
    # Debug log (comment out in production if needed)
    print(f"FUNC (get_supplier_delivery_date): Calculating for qty {quantity} from date string '{input_date_str}'")

    # Attempt to parse the input date
    try:
        input_date_dt = datetime.fromisoformat(input_date_str.split("T")[0])
    except (ValueError, TypeError):
        # Fallback to current date on format error
        print(f"WARN (get_supplier_delivery_date): Invalid date format '{input_date_str}', using today as base.")
        input_date_dt = datetime.now()

    # Determine delivery delay based on quantity
    if quantity <= 10:
        days = 0
    elif quantity <= 100:
        days = 1
    elif quantity <= 1000:
        days = 4
    else:
        days = 7

    # Add delivery days to the starting date
    delivery_date_dt = input_date_dt + timedelta(days=days)

    # Return formatted delivery date
    return delivery_date_dt.strftime("%Y-%m-%d")

def get_cash_balance(as_of_date: Union[str, datetime]) -> float:
    """
    Calculate the current cash balance as of a specified date.

    The balance is computed by subtracting total stock purchase costs ('stock_orders')
    from total revenue ('sales') recorded in the transactions table up to the given date.

    Args:
        as_of_date (str or datetime): The cutoff date (inclusive) in ISO format or as a datetime object.

    Returns:
        float: Net cash balance as of the given date. Returns 0.0 if no transactions exist or an error occurs.
    """
    try:
        # Convert date to ISO format if it's a datetime object
        if isinstance(as_of_date, datetime):
            as_of_date = as_of_date.isoformat()

        # Query all transactions on or before the specified date
        transactions = pd.read_sql(
            "SELECT * FROM transactions WHERE transaction_date <= :as_of_date",
            db_engine,
            params={"as_of_date": as_of_date},
        )

        # Compute the difference between sales and stock purchases
        if not transactions.empty:
            total_sales = transactions.loc[transactions["transaction_type"] == "sales", "price"].sum()
            total_purchases = transactions.loc[transactions["transaction_type"] == "stock_orders", "price"].sum()
            return float(total_sales - total_purchases)

        return 0.0

    except Exception as e:
        print(f"Error getting cash balance: {e}")
        return 0.0


def generate_financial_report(as_of_date: Union[str, datetime]) -> Dict:
    """
    Generate a complete financial report for the company as of a specific date.

    This includes:
    - Cash balance
    - Inventory valuation
    - Combined asset total
    - Itemized inventory breakdown
    - Top 5 best-selling products

    Args:
        as_of_date (str or datetime): The date (inclusive) for which to generate the report.

    Returns:
        Dict: A dictionary containing the financial report fields:
            - 'as_of_date': The date of the report
            - 'cash_balance': Total cash available
            - 'inventory_value': Total value of inventory
            - 'total_assets': Combined cash and inventory value
            - 'inventory_summary': List of items with stock and valuation details
            - 'top_selling_products': List of top 5 products by revenue
    """
    # Normalize date input
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # Get current cash balance
    cash = get_cash_balance(as_of_date)

    # Get current inventory snapshot
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    inventory_value = 0.0
    inventory_summary = []

    # Compute total inventory value and summary by item
    for _, item in inventory_df.iterrows():
        stock_info = get_stock_level(item["item_name"], as_of_date)
        stock = stock_info["current_stock"].iloc[0]
        item_value = stock * item["unit_price"]
        inventory_value += item_value

        inventory_summary.append({
            "item_name": item["item_name"],
            "stock": stock,
            "unit_price": item["unit_price"],
            "value": item_value,
        })

    # Identify top-selling products by revenue
    top_sales_query = """
        SELECT item_name, SUM(units) as total_units, SUM(price) as total_revenue
        FROM transactions
        WHERE transaction_type = 'sales' AND transaction_date <= :date
        GROUP BY item_name
        ORDER BY total_revenue DESC
        LIMIT 5
    """
    top_sales = pd.read_sql(top_sales_query, db_engine, params={"date": as_of_date})
    top_selling_products = top_sales.to_dict(orient="records")

    return {
        "as_of_date": as_of_date,
        "cash_balance": cash,
        "inventory_value": inventory_value,
        "total_assets": cash + inventory_value,
        "inventory_summary": inventory_summary,
        "top_selling_products": top_selling_products,
    }


def search_quote_history(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """
    Retrieve a list of historical quotes that match any of the provided search terms.

    The function searches both the original customer request (from `quote_requests`) and
    the explanation for the quote (from `quotes`) for each keyword. Results are sorted by
    most recent order date and limited by the `limit` parameter.

    Args:
        search_terms (List[str]): List of terms to match against customer requests and explanations.
        limit (int, optional): Maximum number of quote records to return. Default is 5.

    Returns:
        List[Dict]: A list of matching quotes, each represented as a dictionary with fields:
            - original_request
            - total_amount
            - quote_explanation
            - job_type
            - order_size
            - event_type
            - order_date
    """
    conditions = []
    params = {}

    # Build SQL WHERE clause using LIKE filters for each search term
    for i, term in enumerate(search_terms):
        param_name = f"term_{i}"
        conditions.append(
            f"(LOWER(qr.response) LIKE :{param_name} OR "
            f"LOWER(q.quote_explanation) LIKE :{param_name})"
        )
        params[param_name] = f"%{term.lower()}%"

    # Combine conditions; fallback to always-true if no terms provided
    where_clause = " OR ".join(conditions) if conditions else "1=1"

    # Final SQL query to join quotes with quote_requests
    query = f"""
        SELECT
            qr.response AS original_request,
            q.total_amount,
            q.quote_explanation,
            q.job_type,
            q.order_size,
            q.event_type,
            q.order_date
        FROM quotes q
        JOIN quote_requests qr ON q.request_id = qr.id
        WHERE {where_clause}
        ORDER BY q.order_date DESC
        LIMIT {limit}
    """

    # Execute parameterized query
    with db_engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]

########################
########################
########################
# YOUR MULTI AGENT STARTS HERE
########################
########################
########################


# Set up and load your env parameters and instantiate your model.

import os
import re
import json

from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from dataclasses import dataclass

dotenv.load_dotenv()
open_ai_key = os.getenv("OPENAI_API_KEY")

provider = OpenAIProvider(
     openai_client=AsyncOpenAI(
         api_key=open_ai_key,
         #base_url="https://openai.vocareum.com/v1",
     )
 )
model = OpenAIModel("gpt-4o", provider=provider)

# Agents and Orchestrator initiatization
orchestrator = Agent()
inventory_agent = Agent()
quoting_agent = Agent()
business_advisor_agent = Agent()
sales_agent = Agent()


"""Set up tools for your agents to use, these should be methods that combine the database functions above
 and apply criteria to them to ensure that the flow of the system is correct."""

def find_matching_item_by_name(requested_name: str) -> str:
    """
    Find the 
    """
    inventory_items = pd.read_sql(
        "SELECT item_name FROM inventory", db_engine
    )["item_name"].tolist()

    if not inventory_items:
        return None

    req = requested_name.strip().lower()

    # 1. Exact match
    for item in inventory_items:
        if item.lower() == req:
            return item

    # 2 & 3. Bidirectional substring — single pass, prefer "req in item" (more specific)
    substring_match = None
    for item in inventory_items:
        item_lower = item.lower()
        if req in item_lower:               # e.g. "streamers" in "Party streamers"
            return item
        if item_lower in req and substring_match is None:
            substring_match = item          # e.g. "Poster paper" in "colorful poster paper"
    if substring_match:
        return substring_match

    # 4. Word-overlap scoring (keep product codes like "a4", "a3")
    # "paper" is excluded because it appears in almost every item name and produces false matches
    stop_words = {"the", "a", "an", "of", "for", "and", "or", "with", "in", "on", "paper", "papers"}
    req_words = {w for w in req.split() if w not in stop_words}
    if not req_words:
        return None

    best_item, best_score = None, 0
    for item in inventory_items:
        item_words = {w for w in item.lower().split() if w not in stop_words}
        score = len(req_words & item_words)
        if score > best_score:
            best_score, best_item = score, item

    return best_item if best_score > 0 else None

# Tools for inventory agent

INVENTORY_SYSTEM_PROMPT = """\
You are the Inventory Agent for Munder Difflin, a paper supply company.
Your goal is to accurately report stock levels and place stock orders when instructed.

**Always pass the `as_of_date` provided in the task to every tool call.**

## Available Tools
- `get_full_inventory_report(as_of_date)` — returns all items with current stock and minimum stock levels
- `check_stock_levels(item_name, as_of_date)` — returns current stock for a single item
- `check_reorder_status(item_name, as_of_date)` — returns whether an item is below its minimum stock threshold
- `check_delivery_timeline(item_name, quantity, order_date)` — returns the estimated supplier delivery date
- `get_company_financials(as_of_date)` — returns unit prices for all items
- `check_cash_balance(as_of_date)` — returns the current cash balance
- `place_stock_order(item_name, quantity, price, order_date)` — places a purchase order for stock

## Task Types — Read the task header to determine which workflow to follow

### TASK TYPE: INQUIRY
Goal: Check and report stock levels for the requested items. Do NOT run proactive maintenance. Do NOT call `get_full_inventory_report`.
Workflow:
1. Call `check_stock_levels` once for each item.
2. Report status using the Output Format below.

### TASK TYPE: RESTOCK ORDER
Goal: Place stock purchase orders for the specified items using the exact values provided.
Workflow:
1. For each item provided, follow the `place_stock_order` Usage Rule below to place the order.
2. Report the result of each order.

### TASK TYPE: MAINTENANCE (default if no task type header is given)
Goal: Proactively maintain healthy stock levels, then execute any additional assigned task.
Workflow:
1. **Proactive Stock Maintenance**:
   a. Use `get_full_inventory_report` to list all items.
   b. For each item, use `check_reorder_status` to find items below minimum stock.
   c. For each item needing reorder, follow the `place_stock_order` Usage Rule. Reorder quantity = `(min_stock_level - current_stock) + 40`.
2. **Execute Assigned Task**: After maintenance, execute the specific task in the request.

## `place_stock_order` Usage Rule
Before EVERY call to `place_stock_order`, execute these steps in sequence:
1. **Determine Order Cost**: Use `get_company_financials` to get `unit_price` if not already provided. Calculate total cost = `quantity * unit_price`.
2. **Check Funds**: Call `check_cash_balance` to get the current cash balance.
3. **Verify and Execute**:
   - If cash balance >= total cost → call `place_stock_order`.
   - If cash balance < total cost → do NOT place the order; report failure due to insufficient funds.

## Output Format
Report inventory status using exactly this format for each item:

1. **[Item Name]**:
   - Stock: [current_stock] units
   - Requested: [requested_quantity] units
   - Status: Available | Insufficient | N/A (use N/A if the item was not found in inventory)

**Handle Ambiguity**: If the request is ambiguous, describe your capabilities and ask for clarification. Do not place any orders if the request is ambiguous.
"""

@dataclass
class InventoryDependencies:
    db_engine: Engine
    items_name: str
    as_of_date: str
    quantity: int

class InventoryOutput(BaseModel):
    items: List[Dict] = Field(description="List of items reordered during proactive maintenance, each with item_name and quantity")
    result_assigned_task: str = Field(description="The result of the assigned task")
    order_skipped: List[Dict] = Field(description="List of orders skipped due to insufficient funds, each with item_name and reason")


def check_stock_levels(ctx: RunContext[InventoryDependencies], item_name: str, as_of_date: str) -> str:
    """Tool for the inventory agent to check the stock level of a specific item as of a given date."""
    stock_info = get_stock_level(item_name, as_of_date)
    return stock_info.to_string()


def check_reorder_status(ctx: RunContext[InventoryDependencies], item_name: str, as_of_date: str) -> str:
    """Tool for the inventory agent to check if a specific item needs to be reordered based on current stock and minimum levels."""
    stock_info = get_stock_level(item_name, as_of_date)
    current_stock = stock_info["current_stock"].iloc[0]

    inventory_df = pd.read_sql("SELECT * FROM inventory WHERE item_name = :item_name", db_engine, params={"item_name": item_name})
    if inventory_df.empty:
        return f"Item '{item_name}' not found in inventory."

    min_stock_level = inventory_df["min_stock_level"].iloc[0]
    if current_stock <= min_stock_level:
        return f"Item '{item_name}' is at or below minimum stock level (Current: {current_stock}, Min: {min_stock_level}). Reorder needed."
    else:
        return f"Item '{item_name}' is above minimum stock level (Current: {current_stock}, Min: {min_stock_level}). No reorder needed."

def get_full_inventory_report(ctx: RunContext[InventoryDependencies], as_of_date: str) -> str:
    """Tool for the inventory agent to get a full report of all items in stock as of a given date."""
    inventory_report = get_all_inventory(as_of_date)
    if not inventory_report:
        return "No inventory found."
    return pd.DataFrame.from_dict(inventory_report, orient='index', columns=['stock']).to_string()
    

def check_delivery_timeline(ctx: RunContext[InventoryDependencies],item_name: str, quantity: int, order_date: str) -> str:
    """Tool for the inventory agent to check the delivery timeline for a specific item and quantity."""
    delivery_date = get_supplier_delivery_date(order_date, quantity)
    return f"Estimated delivery date for {quantity} units of '{item_name}' ordered on {order_date}: {delivery_date}"


def check_cash_balance(ctx: RunContext[InventoryDependencies], as_of_date: str) -> str:
    """Tool for the inventory agent to check the company's cash balance as of a given date."""
    cash_balance = get_cash_balance(as_of_date)
    return f"The current cash balance is ${cash_balance:.2f}."

def get_company_financials(ctx: RunContext[InventoryDependencies], as_of_date: str) -> str:
    """
    Generates a complete financial report for the company for internal use.

    Args:
        as_of_date (str): The date for the report, in YYYY-MM-DD format.

    Returns:
        A string summarizing the financial report.
    """
    report = generate_financial_report(as_of_date)
    return (
        f"Financial Report as of {report['as_of_date']}:\n"
        f"Cash Balance: ${report['cash_balance']:.2f}\n"
        f"Inventory Value: ${report['inventory_value']:.2f}\n"
        f"Total Assets: ${report['total_assets']:.2f}\n"
        f"Top Selling Products: {report['top_selling_products']}"
    )
                                         
def place_stock_order(ctx: RunContext[InventoryDependencies], item_name: str, quantity: int, price: float, order_date: str) -> str:
    """
    Tool for the inventory agent to place a stock order for a specific item and quantity.

    Args:
        item_name (str): The name of the item to order.
        quantity (int): The number of units to order.
        price (float): The total price of the order.
        order_date (str): The date of the order, in YYYY-MM-DD format.

    Returns:
        A string confirming the stock order and providing a transaction ID, or an error message.
    """
    resolved_name = find_matching_item_by_name(item_name) or item_name
    try:
        transaction_id = create_transaction(
            item_name=resolved_name,
            transaction_type="stock_orders",
            quantity=quantity,
            price=price,
            date=order_date,
        )

        return f"Stock order placed for {quantity} units of '{resolved_name}' at a total price of ${price:.2f}. Transaction ID: {transaction_id}."
    except Exception as e:
        return f"Error placing stock order: {e}"

inventory_agent = Agent(
    model,
    #deps_type = InventoryDependencies,
    #output_type=str,
    tools=[            
        Tool(check_stock_levels, takes_ctx=True),
        Tool(check_reorder_status, takes_ctx=True),
        Tool(get_full_inventory_report, takes_ctx=True),
        Tool(check_delivery_timeline, takes_ctx=True),
        Tool(get_company_financials, takes_ctx=True),
        Tool(check_cash_balance, takes_ctx=True),
        Tool(place_stock_order, takes_ctx=True),
    ],
    system_prompt=INVENTORY_SYSTEM_PROMPT,
)

# Tools for quoting agent
QUOTING_SYSTEM_PROMPT = """\
You are the Quoting Agent for Munder Difflin, a paper supply company.
Your goal is to generate a final, consolidated quote for all items in a customer's request by following a strict, multi-step workflow.

## Available Tools
- `get_pricing_and_availability(item_name, quantity, as_of_date)` — returns unit price, total price, current stock, and estimated delivery date for one item
- `quote_history(customer_request)` — searches historical quotes using keywords from the full request; returns past pricing and discounts
- `apply_commission_and_discount(base_quote, discount)` — takes the raw string from `get_pricing_and_availability` as `base_quote` and a discount float; applies a fixed 5% commission plus the loyalty discount; returns the final per-unit price

**Always pass the `as_of_date` provided in the task to every tool call that accepts it.**

## Workflow

**Step 1 — Check Quote History (ONCE per request, before processing any item)**
Call `quote_history` once using the full customer request text. Review the results to decide a single loyalty discount rate to apply to all items.
- Rate must be a decimal between 0.0 (no discount) and 0.03 (max 3%).
- If no relevant history is found, use 0.0.

**Step 2 — Process Each Item Individually**
For each item in the request:
  a. Call `get_pricing_and_availability(item_name, quantity, as_of_date)` to get base price, stock, and delivery date.
  b. Call `apply_commission_and_discount(base_quote, discount)` using the result from step (a) and the discount rate decided in Step 1.

**Step 3 — Consolidate and Finalize**
After processing all items, combine results into a single itemized quote response. Include per-item unit price, total price, availability, and estimated delivery date.

## Output Format
After the analysis, output a JSON array named 'quote_details' with one object per item using exactly these fields:
item_name, qty_requested, current_stock, unit_price, total_price, estimated_delivery_date, availability

Example:
quote_details: [
  {"item_name": "Glossy Paper", "qty_requested": 200, "current_stock": 587, "unit_price": 0.22, "total_price": 44.00, "estimated_delivery_date": "2025-04-05", "availability": "In Stock"},
  {"item_name": "Cardstock", "qty_requested": 100, "current_stock": 50, "unit_price": 0.17, "total_price": 17.00, "estimated_delivery_date": "2025-04-06", "availability": "Low Stock"}
]

**Handle Ambiguity**: If a request is ambiguous or you cannot fulfill it, describe your capabilities and ask for clarification. Do not provide a quote if the request is ambiguous.
"""

@dataclass
class QuotingDependencies:
    db_engine: Engine
    customer_request: str
    items_name: str
    as_of_date: str
    quantity: int

class QuotingOutput(BaseModel):
    items_list: List[Dict] = Field(description="List of quoted items, each with item_name, quantity, availability, delivery_date, and final_quoted_price")
    discount_applied: float = Field(description="Loyalty discount applied as a decimal (e.g. 0.01 for 1%)")
    grand_total: float = Field(description="Grand total price across all quoted items")


def get_pricing_and_availability(ctx: RunContext[QuotingDependencies], item_name: str, quantity: int, as_of_date: str) -> str:
    """
    Tool for the quoting agent to get the base price, availability, and delivery date for a specific item and quantity.
    
    Args:
        item_name (str): The name of the item to quote.
        quantity (int): The number of units requested.
        as_of_date (str): The date for checking availability and pricing, in YYYY-MM-DD format.

    Returns:
        A string summarizing item's price, availability, and estimated delivery date, or an error message.
    
    """
    try:
            inventory_dataFrame = pd.read_sql("SELECT unit_price FROM inventory WHERE item_name = :item_name", db_engine, params={"item_name": item_name})
            
            if inventory_dataFrame.empty:
                return f"Item '{item_name}' not found in inventory."

            unit_price = inventory_dataFrame.iloc[0]["unit_price"]
            stock_level_df = get_stock_level(item_name, as_of_date)
            current_stock = stock_level_df.iloc[0]['current_stock']

            tot_price = unit_price * quantity

            delivery_date = get_supplier_delivery_date(as_of_date, quantity)

            return (f"Item: {item_name}, Price per unit: ${unit_price:.2f}, "
                    f"Total for {quantity} units: ${tot_price:.2f}. "
                    f"Current Availability: {current_stock} units. "
                    f"Estimated delivery date: {delivery_date}.")
    
    except Exception as e:
            return f"Error getting pricing and availability: {e}"

def quote_history(ctx: RunContext[QuotingDependencies], customer_request: str) -> str:
    """
    Tool for the quoting agent to search past quotes based on a customer's request to inform discount decisions.
    
    Args:
        customer_request (str): the customer's request to search in the quote history.
    
    Returns:
        A string summarizing the DataFrame containing past quotes, or a message if none are found.

    """

    _STOPWORDS = {
        "a", "an", "the", "of", "for", "and", "or", "to", "in", "on",
        "at", "by", "with", "that", "this", "is", "it", "we", "i",
        "need", "want", "please", "would", "like", "some", "our", "us",
        "have", "be", "can", "will", "from", "get", "do", "are", "not",
    }

    try:
        pattern = re.compile(r'(?:\d[\d,]*\s+(?:sheets? of|reams? of|packets? of|of|)?\s*)([a-zA-Z0-9\s\(\)\'\"-]+?)(?=\n|,|\s+and\s+|\.|$)', re.IGNORECASE)

        search_terms = [term.strip() for term in pattern.findall(customer_request)]

        if not search_terms:
            # Filter stopwords and short tokens to keep only meaningful keywords
            search_terms = [
                w for w in customer_request.split()
                if len(w) >= 4 and w.lower() not in _STOPWORDS
            ]

        # Cap terms to avoid overly large queries
        search_terms = search_terms[:10]

        quotes = search_quote_history(search_terms)

        if not quotes:
            return "No relevant quote history found for this request."
        return pd.DataFrame(quotes).to_string()
    except Exception as e:
        return f"Error searching quote history: {e}"

def apply_commission_and_discount(ctx: RunContext[QuotingDependencies], base_quote: str, discount: float) -> str:
    """Tool for the quoting agent to apply a sales commission and a variable loyalty discount to a single item's base quote."""
    try:
        # Extract unit price from the base quote string
        match = re.search(r"\$([\d\.]+)", base_quote)
        if not match:
            return "Error: Could not extract unit price from base quote."
        unit_price = float(match.group(1))

        # Apply a fixed sales commission of 5%
        commission_rate = 0.05
        price_with_commission = unit_price * (1 + commission_rate)

        # Apply the loyalty discount
        final_price = price_with_commission * (1 - discount)

        return f"Final quote after applying 5% commission and {discount*100:.2f}% loyalty discount: ${final_price:.2f}"
    except Exception as e:
        return f"Error applying commission and discount: {e}"

quoting_agent = Agent(
    model,
    #deps_type = QuotingDependencies,
    #output_type=str,
    tools=[            
        Tool(get_pricing_and_availability, takes_ctx=True),
        Tool(quote_history, takes_ctx=True),
        Tool(apply_commission_and_discount, takes_ctx=True),
    ],
    system_prompt=QUOTING_SYSTEM_PROMPT,
)

# Tools for business advisor agent
BUSINESS_ADVISOR_SYSTEM_PROMPT = """\
You are the Business Advisor Agent for Munder Difflin, a paper supply company.
Your role is to analyze inventory status and quotes, then decide the correct fulfillment action for each item in a customer request.

## Decision Rules (apply independently per item)

- **FINALIZE_ORDER**: Status is "Available" AND current_stock >= qty_requested. The item is in stock and can be shipped immediately.
- **REORDER_STOCK**: Status is "Insufficient" OR "N/A" (item not found or zero stock), AND the estimated supplier delivery date is ON OR BEFORE the customer deadline. We can restock in time.
- **CANNOT_FULFILL**: Status is "Insufficient" OR "N/A", AND the estimated supplier delivery date would MISS the customer deadline. We cannot fulfill in time.

## Critical Rules

- "N/A" status means the item is absent from current inventory. It is NEVER eligible for FINALIZE_ORDER.
- Always compare the estimated delivery date against the customer deadline when status is not "Available".
- Never invent data. Use only the inventory and quote information provided in the task.

## Output Format

After your analysis, output a JSON array with one object per item using EXACTLY these fields:
item_name, qty_requested, current_stock, unit_price, total_price, estimated_delivery_date, customer_deadline, status, action

Example:
business_analysis_details: [
  {"item_name": "Glossy Paper", "qty_requested": 200, "current_stock": 587, "unit_price": 0.21, "total_price": 42.00, "estimated_delivery_date": "2025-04-05", "customer_deadline": "2025-04-15", "status": "Available", "action": "FINALIZE_ORDER"},
  {"item_name": "Cardstock", "qty_requested": 100, "current_stock": 50, "unit_price": 0.16, "total_price": 16.00, "estimated_delivery_date": "2025-04-20", "customer_deadline": "2025-04-15", "status": "Insufficient", "action": "CANNOT_FULFILL"}
]
"""
@dataclass
class BusinessAdvisoryDependencies:
    db_engine: Engine
    customer_request: str

class BusinessAdvisoryOutput(BaseModel):
    strategic_advice: str = Field(description="Strategic advice based on financial reports and market trends to decide on the next step.")

business_advisor_agent = Agent(
    model,
    #deps_type = BusinessAdvisoryDependencies,
    #output_type=BusinessAdvisoryOutput,
    system_prompt=BUSINESS_ADVISOR_SYSTEM_PROMPT,
)

# Tools for sales agent

SALES_SYSTEM_PROMPT = """\
You are the Sales Agent for Munder Difflin, a paper supply company.
Your sole responsibility is to finalize confirmed customer orders by recording them as sales transactions.

## Available Tool
- `finalize_order(item_name, quantity, price, order_date)` — creates a sales transaction for one item

**Parameter clarification for `finalize_order`:**
- `item_name`: exact product name (case-sensitive)
- `quantity`: number of units ordered (integer)
- `price`: the **unit price per item** (not the total) — the tool calculates the total internally as `quantity * price`
- `order_date`: date in ISO format YYYY-MM-DD

**Note:** `finalize_order` verifies stock internally. If stock is insufficient it returns an error string — do not retry; report the failure to the caller.

## Workflow

For each item in the order:
1. Call `finalize_order(item_name, quantity, price, order_date)` using the exact values provided in the task.
   - Pass the **unit price** (price per single item) as the `price` argument, not the total price.
2. If the tool returns a confirmation with a transaction ID → the item is successfully recorded.
3. If the tool returns an error (e.g. insufficient stock) → report the failure clearly; do not retry.

If an order contains multiple items, call `finalize_order` once per item in separate calls.

## Output
Return a concise summary that includes for each item:
- Item name, quantity, unit price, and total price
- Transaction ID (on success) or reason for failure (on error)

## Handling Ambiguity
If `item_name`, `quantity`, `price`, or `order_date` are missing or ambiguous, do NOT call `finalize_order`. State clearly what is missing and ask for it.
"""

@dataclass
class SalesDependencies:
    db_engine: Engine
    customer_request: str
    items_name: str
    quantity: int
    price: float
    order_date: str

class SalesOutput(BaseModel):
    transaction_summary: List[Dict] = Field(description="List of finalized transactions, each with item_name, quantity, total_price, and transaction_id or error_message.")

#@sales_agent.tool
def finalize_order(ctx: RunContext[SalesDependencies], item_name: str, quantity: int, price: float, order_date: str) -> str:
    """Tool for the sales agent to create a sales transaction for a specific item, quantity, and price.
    
    Args:
        item_name (str): The name of the item being ordered.
        quantity (int): The number of units being ordered.
        price (float): The total price for the order.
        order_date (str): The date of the order in ISO format (YYYY-MM-DD).
    
    Returns:
        str: A confirmation message with the transaction ID if successful, or an error message if the order cannot be finalized.
    
    """
    
    resolved_name = find_matching_item_by_name(item_name) or item_name
    total_price = quantity * price

    try:
        transaction_id = create_transaction(
            item_name=resolved_name,
            transaction_type="sales",
            quantity=quantity,
            price=total_price,
            date=order_date,
        )
        unit_price = price
        return f"Sale finalized successfully! Transaction ID: {transaction_id}. Sold {quantity} units of {resolved_name} at ${unit_price:.2f} per unit. Total: ${total_price:.2f}"
    except Exception as e:
        return f"Error finalizing sale: {str(e)}"

sales_agent = Agent(
    model,
    #deps_type = SalesDependencies,
    #output_type=str,
    tools=[            
        Tool(finalize_order, takes_ctx=True),
    ],
    system_prompt=SALES_SYSTEM_PROMPT,
)

# Tool for orchestrator agent to call the other agents and manage the workflow
# Set up your agents and create an orchestration agent that will manage them.

ORCHESTATOR_SYSTEM_PROMPT = """\
You are the Customer Service Agent for Munder Difflin, a paper supply company.
Your sole responsibility is to handle customer inquiries and orders for paper products by routing them through the `handle_customer_request` tool.

## Available Tool
- `handle_customer_request(customer_request, as_of_date)` — processes any customer paper request end-to-end

**CRITICAL RULES:**
- For ANY customer input about paper products, you MUST call `handle_customer_request`. Do NOT answer directly.
- Do NOT advise customers to buy from other companies. You ARE the company.
- Do NOT act as a general assistant.

## Formatting the Final Response

After `handle_customer_request` returns, format the response to the customer following these rules:

1. **Include all relevant information** from the tool result that is useful to the customer.
2. **Explain decisions transparently** — if an item cannot be fulfilled or has a specific delivery date, briefly explain why (e.g., "out of stock", "delivery would miss your deadline").
3. **Protect sensitive information** — omit internal stock levels, financial details, supplier names, transaction IDs, and any PII not provided by the customer.

4. **Use this output template**, adapting the sections based on what was fulfilled:

---
Thank you for your request. Here is the status of your order:

**Confirmed items** (to be delivered by [DELIVERY_DATE]):
- [QUANTITY] [UNIT] of [ITEM_NAME] — $[TOTAL_PRICE]

**Items being restocked** (expected delivery by [RESTOCK_DATE]):
- [QUANTITY] [UNIT] of [ITEM_NAME] — we are placing a supply order to fulfill your request

**Items we cannot fulfill** (delivery deadline cannot be met):
- [ITEM_NAME] — [brief reason, e.g., "supplier delivery would arrive after your deadline of [DATE]"]

Omit any section that has no items. If all items are confirmed, only show the "Confirmed items" section.
---
"""

@dataclass
class OrchestratorDependencies:
    db_engine: Engine
    user_request: str
    as_of_date: str

class OrchestratorOutput(BaseModel):
    final_response: str = Field(description="A final summarized outcome to the customer after processing the request through the agents.")


@orchestrator.tool
async def handle_customer_request(ctx: RunContext[OrchestratorDependencies], customer_request: str, as_of_date: str) -> str:
    """ Handles a customer's end-to-end request for an order by orchestrating calls to the inventory, 
        quoting, and sales agents as needed. It gets a quote, checks stock, places a stock order if necessary, and finalizes the customer order.

        Args:
            user_request (str): The full text of the customer's request.
            as_of_date (str): The date for the request, in YYYY-MM-DD format.

        Returns:
            str: A final summarized outcome to the customer after processing the request through the agents.
    """

    print("DEBUG_handle_customer_request FUNC call\n\n")

    print("customer_request=", customer_request)
    print("\n\n")

    # Initialize all agent results to None so accesses never raise NameError
    inventory_result_message = None
    quote_result_message = None
    business_advisor_result = None
    sales_result_message = None

    #Step 1: normalize the request and extract the key item names.
    customer_request_lower = customer_request.lower()

    #Step2: Extract expected delivery deadline from the customer request (e.g. "by April 15, 2025" or "before 2025-04-15")
    customer_deadline = None
    deadline_match = re.search(
        r'(?:by|before|for|needed by|deliver(?:ed)? by)\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2})',
        customer_request, re.IGNORECASE
    )
    if deadline_match:
        raw_deadline = deadline_match.group(1).strip()
        for fmt in ("%B %d, %Y", "%B %d %Y", "%Y-%m-%d"):
            try:
                from datetime import datetime
                customer_deadline = datetime.strptime(raw_deadline, fmt).date()
                break
            except ValueError:
                continue
    print("customer_deadline=", customer_deadline)

    #Step4: determinate request type
    is_inquiry = any(keyword in customer_request_lower for keyword in ["what do you have", "check", "stock", "inventory", "is there", "availability", "in stock"])
    is_quote = any(keyword in customer_request_lower for keyword in ["quote", "price", "cost", "how much", "pricing"])
    is_purchase = any(keyword in customer_request_lower for keyword in ["place order", "accept", "i'll take", "proceed","yes", "go ahead", "buy", "purchase"])

    items_mentioned = []
    quantities_mentioned = []

    quantity_pattern = r'(\d+)\s*(?:sheets?|units?|reams?|rolls?|boxes?)'
    quantities = re.findall(quantity_pattern, customer_request_lower)
    if quantities:
        quantities_mentioned = [int(q) for q in quantities]
    
    print("is_inquiry", is_inquiry)
    print("is_quote", is_quote)
    print("is_purchase", is_purchase)

    #Step 5: extract exact item names and quantities from the customer request
    items_mentioned = []
    quantities_mentioned = []
    unresolved_items = []  # items extracted but not found in our catalog

    # Fix: unit group is optional but must own its leading space to avoid consuming
    # the separator space when no unit word is present (e.g. "200 balloons").
    # Also added \bfor\b as a lookahead terminator so "200 balloons for the parade"
    # stops at "balloons" and doesn't absorb the trailing phrase.
    pair_pattern = r'(\d[\d,]*)(?:\s+(?:sheets?|units?|reams?|rolls?|boxes?))?\s+(?:of\s+)?([a-zA-Z][a-zA-Z0-9\s\(\)\-]+?)(?=\s*(?:,|\band\b|\bfor\b|\.|$))'
    pairs = re.findall(pair_pattern, customer_request_lower, re.IGNORECASE | re.MULTILINE)

    for qty_str, item_candidate in pairs:
        clean_candidate = re.sub(r'\(.*?\)', '', item_candidate).strip()
        qty = int(qty_str.replace(',', ''))
        resolved = find_matching_item_by_name(clean_candidate)
        if resolved:
            items_mentioned.append(resolved)
            quantities_mentioned.append(qty)
        else:
            # Keep unresolved items so they can be reported as N/A to the customer
            unresolved_items.append({"item_name": clean_candidate, "qty_requested": qty})
            print(f"DEBUG_unresolved: '{clean_candidate}' not found in catalog — will mark N/A")

    #Step 6: check inventory for the extracted items

    if items_mentioned:
        print("DEBUG_inventory_agent_run FUNC call\n\n")

        items_quantities = ", ".join(f"{q} x {i}" for i, q in zip(items_mentioned, quantities_mentioned))
        inventory_result_message = await inventory_agent.run(
            f"TASK TYPE: INQUIRY. Do NOT run proactive stock maintenance. Do NOT call get_full_inventory_report.\n"
            f"Call check_stock_levels ONCE for each item below, then report using the required output format.\n"
            f"Date: {as_of_date}.\n"
            f"Items to check: {items_quantities}.\n"
            f"After the report, output a JSON array named 'inventory_details' with one object per item using exactly these fields: "
            f"item_name, qty_requested, current_stock, status.\n"
            f"Status rules: use 'Available' if current_stock >= qty_requested, 'Insufficient' if current_stock < qty_requested, 'N/A' if the item was not found in inventory.\n"
            f"Example JSON format:\n"
            f"inventory_details: [\n"
            f"  {{\"item_name\": \"Glossy Paper\", \"qty_requested\": 200, \"current_stock\": 587, \"status\": \"Available\"}},\n"
            f"  {{\"item_name\": \"Cardstock\", \"qty_requested\": 100, \"current_stock\": 50, \"status\": \"Insufficient\"}},\n"
            f"  {{\"item_name\": \"Unknown Item\", \"qty_requested\": 50, \"current_stock\": 0, \"status\": \"N/A\"}}\n"
            f"]"
        )

    #Step 7: check inventoru_details before quoting

    inventory_details = []
    if inventory_result_message is not None:
        print("inventory_result_message=", inventory_result_message.output)
        inventory_json_match = re.search(r'inventory_details\s*:\s*(\[.*?\])', inventory_result_message.output, re.DOTALL)
        if inventory_json_match:
            try:
                inventory_details = json.loads(inventory_json_match.group(1))
                print("inventory_details=", json.dumps(inventory_details, indent=2))
            except json.JSONDecodeError as e:
                print(f"Warning: could not parse inventory_details JSON: {e}")
        else:
            print("Warning: inventory_details JSON block not found in inventory agent output.")

    # Step 7a: Append unresolved items (not in our catalog) as N/A — no restock possible
    already_named = {i["item_name"].lower() for i in inventory_details}
    for u in unresolved_items:
        if u["item_name"].lower() not in already_named:
            inventory_details.append({
                "item_name": u["item_name"],
                "qty_requested": u["qty_requested"],
                "current_stock": 0,
                "status": "N/A",
            })
            print(f"DEBUG_na_item: added '{u['item_name']}' as N/A (not in catalog, cannot restock)")

    #Step 7b: For Insufficient items, attempt restock if delivery is before customer deadline

    insufficient_items = [i for i in inventory_details if i.get("status") == "Insufficient"]

    if insufficient_items and customer_deadline:
        print("DEBUG_restock_check: found insufficient items, checking delivery feasibility")
        restock_candidates = []

        for item in insufficient_items:
            item_name = item["item_name"]
            qty_needed = int(item["qty_requested"] * 1.1)
            estimated_delivery_str = get_supplier_delivery_date(as_of_date, qty_needed)
            estimated_delivery = datetime.fromisoformat(estimated_delivery_str).date()
            print(f"  {item_name}: delivery {estimated_delivery_str}, deadline {customer_deadline}")

            customer_delivery_date = estimated_delivery
            print(f"  {item_name}: restock arrives {estimated_delivery_str}, customer delivery {customer_delivery_date}, deadline {customer_deadline}")

            if customer_delivery_date <= customer_deadline:
                restock_candidates.append({
                    "item_name": item_name,
                    "qty_requested": qty_needed,
                    "estimated_delivery": estimated_delivery_str,
                    "customer_delivery_date": str(customer_delivery_date),
                })
            else:
                print(f"  {item_name}: customer delivery {customer_delivery_date} misses deadline — keeping Insufficient")

        if restock_candidates:
            # Check cash balance once before any restock
            cash_balance = get_cash_balance(as_of_date)
            print(f"DEBUG_restock_check: cash balance = ${cash_balance:.2f}")

            affordable_candidates = []
            for c in restock_candidates:
                price_df = pd.read_sql(
                    "SELECT unit_price FROM inventory WHERE item_name = :name",
                    db_engine, params={"name": c["item_name"]}
                )
                if price_df.empty:
                    print(f"  {c['item_name']}: unit price not found — keeping Insufficient")
                    continue
                unit_price = float(price_df.iloc[0]["unit_price"])
                order_cost = unit_price * c["qty_requested"]
                if cash_balance >= order_cost:
                    affordable_candidates.append({**c, "unit_price": unit_price, "order_cost": order_cost})
                    cash_balance -= order_cost  # deduct to account for subsequent items
                    print(f"  {c['item_name']}: cost=${order_cost:.2f} — affordable, added to restock")
                else:
                    print(f"  {c['item_name']}: cost=${order_cost:.2f} exceeds balance ${cash_balance:.2f} — keeping Insufficient")

            if affordable_candidates:
                restock_items_str = "\n".join(
                    f"- item_name: {c['item_name']}, quantity: {c['qty_requested']}, unit_price: {c['unit_price']:.4f}, order_date: {as_of_date}"
                    for c in affordable_candidates
                )
                print("DEBUG_restock_order: placing restock orders via inventory agent")
                await inventory_agent.run(
                    f"TASK TYPE: RESTOCK ORDER. Do NOT run proactive stock maintenance.\n"
                    f"Call place_stock_order once for each item below using the exact values provided.\n"
                    f"Date: {as_of_date}.\n{restock_items_str}"
                )
            restock_candidates = affordable_candidates

            # Re-check inventory for restocked items and update inventory_details
            for item in inventory_details:
                candidate = next((c for c in restock_candidates if c["item_name"] == item["item_name"]), None)
                if candidate:
                    updated_stock_df = get_stock_level(item["item_name"], as_of_date)
                    if not updated_stock_df.empty:
                        new_stock = int(updated_stock_df.iloc[0]["current_stock"])
                        item["current_stock"] = new_stock
                        item["status"] = "Available" if new_stock >= item["qty_requested"] else "Insufficient"
                        # Set the correct customer-facing delivery date: restock arrival + 1 day
                        item["estimated_delivery_date"] = candidate["customer_delivery_date"]
                        print(f"  Re-checked {item['item_name']}: new stock={new_stock}, status={item['status']}, customer delivery={candidate['customer_delivery_date']}")

        print("inventory_details after restock=", json.dumps(inventory_details, indent=2))

    #Step 8: get a quote from the quoting agent using exact DB item names

    print("DEBUG_quote_agent_run FUNC call\n\n")
    items_quantities = ", ".join(f"{q} x {i}" for i, q in zip(items_mentioned, quantities_mentioned))

    # Build delivery date overrides for items that were restocked in Step 7b
    restocked_delivery_overrides = {
        item["item_name"]: item["estimated_delivery_date"]
        for item in inventory_details
        if "estimated_delivery_date" in item
    }
    override_note = ""
    if restocked_delivery_overrides:
        override_lines = "\n".join(
            f"  - {name}: use {date} as estimated_delivery_date (stock arrives from supplier on this date)"
            for name, date in restocked_delivery_overrides.items()
        )
        override_note = (
            f"\nIMPORTANT — delivery date overrides for restocked items (do NOT call get_supplier_delivery_date for these; use the date provided):\n"
            f"{override_lines}\n"
        )

    quote_result_message = await quoting_agent.run(
        f"Provide a detailed quote as of {as_of_date} for these items: {items_quantities}. "
        f"Use the exact item names provided. "
        f"{override_note}"
        f"After the quote, output a JSON array named 'quote_details' with one object per item using exactly these fields: "
        f"item_name, qty_requested, current_stock, unit_price, total_price, estimated_delivery_date, status. "
        f"Retrieve current_stock from the get_pricing_and_availability tool output (labeled 'Current Availability'). "
        f"Example JSON format:\n"
        f"quote_details: [\n"
        f"  {{\"item_name\": \"Glossy Paper\", \"qty_requested\": 200, \"current_stock\": 587, \"unit_price\": 0.21, \"total_price\": 42.00, \"estimated_delivery_date\": \"2025-04-05\", \"status\": \"Available\"}},\n"
        f"  {{\"item_name\": \"Cardstock\", \"qty_requested\": 100, \"current_stock\": 50, \"unit_price\": 0.16, \"total_price\": 16.00, \"estimated_delivery_date\": \"2025-04-02\", \"status\": \"Insufficient\"}}\n"
        f"]"
    )


    #Step 9: Extract quote_details JSON from the quoting agent output
    quote_details = []
    quote_json_match = re.search(r'quote_details\s*:\s*(\[.*?\])', quote_result_message.output, re.DOTALL)
    if quote_json_match:
        try:
            quote_details = json.loads(quote_json_match.group(1))
            print("quote_details=", json.dumps(quote_details, indent=2))
        except json.JSONDecodeError as e:
            print(f"Warning: could not parse quote_details JSON: {e}")
    else:
        print("Warning: quote_details JSON block not found in quoting agent output.")

    #Step 10: use the business analysis agent to analyze the quote and decide the next action.
    print("DEBUG_ba_analysis_agent_run FUNC call\n\n")
    inventory_summary = json.dumps(inventory_details, indent=2) if inventory_details else "No inventory data available."
    business_analysis_agent_instructions = (
        f"Inventory status:\n{inventory_summary}\n\n"
        f"Quote:\n{quote_result_message.output}\n\n"
        f"Customer deadline: {customer_deadline}\n\n"
        f"Rules (apply per item):\n"
        f"- Status is 'Available' AND current_stock >= qty_requested → FINALIZE_ORDER\n"
        f"- Status is 'Insufficient' (low stock or zero stock), AND a supplier delivery date is on or before the customer deadline → REORDER_STOCK\n"
        f"- Status is 'N/A' (item not found) → CANNOT_FULFILL\n"
        f"IMPORTANT: 'N/A' status means the item is not in our current inventory. It is NEVER sufficient for FINALIZE_ORDER. Always apply the REORDER_STOCK or CANNOT_FULFILL rule.\n\n"
        f"After the analysis, output a JSON array named 'business_analysis_details' with one object per item using exactly these fields: "
        f"item_name, qty_requested, current_stock, unit_price, total_price, estimated_delivery_date, customer_deadline, status (Available, Insufficient, or N/A), action (FINALIZE_ORDER, REORDER_STOCK, or CANNOT_FULFILL).\n"
        f"Take current_stock from the inventory status provided above. If not available, use 0.\n"
        f"Example JSON format:\n"
        f"business_analysis_details: [\n"
        f"  {{\"item_name\": \"Glossy Paper\", \"qty_requested\": 200, \"current_stock\": 587, \"unit_price\": 0.21, \"total_price\": 42.00, \"estimated_delivery_date\": \"2025-04-05\", \"customer_deadline\": \"2025-04-15\", \"status\": \"Available\", \"action\": \"FINALIZE_ORDER\"}},\n"
        f"  {{\"item_name\": \"Cardstock\", \"qty_requested\": 100, \"current_stock\": 50, \"unit_price\": 0.16, \"total_price\": 16.00, \"estimated_delivery_date\": \"2025-04-02\", \"customer_deadline\": \"2025-04-15\", \"status\": \"Insufficient\", \"action\": \"REORDER_STOCK\"}}\n"
        f"]"
    )

    business_advisor_result = await business_advisor_agent.run(business_analysis_agent_instructions)
    ba_analysis_result = business_advisor_result.output
    print("ba_analysis_result=", ba_analysis_result)

    #Step 11: Route each item to the appropriate agent based on BA decision

    #Step 11a: Parse the JSON array from the BA agent's text output
    import re as _re
    _json_match = _re.search(r'\[.*?\]', ba_analysis_result, _re.DOTALL)
    if not _json_match:
        return "We apologize — we could not parse the business analysis. Please try again."
    try:
        business_analysis_details = json.loads(_json_match.group())
    except json.JSONDecodeError:
        return "We apologize — we could not parse the business analysis. Please try again."

    print("business_analysis_details=", business_analysis_details)

    finalize_items = [i for i in business_analysis_details if i.get("action") == "FINALIZE_ORDER"]
    reorder_items  = [i for i in business_analysis_details if i.get("action") == "REORDER_STOCK"]
    cannot_items   = [i for i in business_analysis_details if i.get("action") == "CANNOT_FULFILL"]

    print("DEBUG_finalize_items",finalize_items)
    print("DEBUG_reorder_items",reorder_items)
    print("DEBUG_cannot_items",cannot_items)

    #Step 11b: --- Sales agent: finalize confirmed orders ---
    if finalize_items:
        items_list = "\n".join(
            f"- item_name: {i['item_name']}, quantity: {i['qty_requested']}, "
            f"unit_price: {i['unit_price']}, total_price: {i['total_price']}, order_date: {as_of_date}"
            for i in finalize_items
        )
        sales_result_message = await sales_agent.run(
            f"Finalize the following confirmed orders as of {as_of_date}. "
            f"Call finalize_order once per item using the exact values below:\n{items_list}"
        )
        print("sales_result=", sales_result_message.output)

    #Step 11c: --- Inventory agent: place restock orders ---
    if reorder_items:
        items_list = "\n".join(
            f"- item_name: {i['item_name']}, quantity: {i['qty_requested']}, "
            f"unit_price: {i['unit_price']}, total_price: {i['total_price']}, order_date: {as_of_date}"
            for i in reorder_items
        )
        reorder_result_message = await inventory_agent.run(
            f"TASK TYPE: RESTOCK ORDER. Do NOT run proactive stock maintenance.\n"
            f"Call place_stock_order once for each item below using the exact values provided.\n"
            f"Date: {as_of_date}.\n{items_list}"
        )
        print("reorder_result=", reorder_result_message.output)

    #Step 12: --- Build final response ---
    response_parts = []
    if finalize_items:
        response_parts.append(sales_result_message.output)
    if reorder_items:
        response_parts.append(reorder_result_message.output)
    if cannot_items:
        names = ", ".join(i["item_name"] for i in cannot_items)
        response_parts.append(
            f"The following items cannot be fulfilled by the customer's deadline: {names}."
        )
    if not response_parts:
        return "No actionable items were found in your request."

    return "\n\n".join(response_parts)

# initiatize orchestrator agent

orchestrator = Agent(
    model,
    #deps_type=OrchestratorDependencies,
    output_type=str,
    tools=[            
        Tool(handle_customer_request, takes_ctx=True),
    ],
    system_prompt=ORCHESTATOR_SYSTEM_PROMPT,
)

# @orchestrator.tool
# def check_inventory(ctx: RunContext[OrchestratorDependencies], request: str) -> str:
#     """Delegate an inventory-related question to the inventory agent."""
#     result = inventory_agent.run_sync(request)
#     return result.output

# @orchestrator.tool
# def get_quote(ctx: RunContext[OrchestratorDependencies], request: str) -> str:
#     """Delegate a quoting request to the quoting agent."""
#     result = quoting_agent.run_sync(request)
#     return result.output

# @orchestrator.tool
# def place_order(ctx: RunContext[OrchestratorDependencies], request: str) -> str:
#     """Delegate an order placement request to the sales agent."""
#     result = sales_agent.run_sync(request)
#     return result.output


# def process_customer_request(customer_request: str, request_date: str) -> str:
#     """Process a customer request through the multi-agent orchestration system."""
#     prompt = f"Customer request: {customer_request}. Today's date: {request_date}."
#     result = orchestrator.run_sync(prompt)
#     return result.output
        
# Print Agent actions and reasoning in the console for better visibility during testing

# def print_agent_observability(agent_name: str, activity: str, status: str):
#     """
#     Utility function to print agent activities and reasoning in a structured format for better observability during testing.

#     Args:
#         agent_name (str): The name of the agent performing the activity.
#         activity (str): A description of the activity being performed.
#         status (str): The current status or result of the activity.
#     """
#     status_emojis = {
#         "elaborating": "🧠",
#         "completed": "✅",
#         "error": "❌",
#     }
#     emoji = status_emojis.get(status, "ℹ️")
    
#     sys.stdout.write(f"{emoji} [{agent_name}] {activity} - Status: {status}\n")
#     sys.stdout.flush()
#     time.sleep(0.4) # Simulate processing time for better readability

# def print_agent_completion(agent_name: str, response: str):
#     """Print agent message in a structured format to indicate completion of a task."""
#     print(f"✅ [{agent_name}] Completed task with response:\n{response}\n")

# Run your test scenarios by writing them here. Make sure to keep track of them.

def run_test_scenarios():
    
    print("Initializing Database...")
    init_database(db_engine)
    try:
        quote_requests_sample = pd.read_csv("quote_requests_sample.csv")
        quote_requests_sample["request_date"] = pd.to_datetime(
            quote_requests_sample["request_date"], format="%m/%d/%y", errors="coerce"
        )
        quote_requests_sample.dropna(subset=["request_date"], inplace=True)
        quote_requests_sample = quote_requests_sample.sort_values("request_date")
    except Exception as e:
        print(f"FATAL: Error loading test data: {e}")
        return

    # Get initial state
    initial_date = quote_requests_sample["request_date"].min().strftime("%Y-%m-%d")
    report = generate_financial_report(initial_date)
    current_cash = report["cash_balance"]
    current_inventory = report["inventory_value"]

    ############
    ############
    ############
    # INITIALIZE YOUR MULTI AGENT SYSTEM HERE
    ############
    ############
    ############

    print("starting Multi-Agent System Test Scenarios...")
    
    print("Multi-Agent System ready ...\n")

    results = []
    #for idx, row in quote_requests_sample.iterrows():
    for idx, row in quote_requests_sample.head(3).iterrows():
        request_date = row["request_date"].strftime("%Y-%m-%d")

        print(f"\n=== Request {idx+1} ===")
        print(f"Context: {row['job']} organizing {row['event']}")
        print(f"Request Date: {request_date}")
        print(f"Cash Balance: ${current_cash:.2f}")
        print(f"Inventory Value: ${current_inventory:.2f}")

        # Process request
        request_with_date = f"{row['request']} (Date of request: {request_date})"

        ############
        ############
        ############
        # USE YOUR MULTI AGENT SYSTEM TO HANDLE THE REQUEST
        ############
        ############
        ############

        # response = call_your_multi_agent_system(request_with_date)
        response = orchestrator.run_sync(request_with_date)

        current_cash = report["cash_balance"]
        current_inventory = report["inventory_value"]
        
        # Update state
        report = generate_financial_report(request_date)
        current_cash = report["cash_balance"]
        current_inventory = report["inventory_value"]

        print(f"Response: {response.output}")
        print(f"Updated Cash: ${current_cash:.2f}")
        print(f"Updated Inventory: ${current_inventory:.2f}")

        results.append(
            {
                "request_id": idx + 1,
                "request_date": request_date,
                "cash_balance": current_cash,
                "inventory_value": current_inventory,
                "response": response.output,
            }
        )

        time.sleep(1)

    # Final report
    final_date = quote_requests_sample["request_date"].max().strftime("%Y-%m-%d")
    final_report = generate_financial_report(final_date)
    print("\n===== FINAL FINANCIAL REPORT =====")
    print(f"Final Cash: ${final_report['cash_balance']:.2f}")
    print(f"Final Inventory: ${final_report['inventory_value']:.2f}")

    # Save results
    pd.DataFrame(results).to_csv("test_results.csv", index=False)
    return results


if __name__ == "__main__":
    results = run_test_scenarios()
