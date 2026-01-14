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

from .config import (
    VALID_CATEGORIES,
    VALID_PAYMENT_METHODS,
    VALID_REGIONS,
    VALID_SEGMENTS,
)
from .data_loader import get_data_manager
from .models import (
    AgentCapabilities,
    CategoryReturnRate,
    CategoryRevenue,
    CustomerLifetimeValue,
    CustomerLTV,
    DataOverview,
    ErrorResponse,
    MonthlyRevenue,
    MonthOverMonth,
    PaymentMethodAnalysis,
    PaymentMethodMetrics,
    PeriodMetrics,
    RegionalComparison,
    RegionMetrics,
    ReturnRateByCategory,
    RevenueByCategory,
    RevenueTrends,
    SegmentComparison,
    SegmentMetrics,
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
def get_customer_ltv(
    top_n: int = 10,
    region: Optional[str] = None,
    segment: Optional[str] = None,
) -> dict:
    """
    Get top customers ranked by lifetime value (total spending).

    This tool identifies the most valuable customers based on their total
    transaction amount. Useful for loyalty programs, targeted marketing,
    and customer segmentation analysis.

    Args:
        top_n: Number of top customers to return (default: 10, max: 50).
        region: Optional filter by customer region.
               Valid values: north, south, east, west.
        segment: Optional filter by customer segment.
                Valid values: new, regular, vip.

    Returns:
        dict: Structured response with:
            - data: List of top customers with LTV metrics
            - average_ltv: Average lifetime value across analyzed customers
            - total_customers_analyzed: Number of customers in the analysis
            - summary: Human-readable interpretation

    Example questions this tool answers:
        - "Which customers have the highest lifetime value?"
        - "Who are our top 5 VIP customers?"
        - "Show me the best customers in the north region"
    """
    dm = get_data_manager()

    # Validate inputs
    if top_n < 1 or top_n > 50:
        return ErrorResponse(
            error_type="invalid_input",
            message=f"top_n must be between 1 and 50, got {top_n}",
            suggestions=["Use a value like 10 or 20"],
        ).model_dump()

    if region and region not in VALID_REGIONS:
        return ErrorResponse(
            error_type="invalid_input",
            message=f"Invalid region: {region}",
            suggestions=[f"Valid regions are: {sorted(VALID_REGIONS)}"],
        ).model_dump()

    if segment and segment not in VALID_SEGMENTS:
        return ErrorResponse(
            error_type="invalid_input",
            message=f"Invalid segment: {segment}",
            suggestions=[f"Valid segments are: {sorted(VALID_SEGMENTS)}"],
        ).model_dump()

    # Get merged data (transactions + customers)
    df = dm.get_merged_data()

    # Exclude returns from LTV calculation
    df = df[df["is_returned"] == False].copy()

    # Apply filters
    filters_applied: dict = {}
    if region:
        df = df[df["region"] == region]
        filters_applied["region"] = region
    if segment:
        df = df[df["customer_segment"] == segment]
        filters_applied["segment"] = segment

    if df.empty:
        return ErrorResponse(
            error_type="no_data",
            message="No customers found matching the specified filters.",
            suggestions=["Try removing filters", "Check region/segment spelling"],
        ).model_dump()

    # Aggregate by customer
    customer_agg = (
        df.groupby(["customer_id", "region", "customer_segment"])
        .agg(
            total_spent=("amount", "sum"),
            transaction_count=("transaction_id", "count"),
        )
        .reset_index()
    )

    customer_agg["avg_transaction_value"] = (
        customer_agg["total_spent"] / customer_agg["transaction_count"]
    )

    # Sort and rank
    customer_agg = customer_agg.sort_values("total_spent", ascending=False)
    customer_agg["rank"] = range(1, len(customer_agg) + 1)

    # Get top N
    top_customers = customer_agg.head(top_n)

    # Build response data
    customer_data = []
    for _, row in top_customers.iterrows():
        customer_data.append(
            CustomerLTV(
                customer_id=row["customer_id"],
                total_spent=round(row["total_spent"], 2),
                transaction_count=int(row["transaction_count"]),
                avg_transaction_value=round(row["avg_transaction_value"], 2),
                region=row["region"],
                segment=row["customer_segment"],
                rank=int(row["rank"]),
            )
        )

    average_ltv = customer_agg["total_spent"].mean()
    total_customers = len(customer_agg)

    response = CustomerLifetimeValue(
        tool_used="get_customer_ltv",
        summary=(
            f"Top {len(customer_data)} customers by lifetime value. "
            f"#1 is {customer_data[0].customer_id} with ${customer_data[0].total_spent:,.2f} "
            f"from {customer_data[0].transaction_count} transactions. "
            f"Average LTV across {total_customers} customers is ${average_ltv:,.2f}."
        ),
        data=customer_data,
        average_ltv=round(average_ltv, 2),
        total_customers_analyzed=total_customers,
        metadata=ToolMetadata(
            date_range_start=dm.data_start.strftime("%Y-%m-%d"),
            date_range_end=dm.data_end.strftime("%Y-%m-%d"),
            filters_applied=filters_applied,
            record_count=len(top_customers),
            data_as_of=dm.data_end.strftime("%Y-%m-%d"),
        ),
    )

    return response.model_dump()


@tool
def get_return_rates(
    category: Optional[str] = None,
) -> dict:
    """
    Calculate return rates by product category.

    This tool analyzes the percentage of transactions that were returned
    for each product category, helping identify quality or satisfaction issues.

    Args:
        category: Optional filter to analyze a specific category.
                 Valid values: electronics, clothing, home, grocery, sports.
                 If not provided, shows all categories.

    Returns:
        dict: Structured response with:
            - data: List of categories with return rate metrics
            - overall_return_rate: Return rate across all transactions
            - highest_return_category: Category with highest return rate
            - total_revenue_lost: Total revenue lost to returns
            - summary: Human-readable interpretation

    Example questions this tool answers:
        - "What's the return rate by product category?"
        - "Which category has the most returns?"
        - "How much revenue are we losing to returns?"
    """
    dm = get_data_manager()

    # Validate input
    if category and category not in VALID_CATEGORIES:
        return ErrorResponse(
            error_type="invalid_input",
            message=f"Invalid category: {category}",
            suggestions=[f"Valid categories are: {sorted(VALID_CATEGORIES)}"],
        ).model_dump()

    df = dm.transactions

    # Apply category filter
    filters_applied: dict = {}
    if category:
        df = df[df["category"] == category]
        filters_applied["category"] = category

    if df.empty:
        return ErrorResponse(
            error_type="no_data",
            message="No transactions found.",
            suggestions=["Check category spelling"],
        ).model_dump()

    # Calculate return rates by category
    category_stats = (
        df.groupby("category")
        .agg(
            total_transactions=("transaction_id", "count"),
            returned_count=("is_returned", "sum"),
            total_amount=("amount", "sum"),
        )
        .reset_index()
    )

    # Calculate returned revenue per category
    returned_revenue = (
        df[df["is_returned"] == True]
        .groupby("category")["amount"]
        .sum()
        .reset_index()
    )
    returned_revenue.columns = ["category", "revenue_lost"]

    category_stats = category_stats.merge(returned_revenue, on="category", how="left")
    category_stats["revenue_lost"] = category_stats["revenue_lost"].fillna(0)

    category_stats["return_rate_percent"] = (
        100 * category_stats["returned_count"] / category_stats["total_transactions"]
    )

    # Sort by return rate descending
    category_stats = category_stats.sort_values("return_rate_percent", ascending=False)

    # Build response data
    category_data = []
    for _, row in category_stats.iterrows():
        category_data.append(
            CategoryReturnRate(
                category=row["category"],
                total_transactions=int(row["total_transactions"]),
                returned_count=int(row["returned_count"]),
                return_rate_percent=round(row["return_rate_percent"], 1),
                revenue_lost_to_returns=round(row["revenue_lost"], 2),
            )
        )

    # Overall metrics
    total_txn = df["transaction_id"].count()
    total_returned = df["is_returned"].sum()
    overall_return_rate = 100 * total_returned / total_txn if total_txn > 0 else 0
    total_revenue_lost = df[df["is_returned"] == True]["amount"].sum()

    highest_return_category = category_data[0].category if category_data else "N/A"

    response = ReturnRateByCategory(
        tool_used="get_return_rates",
        summary=(
            f"Overall return rate is {overall_return_rate:.1f}%. "
            f"{highest_return_category.title()} has the highest return rate "
            f"at {category_data[0].return_rate_percent}%. "
            f"Total revenue lost to returns: ${total_revenue_lost:,.2f}."
        ),
        data=category_data,
        overall_return_rate=round(overall_return_rate, 1),
        highest_return_category=highest_return_category,
        total_revenue_lost=round(total_revenue_lost, 2),
        metadata=ToolMetadata(
            date_range_start=dm.data_start.strftime("%Y-%m-%d"),
            date_range_end=dm.data_end.strftime("%Y-%m-%d"),
            filters_applied=filters_applied,
            record_count=int(total_txn),
            data_as_of=dm.data_end.strftime("%Y-%m-%d"),
        ),
    )

    return response.model_dump()


@tool
def compare_regions() -> dict:
    """
    Compare business performance across geographic regions.

    This tool provides a comprehensive comparison of all regions,
    including revenue, customer count, transaction volume, and return rates.
    Useful for resource allocation and regional strategy decisions.

    Returns:
        dict: Structured response with:
            - data: List of regions with performance metrics
            - top_region_by_revenue: Best performing region by revenue
            - top_region_by_customers: Region with most customers
            - summary: Human-readable interpretation

    Example questions this tool answers:
        - "Compare performance across regions"
        - "Which region generates the most revenue?"
        - "How do our regions compare?"
    """
    dm = get_data_manager()

    # Get merged data
    df = dm.get_merged_data()

    # Calculate metrics by region
    region_stats = (
        df.groupby("region")
        .agg(
            total_revenue=("amount", lambda x: x[df.loc[x.index, "is_returned"] == False].sum()),
            transaction_count=("transaction_id", "count"),
            customer_count=("customer_id", "nunique"),
            returned_count=("is_returned", "sum"),
        )
        .reset_index()
    )

    # Calculate non-returned revenue properly
    non_returned = df[df["is_returned"] == False].groupby("region")["amount"].sum().reset_index()
    non_returned.columns = ["region", "total_revenue"]

    region_stats = region_stats.drop(columns=["total_revenue"]).merge(non_returned, on="region")

    region_stats["avg_transaction_value"] = (
        region_stats["total_revenue"] / (region_stats["transaction_count"] - region_stats["returned_count"])
    )
    region_stats["return_rate_percent"] = (
        100 * region_stats["returned_count"] / region_stats["transaction_count"]
    )

    # Sort by revenue descending
    region_stats = region_stats.sort_values("total_revenue", ascending=False)

    # Build response data
    region_data = []
    for _, row in region_stats.iterrows():
        region_data.append(
            RegionMetrics(
                region=row["region"],
                total_revenue=round(row["total_revenue"], 2),
                customer_count=int(row["customer_count"]),
                transaction_count=int(row["transaction_count"]),
                avg_transaction_value=round(row["avg_transaction_value"], 2),
                return_rate_percent=round(row["return_rate_percent"], 1),
            )
        )

    top_by_revenue = region_data[0].region if region_data else "N/A"
    top_by_customers = max(region_data, key=lambda x: x.customer_count).region if region_data else "N/A"

    response = RegionalComparison(
        tool_used="compare_regions",
        summary=(
            f"{top_by_revenue.title()} leads in revenue with ${region_data[0].total_revenue:,.2f}. "
            f"{top_by_customers.title()} has the most customers ({max(r.customer_count for r in region_data)}). "
            f"Lowest return rate: {min(r.region for r in region_data)} "
            f"({min(r.return_rate_percent for r in region_data)}%)."
        ),
        data=region_data,
        top_region_by_revenue=top_by_revenue,
        top_region_by_customers=top_by_customers,
        metadata=ToolMetadata(
            date_range_start=dm.data_start.strftime("%Y-%m-%d"),
            date_range_end=dm.data_end.strftime("%Y-%m-%d"),
            filters_applied={},
            record_count=len(df),
            data_as_of=dm.data_end.strftime("%Y-%m-%d"),
        ),
    )

    return response.model_dump()


@tool
def get_month_over_month() -> dict:
    """
    Compare current month performance to the previous month.

    This tool analyzes revenue, transaction count, and customer metrics
    for the current month versus the previous month. Time periods are
    anchored to the dataset's end date, not the system clock.

    Returns:
        dict: Structured response with:
            - current_period: Metrics for current month
            - previous_period: Metrics for previous month
            - revenue_change_percent: Percentage change in revenue
            - transaction_change_percent: Percentage change in transactions
            - trend: "growth", "decline", or "stable"
            - summary: Human-readable interpretation

    Example questions this tool answers:
        - "How is this month performing compared to last month?"
        - "Are we growing or declining?"
        - "Month over month comparison"
    """
    dm = get_data_manager()

    df = dm.transactions

    # Exclude returns from revenue calculations
    df_valid = df[df["is_returned"] == False].copy()

    # Current month (based on dataset end date, not system time)
    current_mask = (df_valid["transaction_date"] >= dm.current_month_start) & (
        df_valid["transaction_date"] <= dm.current_month_end
    )
    current_df = df_valid[current_mask]

    # Previous month
    prev_mask = (df_valid["transaction_date"] >= dm.prev_month_start) & (
        df_valid["transaction_date"] <= dm.prev_month_end
    )
    prev_df = df_valid[prev_mask]

    # Calculate metrics for current period
    current_revenue = current_df["amount"].sum() if not current_df.empty else 0
    current_txn_count = len(current_df)
    current_customers = current_df["customer_id"].nunique() if not current_df.empty else 0
    current_avg = current_revenue / current_txn_count if current_txn_count > 0 else 0

    # Calculate metrics for previous period
    prev_revenue = prev_df["amount"].sum() if not prev_df.empty else 0
    prev_txn_count = len(prev_df)
    prev_customers = prev_df["customer_id"].nunique() if not prev_df.empty else 0
    prev_avg = prev_revenue / prev_txn_count if prev_txn_count > 0 else 0

    # Calculate changes
    if prev_revenue > 0:
        revenue_change = 100 * (current_revenue - prev_revenue) / prev_revenue
    else:
        revenue_change = 100.0 if current_revenue > 0 else 0.0

    if prev_txn_count > 0:
        txn_change = 100 * (current_txn_count - prev_txn_count) / prev_txn_count
    else:
        txn_change = 100.0 if current_txn_count > 0 else 0.0

    # Determine trend
    if revenue_change > 5:
        trend = "growth"
    elif revenue_change < -5:
        trend = "decline"
    else:
        trend = "stable"

    current_period = PeriodMetrics(
        period_label="current_month",
        start_date=dm.current_month_start.strftime("%Y-%m-%d"),
        end_date=dm.current_month_end.strftime("%Y-%m-%d"),
        revenue=round(current_revenue, 2),
        transaction_count=current_txn_count,
        unique_customers=current_customers,
        avg_transaction_value=round(current_avg, 2),
    )

    previous_period = PeriodMetrics(
        period_label="previous_month",
        start_date=dm.prev_month_start.strftime("%Y-%m-%d"),
        end_date=dm.prev_month_end.strftime("%Y-%m-%d"),
        revenue=round(prev_revenue, 2),
        transaction_count=prev_txn_count,
        unique_customers=prev_customers,
        avg_transaction_value=round(prev_avg, 2),
    )

    # Build summary
    trend_word = "up" if revenue_change > 0 else "down" if revenue_change < 0 else "flat"

    response = MonthOverMonth(
        tool_used="get_month_over_month",
        summary=(
            f"Revenue is {trend_word} {abs(revenue_change):.1f}% month-over-month. "
            f"Current month: ${current_revenue:,.2f} ({current_txn_count} transactions). "
            f"Previous month: ${prev_revenue:,.2f} ({prev_txn_count} transactions). "
            f"Trend: {trend}."
        ),
        current_period=current_period,
        previous_period=previous_period,
        revenue_change_percent=round(revenue_change, 1),
        transaction_change_percent=round(txn_change, 1),
        trend=trend,
        metadata=ToolMetadata(
            date_range_start=dm.prev_month_start.strftime("%Y-%m-%d"),
            date_range_end=dm.current_month_end.strftime("%Y-%m-%d"),
            filters_applied={},
            record_count=current_txn_count + prev_txn_count,
            data_as_of=dm.data_end.strftime("%Y-%m-%d"),
        ),
    )

    return response.model_dump()


@tool
def get_data_overview() -> dict:
    """
    Get basic information about the dataset.

    This tool provides an overview of the available data, including
    date range, record counts, and available dimensions for filtering.

    Returns:
        dict: Structured response with:
            - data_start: Earliest transaction date
            - data_end: Most recent transaction date
            - transaction_count: Total number of transactions
            - customer_count: Total number of customers
            - categories: Available product categories
            - regions: Available geographic regions
            - segments: Available customer segments
            - payment_methods: Available payment methods

    Example questions this tool answers:
        - "What is the date range of the data?"
        - "How many transactions are in the dataset?"
        - "What is the most recent transaction date?"
        - "What categories are available?"
    """
    dm = get_data_manager()

    response = DataOverview(
        tool_used="get_data_overview",
        summary=(
            f"Dataset contains {dm.transaction_count:,} transactions from "
            f"{dm.customer_count:,} customers, spanning "
            f"{dm.data_start.strftime('%Y-%m-%d')} to {dm.data_end.strftime('%Y-%m-%d')}."
        ),
        data_start=dm.data_start.strftime("%Y-%m-%d"),
        data_end=dm.data_end.strftime("%Y-%m-%d"),
        transaction_count=dm.transaction_count,
        customer_count=dm.customer_count,
        categories=sorted(VALID_CATEGORIES),
        regions=sorted(VALID_REGIONS),
        segments=sorted(VALID_SEGMENTS),
        payment_methods=sorted(VALID_PAYMENT_METHODS),
        metadata=ToolMetadata(
            date_range_start=dm.data_start.strftime("%Y-%m-%d"),
            date_range_end=dm.data_end.strftime("%Y-%m-%d"),
            filters_applied={},
            record_count=dm.transaction_count,
            data_as_of=dm.data_end.strftime("%Y-%m-%d"),
        ),
    )

    return response.model_dump()


@tool
def get_payment_method_analysis(
    category: Optional[str] = None,
    region: Optional[str] = None,
) -> dict:
    """
    Analyze transaction patterns by payment method.

    This tool breaks down revenue, transaction count, and average values
    by payment method (credit card, debit card, PayPal, Apple Pay).
    Useful for understanding customer payment preferences and optimizing
    payment processing.

    Args:
        category: Optional filter by product category.
                 Valid values: electronics, clothing, home, grocery, sports.
        region: Optional filter by customer region.
               Valid values: north, south, east, west.

    Returns:
        dict: Structured response with:
            - data: List of payment methods with metrics
            - total_revenue: Total revenue across all payment methods
            - most_popular_method: Payment method with most transactions
            - highest_avg_value_method: Payment method with highest average order
            - summary: Human-readable interpretation

    Example questions this tool answers:
        - "What payment methods do customers prefer?"
        - "Which payment method has the highest average order value?"
        - "What's the return rate by payment method?"
        - "How does credit card compare to PayPal?"
    """
    dm = get_data_manager()

    # Validate inputs
    if category and category not in VALID_CATEGORIES:
        return ErrorResponse(
            error_type="invalid_input",
            message=f"Invalid category: {category}",
            suggestions=[f"Valid categories are: {sorted(VALID_CATEGORIES)}"],
        ).model_dump()

    if region and region not in VALID_REGIONS:
        return ErrorResponse(
            error_type="invalid_input",
            message=f"Invalid region: {region}",
            suggestions=[f"Valid regions are: {sorted(VALID_REGIONS)}"],
        ).model_dump()

    # Get data
    df = dm.get_merged_data()

    # Apply filters
    filters_applied: dict = {}
    if category:
        df = df[df["category"] == category]
        filters_applied["category"] = category
    if region:
        df = df[df["region"] == region]
        filters_applied["region"] = region

    if df.empty:
        return ErrorResponse(
            error_type="no_data",
            message="No transactions found matching the specified filters.",
            suggestions=["Try removing filters"],
        ).model_dump()

    # Calculate metrics by payment method
    # For revenue, exclude returns
    df_valid = df[df["is_returned"] == False]

    payment_stats = (
        df.groupby("payment_method")
        .agg(
            transaction_count=("transaction_id", "count"),
            returned_count=("is_returned", "sum"),
        )
        .reset_index()
    )

    # Revenue from non-returned transactions
    revenue_by_method = (
        df_valid.groupby("payment_method")["amount"]
        .agg(["sum", "mean"])
        .reset_index()
    )
    revenue_by_method.columns = ["payment_method", "total_revenue", "avg_transaction_value"]

    payment_stats = payment_stats.merge(revenue_by_method, on="payment_method", how="left")
    payment_stats["total_revenue"] = payment_stats["total_revenue"].fillna(0)
    payment_stats["avg_transaction_value"] = payment_stats["avg_transaction_value"].fillna(0)

    # Calculate percentages and return rates
    total_transactions = payment_stats["transaction_count"].sum()
    total_revenue = payment_stats["total_revenue"].sum()

    payment_stats["percentage_of_transactions"] = (
        100 * payment_stats["transaction_count"] / total_transactions
    )
    payment_stats["return_rate_percent"] = (
        100 * payment_stats["returned_count"] / payment_stats["transaction_count"]
    )

    # Sort by transaction count (most popular first)
    payment_stats = payment_stats.sort_values("transaction_count", ascending=False)

    # Build response data
    payment_data = []
    for _, row in payment_stats.iterrows():
        payment_data.append(
            PaymentMethodMetrics(
                payment_method=row["payment_method"],
                total_revenue=round(row["total_revenue"], 2),
                transaction_count=int(row["transaction_count"]),
                avg_transaction_value=round(row["avg_transaction_value"], 2),
                percentage_of_transactions=round(row["percentage_of_transactions"], 1),
                return_rate_percent=round(row["return_rate_percent"], 1),
            )
        )

    most_popular = payment_data[0].payment_method if payment_data else "N/A"
    highest_avg = max(payment_data, key=lambda x: x.avg_transaction_value).payment_method if payment_data else "N/A"

    response = PaymentMethodAnalysis(
        tool_used="get_payment_method_analysis",
        summary=(
            f"Most popular payment method is {most_popular.replace('_', ' ')} "
            f"with {payment_data[0].percentage_of_transactions}% of transactions. "
            f"Highest average order value: {highest_avg.replace('_', ' ')} "
            f"(${max(p.avg_transaction_value for p in payment_data):,.2f}). "
            f"Total revenue: ${total_revenue:,.2f}."
        ),
        data=payment_data,
        total_revenue=round(total_revenue, 2),
        most_popular_method=most_popular,
        highest_avg_value_method=highest_avg,
        metadata=ToolMetadata(
            date_range_start=dm.data_start.strftime("%Y-%m-%d"),
            date_range_end=dm.data_end.strftime("%Y-%m-%d"),
            filters_applied=filters_applied,
            record_count=int(total_transactions),
            data_as_of=dm.data_end.strftime("%Y-%m-%d"),
        ),
    )

    return response.model_dump()


@tool
def get_segment_comparison(
    region: Optional[str] = None,
) -> dict:
    """
    Compare performance across customer segments (new, regular, VIP).

    This tool analyzes how different customer segments perform in terms
    of revenue, transaction frequency, and return rates. Useful for
    customer strategy and loyalty program decisions.

    Args:
        region: Optional filter by customer region.
               Valid values: north, south, east, west.

    Returns:
        dict: Structured response with:
            - data: List of segments with performance metrics
            - top_segment_by_revenue: Segment generating most revenue
            - top_segment_by_avg_value: Segment with highest average transaction
            - total_customers: Total customers analyzed
            - summary: Human-readable interpretation

    Example questions this tool answers:
        - "How do VIP customers compare to regular customers?"
        - "Which customer segment spends the most?"
        - "What's the return rate by customer segment?"
        - "Are new customers performing well?"
    """
    dm = get_data_manager()

    # Validate input
    if region and region not in VALID_REGIONS:
        return ErrorResponse(
            error_type="invalid_input",
            message=f"Invalid region: {region}",
            suggestions=[f"Valid regions are: {sorted(VALID_REGIONS)}"],
        ).model_dump()

    # Get merged data
    df = dm.get_merged_data()

    # Apply filters
    filters_applied: dict = {}
    if region:
        df = df[df["region"] == region]
        filters_applied["region"] = region

    if df.empty:
        return ErrorResponse(
            error_type="no_data",
            message="No data found matching the specified filters.",
            suggestions=["Try removing filters"],
        ).model_dump()

    # Calculate metrics by segment
    df_valid = df[df["is_returned"] == False]

    segment_stats = (
        df.groupby("customer_segment")
        .agg(
            transaction_count=("transaction_id", "count"),
            customer_count=("customer_id", "nunique"),
            returned_count=("is_returned", "sum"),
        )
        .reset_index()
    )

    # Revenue from non-returned transactions
    revenue_by_segment = (
        df_valid.groupby("customer_segment")["amount"]
        .agg(["sum", "mean"])
        .reset_index()
    )
    revenue_by_segment.columns = ["customer_segment", "total_revenue", "avg_transaction_value"]

    segment_stats = segment_stats.merge(revenue_by_segment, on="customer_segment", how="left")
    segment_stats["total_revenue"] = segment_stats["total_revenue"].fillna(0)
    segment_stats["avg_transaction_value"] = segment_stats["avg_transaction_value"].fillna(0)

    # Calculate derived metrics
    total_revenue = segment_stats["total_revenue"].sum()
    total_customers = segment_stats["customer_count"].sum()

    segment_stats["avg_transactions_per_customer"] = (
        segment_stats["transaction_count"] / segment_stats["customer_count"]
    )
    segment_stats["return_rate_percent"] = (
        100 * segment_stats["returned_count"] / segment_stats["transaction_count"]
    )
    segment_stats["percentage_of_revenue"] = (
        100 * segment_stats["total_revenue"] / total_revenue
    )

    # Sort by revenue descending
    segment_stats = segment_stats.sort_values("total_revenue", ascending=False)

    # Build response data
    segment_data = []
    for _, row in segment_stats.iterrows():
        segment_data.append(
            SegmentMetrics(
                segment=row["customer_segment"],
                total_revenue=round(row["total_revenue"], 2),
                customer_count=int(row["customer_count"]),
                transaction_count=int(row["transaction_count"]),
                avg_transaction_value=round(row["avg_transaction_value"], 2),
                avg_transactions_per_customer=round(row["avg_transactions_per_customer"], 1),
                return_rate_percent=round(row["return_rate_percent"], 1),
                percentage_of_revenue=round(row["percentage_of_revenue"], 1),
            )
        )

    top_by_revenue = segment_data[0].segment if segment_data else "N/A"
    top_by_avg = max(segment_data, key=lambda x: x.avg_transaction_value).segment if segment_data else "N/A"

    response = SegmentComparison(
        tool_used="get_segment_comparison",
        summary=(
            f"{top_by_revenue.upper()} customers lead in total revenue with "
            f"${segment_data[0].total_revenue:,.2f} ({segment_data[0].percentage_of_revenue}% of total). "
            f"{top_by_avg.upper()} segment has highest average transaction "
            f"(${max(s.avg_transaction_value for s in segment_data):,.2f}). "
            f"Total customers: {total_customers}."
        ),
        data=segment_data,
        top_segment_by_revenue=top_by_revenue,
        top_segment_by_avg_value=top_by_avg,
        total_customers=int(total_customers),
        metadata=ToolMetadata(
            date_range_start=dm.data_start.strftime("%Y-%m-%d"),
            date_range_end=dm.data_end.strftime("%Y-%m-%d"),
            filters_applied=filters_applied,
            record_count=len(df),
            data_as_of=dm.data_end.strftime("%Y-%m-%d"),
        ),
    )

    return response.model_dump()


@tool
def get_revenue_trends(
    category: Optional[str] = None,
) -> dict:
    """
    Show monthly revenue trends over the dataset period.

    This tool provides a time-series view of revenue, helping identify
    seasonal patterns, growth trends, and performance anomalies.
    Data is aggregated by calendar month.

    Args:
        category: Optional filter by product category.
                 Valid values: electronics, clothing, home, grocery, sports.

    Returns:
        dict: Structured response with:
            - data: List of monthly metrics (chronological order)
            - total_revenue: Sum of all months
            - best_month: Highest revenue month
            - worst_month: Lowest revenue month
            - avg_monthly_revenue: Average monthly revenue
            - overall_trend: "growing", "declining", or "stable"
            - summary: Human-readable interpretation

    Example questions this tool answers:
        - "What's our revenue trend over time?"
        - "Which month had the highest sales?"
        - "Show me monthly revenue for the year"
        - "Are we growing or declining overall?"
    """
    dm = get_data_manager()

    # Validate input
    if category and category not in VALID_CATEGORIES:
        return ErrorResponse(
            error_type="invalid_input",
            message=f"Invalid category: {category}",
            suggestions=[f"Valid categories are: {sorted(VALID_CATEGORIES)}"],
        ).model_dump()

    # Get transactions (exclude returns for revenue)
    df = dm.transactions
    df = df[df["is_returned"] == False].copy()

    # Apply category filter
    filters_applied: dict = {}
    if category:
        df = df[df["category"] == category]
        filters_applied["category"] = category

    if df.empty:
        return ErrorResponse(
            error_type="no_data",
            message="No transactions found matching the specified filters.",
            suggestions=["Try removing filters"],
        ).model_dump()

    # Add month column for grouping
    df["month"] = df["transaction_date"].dt.to_period("M")

    # Aggregate by month
    monthly_stats = (
        df.groupby("month")
        .agg(
            revenue=("amount", "sum"),
            transaction_count=("transaction_id", "count"),
            unique_customers=("customer_id", "nunique"),
        )
        .reset_index()
    )

    monthly_stats["avg_transaction_value"] = (
        monthly_stats["revenue"] / monthly_stats["transaction_count"]
    )

    # Sort chronologically
    monthly_stats = monthly_stats.sort_values("month")

    # Build response data
    monthly_data = []
    for _, row in monthly_stats.iterrows():
        monthly_data.append(
            MonthlyRevenue(
                month=str(row["month"]),
                revenue=round(row["revenue"], 2),
                transaction_count=int(row["transaction_count"]),
                unique_customers=int(row["unique_customers"]),
                avg_transaction_value=round(row["avg_transaction_value"], 2),
            )
        )

    # Calculate summary metrics
    total_revenue = sum(m.revenue for m in monthly_data)
    avg_monthly = total_revenue / len(monthly_data) if monthly_data else 0

    best_month = max(monthly_data, key=lambda x: x.revenue).month if monthly_data else "N/A"
    worst_month = min(monthly_data, key=lambda x: x.revenue).month if monthly_data else "N/A"

    # Determine overall trend (compare first half to second half)
    if len(monthly_data) >= 4:
        mid = len(monthly_data) // 2
        first_half_avg = sum(m.revenue for m in monthly_data[:mid]) / mid
        second_half_avg = sum(m.revenue for m in monthly_data[mid:]) / (len(monthly_data) - mid)

        change_percent = 100 * (second_half_avg - first_half_avg) / first_half_avg if first_half_avg > 0 else 0

        if change_percent > 10:
            trend = "growing"
        elif change_percent < -10:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "stable"  # Not enough data to determine trend

    response = RevenueTrends(
        tool_used="get_revenue_trends",
        summary=(
            f"Revenue trend over {len(monthly_data)} months. "
            f"Total: ${total_revenue:,.2f}, Average: ${avg_monthly:,.2f}/month. "
            f"Best month: {best_month} (${max(m.revenue for m in monthly_data):,.2f}). "
            f"Overall trend: {trend}."
        ),
        data=monthly_data,
        total_revenue=round(total_revenue, 2),
        best_month=best_month,
        worst_month=worst_month,
        avg_monthly_revenue=round(avg_monthly, 2),
        overall_trend=trend,
        metadata=ToolMetadata(
            date_range_start=dm.data_start.strftime("%Y-%m-%d"),
            date_range_end=dm.data_end.strftime("%Y-%m-%d"),
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
            tool_name="get_customer_ltv",
            description="Get top customers ranked by lifetime value (total spending)",
            example_questions=[
                "Which customers have the highest lifetime value?",
                "Who are our top 5 VIP customers?",
                "Show me the best customers in the north region",
            ],
            parameters=["top_n", "region", "segment"],
        ),
        ToolCapability(
            tool_name="get_return_rates",
            description="Calculate return rates by product category",
            example_questions=[
                "What's the return rate by product category?",
                "Which category has the most returns?",
                "How much revenue are we losing to returns?",
            ],
            parameters=["category"],
        ),
        ToolCapability(
            tool_name="compare_regions",
            description="Compare business performance across geographic regions",
            example_questions=[
                "Compare performance across regions",
                "Which region generates the most revenue?",
                "How do our regions compare?",
            ],
            parameters=[],
        ),
        ToolCapability(
            tool_name="get_month_over_month",
            description="Compare current month performance to previous month",
            example_questions=[
                "How is this month performing compared to last month?",
                "Are we growing or declining?",
                "Month over month comparison",
            ],
            parameters=[],
        ),
        ToolCapability(
            tool_name="get_data_overview",
            description="Get basic dataset information: date range, record counts, available dimensions",
            example_questions=[
                "What is the date range of the data?",
                "How many transactions are there?",
                "What is the most recent transaction date?",
                "What categories are available?",
            ],
            parameters=[],
        ),
        ToolCapability(
            tool_name="get_payment_method_analysis",
            description="Analyze transaction patterns by payment method",
            example_questions=[
                "What payment methods do customers prefer?",
                "Which payment method has the highest average order value?",
                "What's the return rate by payment method?",
            ],
            parameters=["category", "region"],
        ),
        ToolCapability(
            tool_name="get_segment_comparison",
            description="Compare performance across customer segments (new, regular, VIP)",
            example_questions=[
                "How do VIP customers compare to regular customers?",
                "Which customer segment spends the most?",
                "What's the return rate by customer segment?",
            ],
            parameters=["region"],
        ),
        ToolCapability(
            tool_name="get_revenue_trends",
            description="Show monthly revenue trends over the dataset period",
            example_questions=[
                "What's our revenue trend over time?",
                "Which month had the highest sales?",
                "Are we growing or declining overall?",
            ],
            parameters=["category"],
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
            f"I have {len(capabilities)} analytics tools available: "
            "revenue by category, customer lifetime value, return rates, "
            "regional comparison, month-over-month analysis, payment method analysis, "
            "customer segment comparison, and revenue trends."
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
