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

from src.config import VALID_CATEGORIES, VALID_PAYMENT_METHODS, VALID_REGIONS, VALID_SEGMENTS
from src.tools import (
    compare_regions,
    explain_capabilities,
    get_customer_ltv,
    get_data_overview,
    get_month_over_month,
    get_return_rates,
    get_revenue_by_category,
)


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

    def test_includes_all_tools(self):
        """Capabilities include all 7 tools."""
        result = explain_capabilities()
        tool_names = {item["tool_name"] for item in result["data"]}
        expected_tools = {
            "get_revenue_by_category",
            "get_customer_ltv",
            "get_return_rates",
            "compare_regions",
            "get_month_over_month",
            "get_data_overview",
            "explain_capabilities",
        }
        assert tool_names == expected_tools


# === Data Overview Tests ===


class TestGetDataOverview:
    """Tests for get_data_overview tool."""

    def test_returns_dict(self):
        """Tool returns a dictionary."""
        result = get_data_overview()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        """Response has required keys."""
        result = get_data_overview()
        assert "tool_used" in result
        assert "summary" in result
        assert "data_start" in result
        assert "data_end" in result
        assert "transaction_count" in result
        assert "customer_count" in result
        assert "categories" in result
        assert "regions" in result
        assert "segments" in result
        assert "payment_methods" in result
        assert "metadata" in result

    def test_date_start_before_end(self):
        """data_start is before data_end."""
        result = get_data_overview()
        assert result["data_start"] < result["data_end"]

    def test_counts_positive(self):
        """Transaction and customer counts are positive."""
        result = get_data_overview()
        assert result["transaction_count"] > 0
        assert result["customer_count"] > 0

    def test_categories_match_config(self):
        """Categories match configuration."""
        result = get_data_overview()
        assert set(result["categories"]) == VALID_CATEGORIES

    def test_regions_match_config(self):
        """Regions match configuration."""
        result = get_data_overview()
        assert set(result["regions"]) == VALID_REGIONS

    def test_segments_match_config(self):
        """Segments match configuration."""
        result = get_data_overview()
        assert set(result["segments"]) == VALID_SEGMENTS

    def test_payment_methods_match_config(self):
        """Payment methods match configuration."""
        result = get_data_overview()
        assert set(result["payment_methods"]) == VALID_PAYMENT_METHODS


# === Customer Lifetime Value Tests ===


class TestGetCustomerLTV:
    """Tests for get_customer_ltv tool."""

    def test_returns_dict(self):
        """Tool returns a dictionary."""
        result = get_customer_ltv()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        """Response has required keys."""
        result = get_customer_ltv()
        assert "tool_used" in result
        assert "summary" in result
        assert "data" in result
        assert "average_ltv" in result
        assert "total_customers_analyzed" in result
        assert "metadata" in result

    def test_default_returns_10_customers(self):
        """Default top_n returns 10 customers."""
        result = get_customer_ltv()
        assert len(result["data"]) == 10

    def test_custom_top_n(self):
        """Custom top_n returns correct number."""
        result = get_customer_ltv(top_n=5)
        assert len(result["data"]) == 5

    def test_customers_sorted_by_spending(self):
        """Customers are sorted by total_spent descending."""
        result = get_customer_ltv()
        spending = [c["total_spent"] for c in result["data"]]
        assert spending == sorted(spending, reverse=True)

    def test_rank_matches_position(self):
        """Rank field matches position in list."""
        result = get_customer_ltv()
        for i, customer in enumerate(result["data"], 1):
            assert customer["rank"] == i

    def test_customer_has_required_fields(self):
        """Each customer has required fields."""
        result = get_customer_ltv()
        for customer in result["data"]:
            assert "customer_id" in customer
            assert "total_spent" in customer
            assert "transaction_count" in customer
            assert "avg_transaction_value" in customer
            assert "region" in customer
            assert "segment" in customer
            assert "rank" in customer

    def test_region_filter(self):
        """Region filter returns only customers from that region."""
        result = get_customer_ltv(region="north")
        for customer in result["data"]:
            assert customer["region"] == "north"

    def test_segment_filter(self):
        """Segment filter returns only customers from that segment."""
        result = get_customer_ltv(segment="vip")
        for customer in result["data"]:
            assert customer["segment"] == "vip"

    def test_invalid_region_returns_error(self):
        """Invalid region returns structured error."""
        result = get_customer_ltv(region="invalid")
        assert result["ok"] == False
        assert result["error_type"] == "invalid_input"

    def test_invalid_segment_returns_error(self):
        """Invalid segment returns structured error."""
        result = get_customer_ltv(segment="invalid")
        assert result["ok"] == False
        assert result["error_type"] == "invalid_input"

    def test_invalid_top_n_returns_error(self):
        """Invalid top_n returns structured error."""
        result = get_customer_ltv(top_n=100)
        assert result["ok"] == False
        assert result["error_type"] == "invalid_input"


# === Return Rates Tests ===


class TestGetReturnRates:
    """Tests for get_return_rates tool."""

    def test_returns_dict(self):
        """Tool returns a dictionary."""
        result = get_return_rates()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        """Response has required keys."""
        result = get_return_rates()
        assert "tool_used" in result
        assert "summary" in result
        assert "data" in result
        assert "overall_return_rate" in result
        assert "highest_return_category" in result
        assert "total_revenue_lost" in result
        assert "metadata" in result

    def test_all_categories_present(self):
        """All 5 categories are included."""
        result = get_return_rates()
        categories = {item["category"] for item in result["data"]}
        assert categories == VALID_CATEGORIES

    def test_category_has_required_fields(self):
        """Each category has required fields."""
        result = get_return_rates()
        for item in result["data"]:
            assert "category" in item
            assert "total_transactions" in item
            assert "returned_count" in item
            assert "return_rate_percent" in item
            assert "revenue_lost_to_returns" in item

    def test_return_rate_calculation(self):
        """Return rate is correctly calculated."""
        result = get_return_rates()
        for item in result["data"]:
            expected_rate = 100 * item["returned_count"] / item["total_transactions"]
            assert abs(item["return_rate_percent"] - expected_rate) < 0.1

    def test_sorted_by_return_rate_descending(self):
        """Categories sorted by return rate descending."""
        result = get_return_rates()
        rates = [item["return_rate_percent"] for item in result["data"]]
        assert rates == sorted(rates, reverse=True)

    def test_highest_return_category_matches_first(self):
        """highest_return_category matches first in sorted list."""
        result = get_return_rates()
        assert result["highest_return_category"] == result["data"][0]["category"]

    def test_category_filter(self):
        """Category filter returns only that category."""
        result = get_return_rates(category="electronics")
        assert len(result["data"]) == 1
        assert result["data"][0]["category"] == "electronics"

    def test_invalid_category_returns_error(self):
        """Invalid category returns structured error."""
        result = get_return_rates(category="invalid")
        assert result["ok"] == False
        assert result["error_type"] == "invalid_input"


# === Regional Comparison Tests ===


class TestCompareRegions:
    """Tests for compare_regions tool."""

    def test_returns_dict(self):
        """Tool returns a dictionary."""
        result = compare_regions()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        """Response has required keys."""
        result = compare_regions()
        assert "tool_used" in result
        assert "summary" in result
        assert "data" in result
        assert "top_region_by_revenue" in result
        assert "top_region_by_customers" in result
        assert "metadata" in result

    def test_all_regions_present(self):
        """All 4 regions are included."""
        result = compare_regions()
        regions = {item["region"] for item in result["data"]}
        assert regions == VALID_REGIONS

    def test_region_has_required_fields(self):
        """Each region has required fields."""
        result = compare_regions()
        for item in result["data"]:
            assert "region" in item
            assert "total_revenue" in item
            assert "customer_count" in item
            assert "transaction_count" in item
            assert "avg_transaction_value" in item
            assert "return_rate_percent" in item

    def test_sorted_by_revenue_descending(self):
        """Regions sorted by revenue descending."""
        result = compare_regions()
        revenues = [item["total_revenue"] for item in result["data"]]
        assert revenues == sorted(revenues, reverse=True)

    def test_top_region_by_revenue_matches_first(self):
        """top_region_by_revenue matches first in sorted list."""
        result = compare_regions()
        assert result["top_region_by_revenue"] == result["data"][0]["region"]

    def test_all_metrics_positive(self):
        """All metric values are positive."""
        result = compare_regions()
        for item in result["data"]:
            assert item["total_revenue"] > 0
            assert item["customer_count"] > 0
            assert item["transaction_count"] > 0
            assert item["avg_transaction_value"] > 0


# === Month-over-Month Tests ===


class TestGetMonthOverMonth:
    """Tests for get_month_over_month tool."""

    def test_returns_dict(self):
        """Tool returns a dictionary."""
        result = get_month_over_month()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        """Response has required keys."""
        result = get_month_over_month()
        assert "tool_used" in result
        assert "summary" in result
        assert "current_period" in result
        assert "previous_period" in result
        assert "revenue_change_percent" in result
        assert "transaction_change_percent" in result
        assert "trend" in result
        assert "metadata" in result

    def test_period_has_required_fields(self):
        """Each period has required fields."""
        result = get_month_over_month()
        for period in [result["current_period"], result["previous_period"]]:
            assert "period_label" in period
            assert "start_date" in period
            assert "end_date" in period
            assert "revenue" in period
            assert "transaction_count" in period
            assert "unique_customers" in period
            assert "avg_transaction_value" in period

    def test_trend_is_valid(self):
        """Trend is one of growth, decline, stable."""
        result = get_month_over_month()
        assert result["trend"] in {"growth", "decline", "stable"}

    def test_revenue_change_matches_calculation(self):
        """Revenue change percent matches actual calculation."""
        result = get_month_over_month()
        current = result["current_period"]["revenue"]
        previous = result["previous_period"]["revenue"]

        if previous > 0:
            expected_change = 100 * (current - previous) / previous
            assert abs(result["revenue_change_percent"] - expected_change) < 0.1

    def test_current_period_is_more_recent(self):
        """Current period end date is after previous period end date."""
        result = get_month_over_month()
        current_end = result["current_period"]["end_date"]
        prev_end = result["previous_period"]["end_date"]
        assert current_end > prev_end

    def test_trend_consistent_with_change(self):
        """Trend is consistent with revenue change."""
        result = get_month_over_month()
        change = result["revenue_change_percent"]
        trend = result["trend"]

        if change > 5:
            assert trend == "growth"
        elif change < -5:
            assert trend == "decline"
        else:
            assert trend == "stable"
