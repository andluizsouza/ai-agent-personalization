"""
Demo: Planner Agent Execution

This script demonstrates the complete 5-step plan execution
for brewery recommendations using the orchestrator agent.

Usage:
    python demo_planner.py --client_id CLT-LNU555
    python demo_planner.py --client_id CLT-LNU555 --verbose
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agents import create_planner_agent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

console = Console()


def print_header():
    """Print demo header."""
    console.print(Panel.fit(
        "[bold cyan]BEES AI - Planner Agent Demo[/bold cyan]\n"
        "[yellow]Orchestrator with 5-Step Plan Execution[/yellow]",
        border_style="cyan"
    ))
    console.print()


def print_metrics(metrics: dict):
    """Print execution metrics in a table."""
    table = Table(title="📊 Execution Metrics", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Execution Time", f"{metrics['total_execution_time_s']:.2f}s")
    table.add_row("Total Tool Calls", str(metrics['total_tool_calls']))
    table.add_row("Tool 1 (SQL Runner)", str(metrics['tools_breakdown']['get_client_profile']))
    table.add_row("Tool 2 (Brewery Finder)", str(metrics['tools_breakdown']['search_breweries']))
    table.add_row("Tool 3 (Web Explorer)", str(metrics['tools_breakdown']['get_website_summary']))
    table.add_row("Cache Hit Rate", f"{metrics['cache_hit_rate']:.1%}")
    table.add_row("Avg Tool Time", f"{metrics['avg_tool_execution_time_ms']:.0f}ms")
    
    console.print(table)


def print_chain_of_thought(chain: list):
    """Print Chain-of-Thought trace."""
    console.print(Panel("[bold]🧠 Chain-of-Thought Trace[/bold]", border_style="yellow"))
    
    for i, step in enumerate(chain, 1):
        console.print(f"\n[cyan]Step {i}: {step['tool']}[/cyan]")
        console.print(f"  Timestamp: {step['timestamp']}")
        console.print(f"  Status: [green]{step['status']}[/green]" if step['status'] == 'success' else f"  Status: [red]{step['status']}[/red]")
        console.print(f"  Execution Time: {step['execution_time_ms']:.0f}ms")
        
        if 'cache_status' in step:
            console.print(f"  Cache Status: {step['cache_status']}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Demo of Planner Agent")
    parser.add_argument(
        '--client_id',
        type=str,
        default='CLT-LNU555',
        help='Client ID to use (default: CLT-LNU555)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    args = parser.parse_args()
    
    print_header()
    
    # Check API key
    if not os.getenv("GOOGLE_API_KEY"):
        console.print("[red]❌ Error: GOOGLE_API_KEY not found in environment[/red]")
        sys.exit(1)
    
    try:
        # Create planner agent
        console.print("[yellow]🤖 Initializing Planner Agent...[/yellow]")
        agent = create_planner_agent(verbose=args.verbose)
        console.print("[green]✅ Agent initialized successfully[/green]\n")
        
        # Execute plan
        console.print(Panel(
            f"[bold]Executing 5-step plan for client: {args.client_id}[/bold]",
            border_style="blue"
        ))
        console.print()
        
        with console.status("[bold green]🔄 Agent is thinking..."):
            result = agent.run(client_id=args.client_id)
        
        console.print()
        
        # Print result
        if result['status'] == 'success':
            console.print(Panel(
                result['response'],
                title="[green]✅ Agent Response[/green]",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"[red]Error: {result.get('error', 'Unknown error')}[/red]",
                title="[red]❌ Execution Failed[/red]",
                border_style="red"
            ))
        
        console.print()
        
        # Print metrics
        metrics = agent.get_metrics()
        print_metrics(metrics)
        
        console.print()
        
        # Print Chain-of-Thought
        chain = agent.get_chain_of_thought()
        print_chain_of_thought(chain)
        
        console.print()
        console.print("[green]✅ Demo completed successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        if args.verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
