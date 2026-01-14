"""
Strands Agent configuration for business analytics.

Creates and configures the AI agent with:
- OpenAI GPT-4o model (temperature=0 for determinism)
- All business analytics tools
- System prompt guiding behavior

This is the ORCHESTRATION layer only:
- No business logic here
- No data access here
- Only model config, tool registration, system prompt
"""
from __future__ import annotations

from typing import Optional

from strands import Agent
from strands.handlers.callback_handler import null_callback_handler
from strands.models.openai import OpenAIModel

from .config import get_settings
from .tools import (
    compare_regions,
    explain_capabilities,
    get_customer_ltv,
    get_data_overview,
    get_month_over_month,
    get_return_rates,
    get_revenue_by_category,
)

SYSTEM_PROMPT = """You are a business analytics assistant for an e-commerce company.

Your role is to answer business questions using the available analytical tools.
Always use tools to get data - never make up numbers or statistics.

When responding:
1. Call the appropriate tool to get structured data
2. Interpret the results for the business user
3. Highlight key insights and actionable recommendations
4. Use specific numbers from the tool output

Available analyses:
- Revenue by category (with optional date and category filters)
- Customer lifetime value (top customers by spending)
- Return rates by product category
- Regional performance comparison
- Month-over-month performance trends
- Data overview (date range, record counts, available dimensions)

IMPORTANT RULES:
- If a question cannot be answered with available tools, use explain_capabilities to show what analyses are possible
- Never hallucinate data - only report what the tools return
- All time references (like "this month") are relative to the dataset's end date, not today's date
- Revenue calculations exclude returned items
- Be precise with numbers - round to 2 decimal places for currency

When presenting results:
- Start with the key finding or answer
- Provide supporting details from the data
- Suggest follow-up questions if relevant
"""


def create_agent() -> Agent:
    """
    Create and configure the business analytics agent.

    Returns:
        Agent: Configured Strands Agent ready for queries

    Raises:
        ValueError: If OPENAI_API_KEY is not set
    """
    settings = get_settings()

    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY not found. "
            "Copy .env.example to .env and add your key."
        )

    # Configure OpenAI model with deterministic settings
    model = OpenAIModel(
        client_args={
            "api_key": settings.openai_api_key,
        },
        model_id=settings.model_id,
        params={
            "temperature": 0.0,  # Deterministic for analytics
            "max_tokens": 2000,  # Sufficient for structured outputs
        },
    )

    # Create agent with all tools
    # Use null_callback_handler to suppress streaming output
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        callback_handler=null_callback_handler,
        tools=[
            get_revenue_by_category,
            get_customer_ltv,
            get_return_rates,
            compare_regions,
            get_month_over_month,
            get_data_overview,
            explain_capabilities,
        ],
    )

    return agent


# Module-level singleton for convenience
_agent: Optional[Agent] = None


def get_agent() -> Agent:
    """Get or create the agent singleton."""
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent


def reset_agent() -> None:
    """Reset agent singleton (for testing)."""
    global _agent
    _agent = None
