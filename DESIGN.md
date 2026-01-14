# Design Decisions and Trade-offs

This document explains the architectural decisions made in this project and the trade-offs involved.

---

## 1. Layered Architecture

```
Agent Layer (agent.py)      → Orchestration: model config, tool registration, system prompt
        ↓
Tools Layer (tools.py)      → Business logic: calculations, aggregations, validation
        ↓
Data Layer (data_loader.py) → Data access: CSV loading, date boundaries, caching
```

**Why this design:**
- Strict separation of concerns enables independent testing
- Tools can be unit-tested without an LLM or API key
- The agent layer has zero business logic - only configuration
- Easy to swap the LLM provider without changing business logic

**Trade-off:** More files to navigate, but each file has a single responsibility.

---

## 2. Dataset-Anchored Time

All time references ("this month", "last month") are relative to `max(transaction_date)` in the dataset, **not** the system clock.

```python
# In data_loader.py
self.data_end = self._transactions["transaction_date"].max()
self.current_month_start = self.data_end.replace(day=1)
```

**Why this design:**
- Reproducible results regardless of when the code runs
- Tests don't break as data ages
- Demo produces consistent output every time
- No dependency on system time

**Trade-off:** Not suitable for real-time dashboards, but perfect for analytical queries on historical data.

---

## 3. Structured Response Contract

Every tool returns a consistent structure:

```python
{
    "tool_used": str,       # Which tool generated this
    "summary": str,         # Human-readable interpretation
    "data": list | dict,    # Structured data for further analysis
    "metadata": {
        "date_range_start": str,
        "date_range_end": str,
        "filters_applied": dict,
        "record_count": int,
        "data_as_of": str
    }
}
```

**Why this design:**
- Consistent structure helps the LLM format responses reliably
- The `summary` field provides ready-to-use text for the user
- The `data` field enables follow-up analysis or programmatic access
- Metadata provides context about what was queried

**Trade-off:** More verbose than minimal responses, but self-documenting and debuggable.

---

## 4. Structured Error Responses

Invalid inputs return a structured error (not exceptions):

```python
{
    "ok": false,
    "error_type": "invalid_input",  # or "no_data", "computation_error"
    "message": "Invalid category: xyz",
    "suggestions": ["Valid categories are: clothing, electronics, ..."]
}
```

**Why this design:**
- The LLM can understand what went wrong
- The LLM can suggest corrections to the user
- No silent failures or hallucinated responses
- Consistent handling across all error cases

**Trade-off:** Requires explicit error handling in every tool, but prevents unpredictable behavior.

---

## 5. Comprehensive Docstrings for Tool Selection

Each tool has detailed docstrings:

```python
@tool
def get_revenue_by_category(...) -> dict:
    """
    Calculate total revenue broken down by product category.

    This tool analyzes e-commerce transaction data to show revenue
    performance across product categories. Returned items are excluded.

    Args:
        start_date: Optional start date filter (YYYY-MM-DD format).
        ...

    Example questions this tool answers:
        - "What is our total revenue by category?"
        - "How much revenue did electronics generate?"
    """
```

**Why this design:**
- The LLM selects tools based on docstrings
- Clear examples improve selection accuracy
- Parameter documentation helps the LLM construct correct calls

**Trade-off:** Verbose code, but this is the LLM's "instruction manual" for using tools correctly.

---

## 6. Unit Tests for Tools, Not LLM Selection

**What tests validate:**
- Response structure (correct keys, types)
- Business logic invariants (sums match totals, percentages = 100%)
- Filtering functionality (date ranges, category filters)
- Error handling (invalid inputs return structured errors)

**What tests do NOT validate:**
- LLM tool selection (depends on docstrings + model behavior)
- End-to-end agent responses (requires API calls, non-deterministic)

**Why this design:**
- Unit tests are fast, free, and deterministic
- LLM behavior testing requires API calls ($) and is inherently non-deterministic
- Tool correctness is testable; LLM selection is validated manually via demo

**Trade-off:** No automated verification of "does the LLM pick the right tool?" This is validated manually through the demo script.

---

## 7. Singleton DataManager

Data is loaded once and cached. All tools access the same instance:

```python
class DataManager:
    _instance: Optional[DataManager] = None

    def __new__(cls, ...) -> DataManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

**Why this design:**
- Avoids duplicate I/O (CSVs loaded only once)
- Consistent date boundaries across all tools
- Easy to reset for testing with `DataManager.reset()`

**Trade-off:** Global state, but necessary for consistent data access and performance.

---

## 8. Revenue Excludes Returns

All revenue calculations filter out `is_returned == True` transactions:

```python
df = df[df["is_returned"] == False].copy()
```

**Why this design:**
- Returned items shouldn't count as revenue
- Consistent business logic across all revenue tools
- Explicitly documented in tool summaries

**Trade-off:** Slightly more complex queries, but accurate business metrics.

---

## 9. Pydantic Models for Response Schemas

Every tool response is defined as a Pydantic model:

```python
class RevenueByCategory(BaseToolResponse):
    data: list[CategoryRevenue]
    total_revenue: float
    top_category: str
```

**Why this design:**
- Type safety and validation
- Automatic JSON serialization
- Self-documenting code
- IDE autocomplete support

**Trade-off:** More boilerplate code, but catches errors early and ensures consistent responses.

---

## 10. Temperature = 0 for Determinism

The agent uses `temperature=0` for the LLM:

```python
params={
    "temperature": 0.0,  # Deterministic for analytics
    "max_tokens": 2000,
}
```

**Why this design:**
- Analytics responses should be consistent
- Same question should produce same tool selection
- Easier to debug and demonstrate

**Trade-off:** Less creative responses, but appropriate for business analytics.

---

## Technical Choices Summary

| Choice | Rationale |
|--------|-----------|
| **Strands SDK** | Required by assignment |
| **OpenAI GPT-4o** | Strong tool-use capability, reliable function calling |
| **Pydantic** | Type safety, validation, JSON serialization |
| **pandas** | Efficient data manipulation for aggregations |
| **pytest** | Standard Python testing, good fixture support |
| **rich** | Pretty console output for demo readability |

---

## What I Would Add With More Time

1. **Integration tests** - Test LLM tool selection with mocked responses
2. **Caching layer** - Cache expensive aggregations for repeated queries
3. **More filters** - Add date filtering to more tools
4. **Streaming responses** - Show partial results as they compute
5. **Multi-turn context** - Remember previous queries in conversation
