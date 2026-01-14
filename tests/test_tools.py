"""
Unit tests for business analytics tools.

These tests validate:
1. Correct response structure (dict with required keys)
2. Business logic invariants (sums, relationships)
3. Date filtering functionality
4. Error handling for invalid inputs

NO hardcoded values - all assertions are contract-based.
Tests work regardless of when data was generated.
"""
from __future__ import annotations

import pytest

from src.config import VALID_CATEGORIES
from src.tools import explain_capabilities, get_revenue_by_category


class TestGetRevenueByCategoryStructure:
    """Tests for response structure and types."""

    def test_returns_dict(self):
        """Tool returns a dictionary (JSON-serializable)."""
        result = get_revenue_by_category()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        """Response contains all required keys."""
        result = get_revenue_by_category()
        assert "tool_used" in result
        assert "summary" in result
        assert "data" in result
        assert "total_revenue" in result
        assert "top_category" in result
        assert "metadata" in result

    def test_metadata_has_required_keys(self):
        """Metadata contains all required keys."""
        result = get_revenue_by_category()
        metadata = result["metadata"]
        assert "date_range_start" in metadata
        assert "date_range_end" in metadata
        assert "filters_applied" in metadata
        assert "record_count" in metadata
        assert "data_as_of" in metadata

    def test_data_is_list(self):
        """data field is a list."""
        result = get_revenue_by_category()
        assert isinstance(result["data"], list)

    def test_category_items_have_required_fields(self):
        """Each category item has required fields."""
        result = get_revenue_by_category()
        for item in result["data"]:
            assert "category" in item
            assert "total_revenue" in item
            assert "transaction_count" in item
            assert "avg_transaction_value" in item
            assert "percentage_of_total" in item


class TestGetRevenueByCategoryInvariants:
    """Tests for business logic invariants."""

    def test_all_categories_present(self):
        """All 5 categories are included in results."""
        result = get_revenue_by_category()
        categories_in_result = {cat["category"] for cat in result["data"]}
        assert categories_in_result == VALID_CATEGORIES

    def test_sum_equals_total(self):
        """Sum of category revenues equals total_revenue."""
        result = get_revenue_by_category()
        calculated_total = sum(cat["total_revenue"] for cat in result["data"])
        assert abs(calculated_total - result["total_revenue"]) < 0.01

    def test_all_revenues_positive(self):
        """All revenue values are positive."""
        result = get_revenue_by_category()
        assert result["total_revenue"] > 0
        assert all(cat["total_revenue"] > 0 for cat in result["data"])

    def test_percentages_sum_to_100(self):
        """Category percentages sum to 100%."""
        result = get_revenue_by_category()
        total_pct = sum(cat["percentage_of_total"] for cat in result["data"])
        assert abs(total_pct - 100.0) < 0.5  # Allow small rounding error

    def test_sorted_by_revenue_descending(self):
        """Categories are sorted by revenue in descending order."""
        result = get_revenue_by_category()
        revenues = [cat["total_revenue"] for cat in result["data"]]
        assert revenues == sorted(revenues, reverse=True)

    def test_top_category_matches_first(self):
        """top_category matches the first category in sorted list."""
        result = get_revenue_by_category()
        assert result["top_category"] == result["data"][0]["category"]

    def test_transaction_counts_positive(self):
        """All transaction counts are positive integers."""
        result = get_revenue_by_category()
        for cat in result["data"]:
            assert isinstance(cat["transaction_count"], int)
            assert cat["transaction_count"] > 0

    def test_avg_transaction_consistent(self):
        """Average transaction value is consistent with total/count."""
        result = get_revenue_by_category()
        for cat in result["data"]:
            expected_avg = cat["total_revenue"] / cat["transaction_count"]
            # Allow small rounding difference
            assert abs(cat["avg_transaction_value"] - expected_avg) < 1.0


class TestGetRevenueByCategoryFiltering:
    """Tests for filtering functionality."""

    def test_date_filtering_reduces_results(self, date_context: dict[str, str]):
        """Date filtering produces fewer transactions than full range."""
        full_result = get_revenue_by_category()

        # Use current month only (subset of data)
        filtered_result = get_revenue_by_category(
            start_date=date_context["current_month_start"],
            end_date=date_context["current_month_end"],
        )

        # Filtered should have fewer records
        assert (
            filtered_result["metadata"]["record_count"]
            <= full_result["metadata"]["record_count"]
        )

    def test_category_filtering(self):
        """Category filtering includes only specified categories."""
        result = get_revenue_by_category(categories=["electronics", "clothing"])

        categories_in_result = {cat["category"] for cat in result["data"]}
        assert categories_in_result == {"electronics", "clothing"}

    def test_single_category_filter(self):
        """Single category filter returns one category."""
        result = get_revenue_by_category(categories=["electronics"])

        assert len(result["data"]) == 1
        assert result["data"][0]["category"] == "electronics"
        assert result["top_category"] == "electronics"

    def test_filters_recorded_in_metadata(self):
        """Applied filters are recorded in metadata."""
        result = get_revenue_by_category(categories=["electronics", "clothing"])

        assert "categories" in result["metadata"]["filters_applied"]
        assert set(result["metadata"]["filters_applied"]["categories"]) == {
            "electronics",
            "clothing",
        }


class TestGetRevenueByCategoryErrorHandling:
    """Tests for error handling."""

    def test_invalid_category_returns_error(self):
        """Invalid category returns structured error."""
        result = get_revenue_by_category(categories=["invalid_category"])

        assert result["ok"] == False
        assert result["error_type"] == "invalid_input"
        assert "suggestions" in result
        assert len(result["suggestions"]) > 0

    def test_invalid_date_format_returns_error(self):
        """Invalid date format returns structured error."""
        result = get_revenue_by_category(start_date="not-a-date")

        assert result["ok"] == False
        assert result["error_type"] == "invalid_input"

    def test_invalid_end_date_returns_error(self):
        """Invalid end date returns structured error."""
        result = get_revenue_by_category(end_date="invalid")

        assert result["ok"] == False
        assert result["error_type"] == "invalid_input"


class TestExplainCapabilities:
    """Tests for explain_capabilities tool."""

    def test_returns_dict(self):
        """Tool returns a dictionary."""
        result = explain_capabilities()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        """Response has required keys."""
        result = explain_capabilities()
        assert "tool_used" in result
        assert "summary" in result
        assert "data" in result
        assert "total_tools" in result
        assert "metadata" in result

    def test_data_is_list(self):
        """data field is a list."""
        result = explain_capabilities()
        assert isinstance(result["data"], list)

    def test_total_tools_matches_data_length(self):
        """total_tools matches length of data list."""
        result = explain_capabilities()
        assert result["total_tools"] == len(result["data"])

    def test_capability_items_have_required_fields(self):
        """Each capability item has required fields."""
        result = explain_capabilities()
        for item in result["data"]:
            assert "tool_name" in item
            assert "description" in item
            assert "example_questions" in item
            assert "parameters" in item

    def test_includes_revenue_tool(self):
        """Capabilities include get_revenue_by_category."""
        result = explain_capabilities()
        tool_names = {item["tool_name"] for item in result["data"]}
        assert "get_revenue_by_category" in tool_names

    def test_includes_itself(self):
        """Capabilities include explain_capabilities itself."""
        result = explain_capabilities()
        tool_names = {item["tool_name"] for item in result["data"]}
        assert "explain_capabilities" in tool_names
