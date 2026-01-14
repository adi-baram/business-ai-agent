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
