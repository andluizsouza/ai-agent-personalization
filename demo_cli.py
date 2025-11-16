"""
Demo: CLI Conversacional - Teste Não-Interativo

Este script demonstra o funcionamento do CLI sem interação do usuário.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from agents import create_planner_agent
from utils.chat_session import ChatSession

console = Console()


def demo_cli():
    """Demonstração do CLI funcionamento."""
    
    # Header
    console.print(Panel.fit(
        "[bold cyan]BEES AI - Demo CLI Conversacional[/bold cyan]\n"
        "[yellow]Demonstração não-interativa do fluxo completo[/yellow]",
        border_style="cyan"
    ))
    console.print()
    
    # Check API key
    if not os.getenv("GOOGLE_API_KEY"):
        console.print("[red]❌ Erro: GOOGLE_API_KEY não encontrada[/red]")
        return
    
    # Initialize agent
    console.print("[yellow]🤖 Inicializando agente...[/yellow]")
    agent = create_planner_agent()
    console.print("[green]✅ Agente inicializado![/green]\n")
    
    # Create session
    client_id = "CLT-LNU555"
    session = ChatSession(client_id=client_id)
    
    console.print(f"[cyan]📋 Session ID: {session.session_id}[/cyan]")
    console.print(f"[cyan]👤 Client ID: {client_id}[/cyan]\n")
    
    # Simulate user message
    user_message = f"Olá! Meu client_id é {client_id}. Preciso de recomendações de novas cervejarias."
    
    console.print(Panel(
        user_message,
        title="[bold cyan]👤 Usuário[/bold cyan]",
        border_style="cyan"
    ))
    console.print()
    
    # Add to session
    session.add_message("user", user_message)
    
    # Execute agent
    console.print("[yellow]🤔 Agente processando...[/yellow]\n")
    
    result = agent.run(client_id=client_id, chat_history=session.get_context_for_agent())
    
    # Show response
    response = result.get('response', '')
    session.add_message("assistant", response)
    
    console.print(Panel(
        response,
        title="[bold green]🤖 Assistente[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))
    console.print()
    
    # Show metrics
    console.print("[bold]📊 Métricas da Execução:[/bold]")
    console.print(f"  ⏱️  Tempo total: {result['execution_time_s']:.2f}s")
    console.print(f"  🔧 Tool calls: {result['tool_calls']}")
    console.print(f"  📝 Mensagens na sessão: {len(session.messages)}")
    console.print()
    
    # Show Chain-of-Thought
    console.print("[bold]🧠 Chain-of-Thought:[/bold]")
    for i, step in enumerate(result['chain_of_thought'], 1):
        console.print(f"  {i}. {step['tool']} - {step['execution_time_ms']:.0f}ms - {step['status']}")
    console.print()
    
    # Show session stats
    stats = session.get_stats()
    console.print("[bold]📈 Estatísticas da Sessão:[/bold]")
    console.print(f"  📊 Total de mensagens: {stats['total_messages']}")
    console.print(f"  👤 Mensagens do usuário: {stats['user_messages']}")
    console.print(f"  🤖 Mensagens do assistente: {stats['assistant_messages']}")
    console.print(f"  ⏱️  Duração: {stats['duration_seconds']:.2f}s")
    console.print()
    
    # Demonstrate commands
    console.print("[bold]💡 Comandos Disponíveis no CLI Interativo:[/bold]")
    console.print("  • /exit ou /quit - Sair do chat")
    console.print("  • /clear - Limpar histórico")
    console.print("  • /log - Mostrar Chain-of-Thought")
    console.print("  • /metrics - Mostrar métricas")
    console.print("  • /help - Mostrar ajuda")
    console.print()
    
    console.print("[green]✅ Demo concluída com sucesso![/green]")
    console.print("[yellow]💡 Execute 'python main.py' para modo interativo[/yellow]")


if __name__ == "__main__":
    demo_cli()
