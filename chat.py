#!/usr/bin/env python3
"""
Interactive chat with the business analytics agent.

Ask any business question about the e-commerce data.
Type 'quit' or 'exit' to stop.

Usage:
    python chat.py

Example questions:
    - What is our total revenue by category?
    - Which customers have the highest lifetime value?
    - How do VIP customers compare to regular customers?
    - What's our revenue trend over time?
"""
from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel

console = Console()


def main():
    """Run interactive chat session."""
    console.print(
        Panel.fit(
            "[bold blue]Business Analytics Agent[/bold blue]\n"
            "Interactive Q&A Mode",
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

    # Check for data
    try:
        dm = get_data_manager()
    except FileNotFoundError:
        console.print("[red]Data not found.[/red] Run 'python generate_data.py' first.")
        sys.exit(1)

    # Create agent
    console.print("[dim]Initializing agent...[/dim]")
    try:
        agent = create_agent()
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("Make sure OPENAI_API_KEY is set in .env file.")
        sys.exit(1)

    console.print("[green]Ready![/green]")
    console.print(f"[dim]Data: {dm.data_start.date()} to {dm.data_end.date()} ({dm.transaction_count:,} transactions)[/dim]")
    console.print("[dim]Type 'quit' to exit, 'help' for example questions.[/dim]\n")

    # Example questions for help
    examples = [
        "What is our total revenue by category?",
        "Which customers have the highest lifetime value?",
        "What's the return rate by product category?",
        "Compare performance across regions",
        "How is this month performing compared to last month?",
        "What payment methods do customers prefer?",
        "How do VIP customers compare to regular customers?",
        "What's our revenue trend over time?",
    ]

    # Chat loop
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

        if question.lower() in ("help", "?"):
            console.print("\n[yellow]Example questions you can ask:[/yellow]")
            for ex in examples:
                console.print(f"  - {ex}")
            console.print()
            continue

        try:
            response = agent(question)
            console.print(f"\n[bold yellow]Agent:[/bold yellow] {response}\n")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}\n")


if __name__ == "__main__":
    main()
