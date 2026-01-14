#!/usr/bin/env python3
"""
Quick demonstration of the business analytics agent.

Runs 3 representative queries showcasing core capabilities:
1. Revenue analysis (the most common business question)
2. Customer insights (LTV analysis)
3. Trend analysis (month-over-month performance)

Usage:
    python demo_short.py

For a full demo with all 9 tools, run:
    python demo.py
"""
from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel

console = Console()

DEMO_QUESTIONS = [
    {
        "question": "What is our total revenue by category?",
        "description": "Revenue Analysis",
    },
    {
        "question": "Which customers have the highest lifetime value?",
        "description": "Customer Insights",
    },
    {
        "question": "How is this month performing compared to last month?",
        "description": "Trend Analysis",
    },
]


def run_demo():
    """Execute the short demonstration."""
    console.print(
        Panel.fit(
            "[bold blue]Business Analytics AI Agent[/bold blue]\n"
            "Quick Demo (3 Questions)",
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
        dm = get_data_manager()
        console.print(f"[dim]Data: {dm.transaction_count:,} transactions, {dm.customer_count:,} customers[/dim]")
        console.print(f"[dim]Period: {dm.data_start.date()} to {dm.data_end.date()}[/dim]\n")
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

    console.print("[green]Ready![/green]\n")

    # Run demo questions
    for i, item in enumerate(DEMO_QUESTIONS, 1):
        console.rule(f"[bold]Question {i}: {item['description']}[/bold]")
        console.print(f"\n[cyan]Q:[/cyan] {item['question']}\n")

        try:
            response = agent(item["question"])
            console.print(f"[yellow]A:[/yellow] {response}\n")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}\n")

    console.print(
        Panel.fit(
            "[green]Demo complete![/green]",
            border_style="green",
        )
    )
    console.print()

    # Offer interactive mode
    console.print("[dim]You can now ask your own questions, or type 'quit' to exit.[/dim]")
    console.print("[dim]For full demo with all 9 tools: python demo.py[/dim]\n")

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
