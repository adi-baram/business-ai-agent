#!/usr/bin/env python3
"""
Demonstration script for the business analytics agent.

Runs 9 queries showcasing all available tools:
1. Data overview
2. Revenue by category
3. Customer lifetime value
4. Return rates
5. Regional comparison
6. Month-over-month performance
7. Payment method analysis
8. Customer segment comparison
9. Revenue trends

Usage:
    python demo.py

Requirements:
    - Run 'python generate_data.py' first to create data files
    - Set OPENAI_API_KEY in .env file
"""
from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

DEMO_QUESTIONS = [
    {
        "question": "What data do we have available? What's the date range and how many records?",
        "description": "Data Overview",
    },
    {
        "question": "What is our total revenue by category?",
        "description": "Revenue by Category",
    },
    {
        "question": "Which customers have the highest lifetime value?",
        "description": "Customer Lifetime Value",
    },
    {
        "question": "What's the return rate by product category?",
        "description": "Return Rates",
    },
    {
        "question": "Compare performance across regions",
        "description": "Regional Comparison",
    },
    {
        "question": "How is this month performing compared to last month?",
        "description": "Month-over-Month",
    },
    {
        "question": "What payment methods do customers prefer?",
        "description": "Payment Method Analysis",
    },
    {
        "question": "How do VIP customers compare to regular and new customers?",
        "description": "Customer Segment Comparison",
    },
    {
        "question": "What's our revenue trend over the past year?",
        "description": "Revenue Trends",
    },
]


def print_data_context():
    """Print information about the loaded data."""
    from src.data_loader import get_data_manager

    dm = get_data_manager()

    table = Table(title="Dataset Information", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Data Period", f"{dm.data_start.date()} to {dm.data_end.date()}")
    table.add_row("Transactions", f"{dm.transaction_count:,}")
    table.add_row("Customers", f"{dm.customer_count:,}")
    table.add_row("Current Month", f"{dm.current_month_start.date()} to {dm.current_month_end.date()}")

    console.print(table)
    console.print()


def run_demo():
    """Execute the demonstration."""
    console.print(
        Panel.fit(
            "[bold blue]Business Analytics AI Agent Demo[/bold blue]\n"
            "Powered by Strands SDK + OpenAI GPT-4o",
            border_style="blue",
        )
    )
    console.print()

    # Import and validate setup
    try:
        from src.agent import create_agent
        from src.data_loader import get_data_manager
    except ImportError as e:
        console.print(f"[red]Import error:[/red] {e}")
        console.print("Make sure you're in the project root directory.")
        sys.exit(1)

    # Check for data files
    try:
        print_data_context()
    except FileNotFoundError as e:
        console.print(f"[red]Data not found:[/red] {e}")
        console.print("\nRun 'python generate_data.py' to create the data files.")
        sys.exit(1)

    # Create agent
    console.print("[dim]Initializing agent...[/dim]")
    try:
        agent = create_agent()
    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        console.print("\nMake sure OPENAI_API_KEY is set in your .env file.")
        sys.exit(1)

    console.print("[green]Agent ready![/green]\n")

    # Run demo questions
    for i, item in enumerate(DEMO_QUESTIONS, 1):
        console.rule(f"[bold]Demo {i}: {item['description']}[/bold]")
        console.print(f"\n[cyan]Question:[/cyan] {item['question']}\n")

        try:
            response = agent(item["question"])
            console.print("[yellow]Response:[/yellow]")
            console.print(str(response))
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")

        console.print()

    # Closing message
    console.print(
        Panel.fit(
            "[bold green]Demo complete![/bold green]",
            border_style="green",
        )
    )
    console.print()

    # Offer interactive mode
    console.print("[dim]You can now ask your own questions, or type 'quit' to exit.[/dim]")
    console.print("[dim]To run tests: pytest tests/ -v[/dim]\n")

    while True:
        try:
            question = console.input("[bold cyan]You:[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not question:
            continue

        if question.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        try:
            response = agent(question)
            console.print(f"\n[bold yellow]Agent:[/bold yellow] {response}\n")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}\n")


if __name__ == "__main__":
    run_demo()
