"""
Business analytics tools for the AI agent.

Each tool:
1. Uses @tool decorator from strands
2. Has comprehensive docstring for LLM understanding
3. Returns a Pydantic model (JSON-serializable)
4. Gets data from DataManager singleton (never reads CSVs)
5. Is deterministic and testable

CRITICAL: Tools NEVER use datetime.now() or read files directly.
All data access goes through DataManager.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
from strands import tool

from .config import VALID_CATEGORIES
from .data_loader import get_data_manager
from .models import (
    AgentCapabilities,
    CategoryRevenue,
    ErrorResponse,
    RevenueByCategory,
    ToolCapability,
    ToolMetadata,
)


@tool
def get_revenue_by_category(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    categories: Optional[list[str]] = None,
) -> dict:
    """
    Calculate total revenue broken down by product category.

    This tool analyzes e-commerce transaction data to show revenue performance
    across product categories. Returned items are excluded from revenue calculations.

    Args:
        start_date: Optional start date filter (YYYY-MM-DD format).
                   If not provided, uses all available data.
        end_date: Optional end date filter (YYYY-MM-DD format).
                 If not provided, uses all available data.
        categories: Optional list of categories to include.
                   Valid values: electronics, clothing, home, grocery, sports.
                   If not provided, includes all categories.

    Returns:
        dict: Structured response with:
            - data: List of category revenue breakdowns
            - total_revenue: Sum across all categories
            - top_category: Highest revenue category
            - summary: Human-readable interpretation
            - metadata: Date range and filters applied

    Example questions this tool answers:
        - "What is our total revenue by category?"
        - "How much revenue did electronics generate?"
        - "Show me revenue breakdown for Q4"
    """
    dm = get_data_manager()

    # Get transactions (excluding returns)
    df = dm.transactions
    df = df[df["is_returned"] == False].copy()

    # Apply date filters
    date_start_used = dm.data_start
    date_end_used = dm.data_end

    if start_date:
        try:
            start_dt = pd.to_datetime(start_date)
            df = df[df["transaction_date"] >= start_dt]
            date_start_used = start_dt
        except (ValueError, pd.errors.ParserError):
            return ErrorResponse(
                error_type="invalid_input",
                message=f"Invalid start_date format: {start_date}. Use YYYY-MM-DD.",
                suggestions=["Use format like '2024-01-01'"],
            ).model_dump()

    if end_date:
        try:
            end_dt = pd.to_datetime(end_date)
            df = df[df["transaction_date"] <= end_dt]
            date_end_used = end_dt
        except (ValueError, pd.errors.ParserError):
            return ErrorResponse(
                error_type="invalid_input",
                message=f"Invalid end_date format: {end_date}. Use YYYY-MM-DD.",
                suggestions=["Use format like '2024-12-31'"],
            ).model_dump()

    # Apply category filter
    filters_applied: dict = {}

    if categories:
        invalid = set(categories) - VALID_CATEGORIES
        if invalid:
            return ErrorResponse(
                error_type="invalid_input",
                message=f"Invalid categories: {invalid}",
                suggestions=[f"Valid categories are: {sorted(VALID_CATEGORIES)}"],
            ).model_dump()
        df = df[df["category"].isin(categories)]
        filters_applied["categories"] = list(categories)

    # Check for empty result
    if df.empty:
        return ErrorResponse(
            error_type="no_data",
            message="No transactions found matching the specified filters.",
            suggestions=[
                "Try a broader date range",
                "Check category spelling",
                "Use explain_capabilities to see valid options",
            ],
        ).model_dump()

    # Aggregate by category
    agg = (
        df.groupby("category")
        .agg(
            total_revenue=("amount", "sum"),
            transaction_count=("transaction_id", "count"),
            avg_transaction_value=("amount", "mean"),
        )
        .reset_index()
    )

    total_revenue = agg["total_revenue"].sum()

    # Build category list (sorted by revenue descending)
    category_data = []
    for _, row in agg.sort_values("total_revenue", ascending=False).iterrows():
        category_data.append(
            CategoryRevenue(
                category=row["category"],
                total_revenue=round(row["total_revenue"], 2),
                transaction_count=int(row["transaction_count"]),
                avg_transaction_value=round(row["avg_transaction_value"], 2),
                percentage_of_total=round(
                    100 * row["total_revenue"] / total_revenue, 1
                ),
            )
        )

    top_category = category_data[0].category if category_data else "N/A"

    # Build response
    response = RevenueByCategory(
        tool_used="get_revenue_by_category",
        summary=(
            f"Total revenue of ${total_revenue:,.2f} across {len(category_data)} categories. "
            f"{top_category.title()} is the top performer with "
            f"${category_data[0].total_revenue:,.2f} "
            f"({category_data[0].percentage_of_total}% of total)."
        ),
        data=category_data,
        total_revenue=round(total_revenue, 2),
        top_category=top_category,
        metadata=ToolMetadata(
            date_range_start=date_start_used.strftime("%Y-%m-%d"),
            date_range_end=date_end_used.strftime("%Y-%m-%d"),
            filters_applied=filters_applied,
            record_count=len(df),
            data_as_of=dm.data_end.strftime("%Y-%m-%d"),
        ),
    )

    return response.model_dump()


@tool
def explain_capabilities() -> dict:
    """
    List all available analytics tools and what questions they can answer.

    Use this tool when:
    - The user asks what the agent can do
    - A question cannot be answered by other tools
    - You need to suggest alternative analyses

    Returns:
        dict: Structured response with:
            - data: List of available tools with descriptions and examples
            - total_tools: Number of available tools
            - summary: Overview of agent capabilities
    """
    dm = get_data_manager()

    capabilities = [
        ToolCapability(
            tool_name="get_revenue_by_category",
            description="Calculate total revenue broken down by product category",
            example_questions=[
                "What is our total revenue by category?",
                "How much revenue did electronics generate?",
                "Show me revenue breakdown for Q4",
            ],
            parameters=["start_date", "end_date", "categories"],
        ),
        ToolCapability(
            tool_name="explain_capabilities",
            description="List all available analytics tools and example questions",
            example_questions=[
                "What can you help me with?",
                "What analyses are available?",
            ],
            parameters=[],
        ),
    ]

    response = AgentCapabilities(
        tool_used="explain_capabilities",
        summary=(
            f"I have {len(capabilities)} analytics tools available. "
            "I can analyze revenue by category with date and category filters. "
            "More tools will be added for customer LTV, return rates, "
            "regional comparisons, and month-over-month analysis."
        ),
        data=capabilities,
        total_tools=len(capabilities),
        metadata=ToolMetadata(
            date_range_start=dm.data_start.strftime("%Y-%m-%d"),
            date_range_end=dm.data_end.strftime("%Y-%m-%d"),
            filters_applied={},
            record_count=0,
            data_as_of=dm.data_end.strftime("%Y-%m-%d"),
        ),
    )

    return response.model_dump()
