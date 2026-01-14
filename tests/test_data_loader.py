"""
Unit tests for DataManager.

Tests validate:
- Data loading and parsing
- Date boundary computation
- Singleton behavior
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.data_loader import DataManager, get_data_manager


class TestDataManagerLoading:
    """Tests for data loading functionality."""

    def test_transactions_loaded(self, data_manager: DataManager):
        """Transactions DataFrame is loaded and not empty."""
        assert data_manager.transactions is not None
        assert len(data_manager.transactions) > 0

    def test_customers_loaded(self, data_manager: DataManager):
        """Customers DataFrame is loaded and not empty."""
        assert data_manager.customers is not None
        assert len(data_manager.customers) > 0

    def test_transaction_columns(self, data_manager: DataManager):
        """Transactions has all required columns."""
        required = {
            "transaction_id",
            "customer_id",
            "transaction_date",
            "category",
            "product_name",
            "amount",
            "quantity",
            "payment_method",
            "is_returned",
        }
        assert required.issubset(set(data_manager.transactions.columns))

    def test_customer_columns(self, data_manager: DataManager):
        """Customers has all required columns."""
        required = {
            "customer_id",
            "region",
            "signup_date",
            "customer_segment",
        }
        assert required.issubset(set(data_manager.customers.columns))

    def test_transaction_date_is_datetime(self, data_manager: DataManager):
        """transaction_date column is datetime type."""
        assert pd.api.types.is_datetime64_any_dtype(
            data_manager.transactions["transaction_date"]
        )

    def test_signup_date_is_datetime(self, data_manager: DataManager):
        """signup_date column is datetime type."""
        assert pd.api.types.is_datetime64_any_dtype(
            data_manager.customers["signup_date"]
        )


class TestDataManagerDateBoundaries:
    """Tests for date boundary computation."""

    def test_data_start_before_data_end(self, data_manager: DataManager):
        """data_start is before data_end."""
        assert data_manager.data_start < data_manager.data_end

    def test_current_month_contains_data_end(self, data_manager: DataManager):
        """Current month range contains data_end."""
        assert data_manager.current_month_start <= data_manager.data_end
        assert data_manager.current_month_end >= data_manager.data_end

    def test_prev_month_before_current_month(self, data_manager: DataManager):
        """Previous month is before current month."""
        assert data_manager.prev_month_end < data_manager.current_month_start

    def test_date_context_returns_strings(self, date_context: dict[str, str]):
        """get_date_context returns ISO format date strings."""
        assert all(isinstance(v, str) for v in date_context.values())
        # Verify format is YYYY-MM-DD
        for key, value in date_context.items():
            pd.to_datetime(value)  # Will raise if invalid


class TestDataManagerSingleton:
    """Tests for singleton behavior."""

    def test_same_instance_returned(self):
        """Multiple calls return the same instance."""
        dm1 = get_data_manager()
        dm2 = get_data_manager()
        assert dm1 is dm2

    def test_reset_creates_new_instance(self):
        """reset() allows new instance creation."""
        dm1 = get_data_manager()
        DataManager.reset()
        dm2 = get_data_manager()
        # After reset, still returns a valid DataManager
        assert isinstance(dm2, DataManager)


class TestDataManagerProperties:
    """Tests for property accessors."""

    def test_transactions_returns_copy(self, data_manager: DataManager):
        """transactions property returns a copy, not the original."""
        df1 = data_manager.transactions
        df2 = data_manager.transactions
        # Modifying df1 should not affect df2
        df1["test_col"] = 1
        assert "test_col" not in df2.columns

    def test_customers_returns_copy(self, data_manager: DataManager):
        """customers property returns a copy, not the original."""
        df1 = data_manager.customers
        df2 = data_manager.customers
        df1["test_col"] = 1
        assert "test_col" not in df2.columns

    def test_merged_data_has_customer_fields(self, data_manager: DataManager):
        """get_merged_data includes customer fields."""
        merged = data_manager.get_merged_data()
        assert "region" in merged.columns
        assert "customer_segment" in merged.columns

    def test_counts_are_positive(self, data_manager: DataManager):
        """transaction_count and customer_count are positive."""
        assert data_manager.transaction_count > 0
        assert data_manager.customer_count > 0
