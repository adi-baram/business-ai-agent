"""
Pydantic models for structured tool responses.

All tools return models that serialize to a consistent contract:
{
    "tool_used": str,       # Name of the tool that generated this
    "summary": str,         # Human-readable summary
    "data": list | dict,    # The structured data
    "metadata": dict        # Additional context (date range, filters applied)
}

Error responses follow:
{
    "ok": false,
    "error_type": str,      # Category of error
    "message": str,         # Human-readable description
    "suggestions": list     # What the user can do instead
}
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# === Base Response Models ===


class ToolMetadata(BaseModel):
    """Metadata included with every tool response."""

    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    filters_applied: dict = Field(default_factory=dict)
    record_count: int = 0
    data_as_of: str  # The data_end date from DataManager


class BaseToolResponse(BaseModel):
    """Base class for all successful tool responses."""

    tool_used: str
    summary: str
    metadata: ToolMetadata


class ErrorResponse(BaseModel):
    """Structured error response."""

    ok: bool = False
    error_type: str  # "invalid_input", "no_data", "computation_error"
    message: str
    suggestions: list[str] = Field(default_factory=list)


# === Revenue by Category ===


class CategoryRevenue(BaseModel):
    """Revenue metrics for a single category."""

    category: str
    total_revenue: float
    transaction_count: int
    avg_transaction_value: float
    percentage_of_total: float


class RevenueByCategory(BaseToolResponse):
    """Response for get_revenue_by_category tool."""

    data: list[CategoryRevenue]
    total_revenue: float
    top_category: str


# === Customer Lifetime Value ===


class CustomerLTV(BaseModel):
    """LTV metrics for a single customer."""

    customer_id: str
    total_spent: float
    transaction_count: int
    avg_transaction_value: float
    region: str
    segment: str
    rank: int


class CustomerLifetimeValue(BaseToolResponse):
    """Response for get_customer_ltv tool."""

    data: list[CustomerLTV]
    average_ltv: float
    total_customers_analyzed: int


# === Return Rates ===


class CategoryReturnRate(BaseModel):
    """Return rate metrics for a single category."""

    category: str
    total_transactions: int
    returned_count: int
    return_rate_percent: float
    revenue_lost_to_returns: float


class ReturnRateByCategory(BaseToolResponse):
    """Response for get_return_rates tool."""

    data: list[CategoryReturnRate]
    overall_return_rate: float
    highest_return_category: str
    total_revenue_lost: float


# === Regional Comparison ===


class RegionMetrics(BaseModel):
    """Performance metrics for a single region."""

    region: str
    total_revenue: float
    customer_count: int
    transaction_count: int
    avg_transaction_value: float
    return_rate_percent: float


class RegionalComparison(BaseToolResponse):
    """Response for compare_regions tool."""

    data: list[RegionMetrics]
    top_region_by_revenue: str
    top_region_by_customers: str


# === Month-over-Month Performance ===


class PeriodMetrics(BaseModel):
    """Metrics for a single time period."""

    period_label: str
    start_date: str
    end_date: str
    revenue: float
    transaction_count: int
    unique_customers: int
    avg_transaction_value: float


class MonthOverMonth(BaseToolResponse):
    """Response for get_month_over_month tool."""

    current_period: PeriodMetrics
    previous_period: PeriodMetrics
    revenue_change_percent: float
    transaction_change_percent: float
    trend: str  # "growth", "decline", "stable"


# === Data Overview ===


class DataOverview(BaseToolResponse):
    """Response for get_data_overview tool."""

    data_start: str
    data_end: str
    transaction_count: int
    customer_count: int
    categories: list[str]
    regions: list[str]
    segments: list[str]
    payment_methods: list[str]


# === Agent Capabilities ===


class ToolCapability(BaseModel):
    """Description of a single tool capability."""

    tool_name: str
    description: str
    example_questions: list[str]
    parameters: list[str]


class AgentCapabilities(BaseToolResponse):
    """Response for explain_capabilities tool."""

    data: list[ToolCapability]
    total_tools: int


# === Payment Method Analysis ===


class PaymentMethodMetrics(BaseModel):
    """Metrics for a single payment method."""

    payment_method: str
    total_revenue: float
    transaction_count: int
    avg_transaction_value: float
    percentage_of_transactions: float
    return_rate_percent: float


class PaymentMethodAnalysis(BaseToolResponse):
    """Response for get_payment_method_analysis tool."""

    data: list[PaymentMethodMetrics]
    total_revenue: float
    most_popular_method: str
    highest_avg_value_method: str


# === Segment Comparison ===


class SegmentMetrics(BaseModel):
    """Performance metrics for a customer segment."""

    segment: str
    total_revenue: float
    customer_count: int
    transaction_count: int
    avg_transaction_value: float
    avg_transactions_per_customer: float
    return_rate_percent: float
    percentage_of_revenue: float


class SegmentComparison(BaseToolResponse):
    """Response for get_segment_comparison tool."""

    data: list[SegmentMetrics]
    top_segment_by_revenue: str
    top_segment_by_avg_value: str
    total_customers: int


# === Revenue Trends ===


class MonthlyRevenue(BaseModel):
    """Revenue metrics for a single month."""

    month: str  # YYYY-MM format
    revenue: float
    transaction_count: int
    unique_customers: int
    avg_transaction_value: float


class RevenueTrends(BaseToolResponse):
    """Response for get_revenue_trends tool."""

    data: list[MonthlyRevenue]
    total_revenue: float
    best_month: str
    worst_month: str
    avg_monthly_revenue: float
    overall_trend: str  # "growing", "declining", "stable"
