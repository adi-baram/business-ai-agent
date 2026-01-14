"""
Data access layer for business analytics agent.

Provides a singleton DataManager that loads CSVs once and provides:
- Cached pandas DataFrames
- Dataset-anchored date context (no datetime.now() usage)
- Merged transaction/customer views

CRITICAL: All time-based logic is anchored to the dataset's max transaction_date,
NOT the system clock. This ensures reproducible results regardless of when the code runs.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from .config import get_settings


class DataManager:
    """
    Singleton class for data access.

    All time-based logic is anchored to the dataset's max transaction_date,
    NOT the system clock. This ensures reproducible results regardless of
    when the code runs.
    """

    _instance: Optional[DataManager] = None

    def __new__(cls, data_dir: Optional[str] = None) -> DataManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, data_dir: Optional[str] = None) -> None:
        if self._initialized:
            return

        if data_dir is None:
            data_dir = get_settings().data_dir

        self._data_dir = Path(data_dir)
        self._load_data()
        self._compute_date_boundaries()
        self._initialized = True

    def _load_data(self) -> None:
        """Load CSVs and convert date columns."""
        # Load transactions
        txn_path = self._data_dir / "transactions.csv"
        if not txn_path.exists():
            raise FileNotFoundError(
                f"transactions.csv not found at {txn_path}. "
                "Run 'python generate_data.py' first."
            )

        self._transactions = pd.read_csv(txn_path)
        self._transactions["transaction_date"] = pd.to_datetime(
            self._transactions["transaction_date"]
        )

        # Load customers
        cust_path = self._data_dir / "customers.csv"
        if not cust_path.exists():
            raise FileNotFoundError(
                f"customers.csv not found at {cust_path}. "
                "Run 'python generate_data.py' first."
            )

        self._customers = pd.read_csv(cust_path)
        self._customers["signup_date"] = pd.to_datetime(
            self._customers["signup_date"]
        )

        # Validate required columns exist
        required_txn_cols = {
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
        required_cust_cols = {
            "customer_id",
            "region",
            "signup_date",
            "customer_segment",
        }

        missing_txn = required_txn_cols - set(self._transactions.columns)
        if missing_txn:
            raise ValueError(f"Missing transaction columns: {missing_txn}")

        missing_cust = required_cust_cols - set(self._customers.columns)
        if missing_cust:
            raise ValueError(f"Missing customer columns: {missing_cust}")

    def _compute_date_boundaries(self) -> None:
        """
        Compute date context from the dataset itself.

        CRITICAL: All time logic is anchored to data_end (max transaction date),
        NOT datetime.now(). This ensures:
        - Reproducible results across different run times
        - Tests don't break when dataset ages
        - "This month" always means the month of the most recent transaction
        """
        self.data_start: pd.Timestamp = self._transactions["transaction_date"].min()
        self.data_end: pd.Timestamp = self._transactions["transaction_date"].max()

        # "Current month" = month containing data_end
        self.current_month_start: pd.Timestamp = self.data_end.replace(day=1)
        self.current_month_end: pd.Timestamp = self.data_end

        # "Previous month" = month before current month
        prev_month_last_day = self.current_month_start - timedelta(days=1)
        self.prev_month_start: pd.Timestamp = prev_month_last_day.replace(day=1)
        self.prev_month_end: pd.Timestamp = prev_month_last_day

    @property
    def transactions(self) -> pd.DataFrame:
        """Get transactions DataFrame (read-only copy)."""
        return self._transactions.copy()

    @property
    def customers(self) -> pd.DataFrame:
        """Get customers DataFrame (read-only copy)."""
        return self._customers.copy()

    def get_merged_data(self) -> pd.DataFrame:
        """Get transactions joined with customer data."""
        return self._transactions.merge(self._customers, on="customer_id", how="left")

    def get_date_context(self) -> dict[str, str]:
        """
        Return dataset date boundaries for tools.

        Returns:
            dict with keys: data_start, data_end, current_month_start,
            current_month_end, prev_month_start, prev_month_end
            All values are ISO format date strings.
        """
        return {
            "data_start": self.data_start.strftime("%Y-%m-%d"),
            "data_end": self.data_end.strftime("%Y-%m-%d"),
            "current_month_start": self.current_month_start.strftime("%Y-%m-%d"),
            "current_month_end": self.current_month_end.strftime("%Y-%m-%d"),
            "prev_month_start": self.prev_month_start.strftime("%Y-%m-%d"),
            "prev_month_end": self.prev_month_end.strftime("%Y-%m-%d"),
        }

    @property
    def transaction_count(self) -> int:
        """Total number of transactions."""
        return len(self._transactions)

    @property
    def customer_count(self) -> int:
        """Total number of customers."""
        return len(self._customers)

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None


def get_data_manager(data_dir: Optional[str] = None) -> DataManager:
    """Get or create the DataManager singleton."""
    return DataManager(data_dir)
