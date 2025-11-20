"""
BEES AI - CLI Conversacional

Interface de linha de comando interativa para o Assistente de Reabastecimento Inteligente.

Features:
- Chat conversacional com contexto persistente
- Comandos especiais (/exit, /clear, /log, /metrics)
- Interface rica com Rich library
- Timeout visual para perguntas condicionais
- Modo debug
- Gerenciamento de sessão

Usage:
    python main.py                    # Modo interativo
    python main.py --client_id C001   # Com client_id pré-definido
    python main.py --debug            # Modo debug
"""

import os
import sys
import argparse
import asyncio
import signal
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich import print as rprint
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agents import create_planner_agent, PlannerAgent
from utils.chat_session import ChatSession
from utils.prompt_loader import load_prompt

console = Console()


class ConversationalCLI:
    """
    Conversational CLI for the BEES AI Assistant.
    
    Manages interactive chat sessions with the planner agent,
    handles special commands, and provides rich terminal UI.
    """
    
    def __init__(self, client_id: Optional[str] = None, debug: bool = False):
        """
        Initialize conversational CLI.
        
        Args:
            client_id: Optional pre-defined client ID
            debug: Enable debug mode
        """
        self.client_id = client_id
        self.debug = debug
        self.session = ChatSession(client_id=client_id)
        self.agent: Optional[PlannerAgent] = None
        self.running = True
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        console.print("\n[yellow] Encerrando sessão...[/yellow]")
        self.running = False
        sys.exit(0)
    
    def print_welcome(self):
        """Print welcome message."""
        welcome_text = load_prompt('initial_welcome.txt')
        
        console.print(Panel(
            Markdown(welcome_text),
            border_style="cyan",
            padding=(1, 2)
        ))
    
    def print_client_welcome(self, client_name: str):
        """
        Print personalized interaction options after client identification.
        Loads message from prompts/interaction_options.txt
        
        Args:
            client_name: Name of the identified client
        """
        
        # Load interaction options template
        welcome_file = Path(__file__).parent / "prompts" / "interaction_options.txt"
        
        if not welcome_file.exists():
            console.print("[yellow]Arquivo de boas-vindas não encontrado.[/yellow]")
            return
        
        with open(welcome_file, 'r', encoding='utf-8') as f:
            welcome_template = f.read()
        
        # Replace {client_name} placeholder
        welcome_message = welcome_template.replace("{client_name}", client_name)
        
        # Display with rich formatting
        console.print()
        console.print(Panel(
            Markdown(welcome_message),
            border_style="green",
            padding=(1, 2),
            title="[bold green]Bem-vindo![/bold green]",
            subtitle="[dim]Comandos: /help | /exit[/dim]"
        ))
        console.print()
    
    def initialize_agent(self):
        """Initialize the planner agent."""
        try:
            with console.status("[bold green] Inicializando agente..."):
                self.agent = create_planner_agent(verbose=self.debug)
            console.print("[green]Agente inicializado com sucesso![/green]\n")
        except Exception as e:
            console.print(f"[red]Erro ao inicializar agente: {e}[/red]")
            if self.debug:
                console.print_exception()
            sys.exit(1)
    
    def request_client_id(self) -> bool:
        """
        Request client_id from user with up to 3 attempts.
        Validates if client exists in database.
        
        Returns:
            True if valid client_id obtained, False otherwise
        """
        max_attempts = 3
        
        console.print(Panel(
            "[bold cyan]Para começar, preciso identificar seu perfil.[/bold cyan]\n\n"
            "Por favor, informe seu Client ID para que eu possa buscar suas preferências "
            "e fazer recomendações personalizadas.",
            title="[cyan]Identificação[/cyan]",
            border_style="cyan",
            padding=(1, 2)
        ))
        console.print()
        
        for attempt in range(1, max_attempts + 1):
            try:
                if attempt > 1:
                    console.print(f"[yellow]Tentativa {attempt} de {max_attempts}[/yellow]\n")
                
                console.print("[cyan]Informe seu Client ID[/cyan]")
                console.print("[dim]Formato esperado: CLT-XXXXXX [/dim]\n")
                
                client_id = Prompt.ask("[bold cyan]Client ID[/bold cyan]").strip().upper()
                
                if not client_id:
                    console.print("[yellow]Client ID não pode estar vazio.[/yellow]\n")
                    continue
                
                # Validate format
                import re
                if not re.match(r'^CLT-[A-Z0-9]+$', client_id):
                    console.print(
                        f"[yellow]Formato inválido: '{client_id}'[/yellow]\n"
                        "[dim]O Client ID deve começar com 'CLT-' seguido de letras/números.[/dim]\n"
                    )
                    continue
                
                # Validate if client exists in database
                console.print(f"\n[dim]✓ Verificando Client ID {client_id} na base...[/dim]")
                
                from tools.sql_runner import get_client_profile
                response = get_client_profile(client_id=client_id)
                
                # Check if client was found (result will be None if not found)
                if not response.get('result'):
                    console.print(
                        f"[red]✗ Client ID '{client_id}' não encontrado na base de dados.[/red]\n"
                        "[dim]Verifique se digitou corretamente ou entre em contato com o suporte.[/dim]\n"
                    )
                    continue
                
                # Success! Extract client data from result
                client_data = response['result']
                self.session.set_client_id(client_id)
                console.print(
                    f"\n[green]✓ Perfeito! Cliente identificado com sucesso.[/green]\n"
                )
                
                # Show personalized welcome message with capabilities
                client_name = client_data.get('client_name', 'Cliente')
                self.print_client_welcome(client_name)
                
                return True
                
            except KeyboardInterrupt:
                console.print("\n[yellow] Operação cancelada.[/yellow]")
                return False
            except Exception as e:
                console.print(f"[red]Erro ao validar client_id: {e}[/red]\n")
                if self.debug:
                    console.print_exception()
                continue
        
        # All attempts failed
        console.print()
        console.print(Panel(
            "[bold yellow]Não foi possível identificar seu perfil após 3 tentativas.[/bold yellow]\n\n"
            "Para sua segurança e melhor experiência, é necessário um Client ID válido "
            "para continuar.\n\n"
            "Por favor:\n"
            "• Verifique se o Client ID está correto\n"
            "• Entre em contato com o suporte BEES\n"
            "• Tente novamente mais tarde\n\n"
            "[dim]Obrigado pela compreensão![/dim]",
            title="[yellow] Sessão Encerrada[/yellow]",
            border_style="yellow",
            padding=(1, 2)
        ))
        console.print()
        return False
    
    def handle_command(self, command: str) -> bool:
        """
        Handle special commands.
        
        Args:
            command: Command string (e.g., '/exit', '/clear')
            
        Returns:
            True if should continue, False if should exit
        """
        command = command.lower().strip()
        
        if command in ['/exit', '/quit']:
            console.print("[yellow]Até logo![/yellow]")
            return False
        
        elif command == '/clear':
            self.session.clear_history()
            console.clear()
            console.print("[green]Histórico limpo![/green]\n")
            self.print_welcome()
        
        elif command == '/log':
            self.show_chain_of_thought()
        
        elif command == '/metrics':
            self.show_metrics()
        
        elif command == '/help':
            self.print_welcome()
        
        else:
            console.print(f"[red]Comando desconhecido: {command}[/red]")
            console.print("[yellow]Digite /help para ver comandos disponíveis[/yellow]\n")
        
        return True
    
    def show_chain_of_thought(self):
        """Display Chain-of-Thought trace from last execution."""
        if not self.agent or not self.agent.execution_log:
            console.print("[yellow]Nenhuma execução ainda[/yellow]\n")
            return
        
        console.print(Panel("[bold]Chain-of-Thought - Última Execução[/bold]", border_style="cyan"))
        
        for i, step in enumerate(self.agent.execution_log, 1):
            console.print(f"\n[cyan]Passo {i}: {step['tool']}[/cyan]")
            console.print(f"  Timestamp: {step['timestamp']}")
            
            status_color = "green" if step['status'] == 'success' else "red"
            console.print(f"  Status: [{status_color}]{step['status']}[/{status_color}]")
            console.print(f"  Tempo: {step['execution_time_ms']:.0f}ms")
            
            if 'cache_status' in step:
                console.print(f"  Cache: {step['cache_status']}")
        
        console.print()
    
    def show_metrics(self):
        """Display session metrics."""
        if not self.agent:
            console.print("[yellow]Agente não inicializado[/yellow]\n")
            return
        
        # Get agent metrics
        agent_metrics = self.agent.get_metrics()
        
        # Get session stats
        session_stats = self.session.get_stats()
        
        # Create metrics table
        table = Table(title="Métricas da Sessão", show_header=True, header_style="bold magenta")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="green")
        
        # Session metrics
        table.add_row("Session ID", session_stats['session_id'])
        if session_stats['client_id']:
            table.add_row("Client ID", session_stats['client_id'])
        table.add_row("Duração", f"{session_stats['duration_seconds']:.1f}s")
        table.add_row("Total de Mensagens", str(session_stats['total_messages']))
        
        # Agent metrics (if available)
        if isinstance(agent_metrics, dict) and 'total_tool_calls' in agent_metrics:
            table.add_row("", "")  # Separator
            table.add_row("Tool Calls Total", str(agent_metrics['total_tool_calls']))
            table.add_row("Tool 1 (SQL Runner)", str(agent_metrics['tools_breakdown']['get_client_profile']))
            table.add_row("Tool 2 (Brewery Finder)", str(agent_metrics['tools_breakdown']['search_breweries']))
            table.add_row("Tool 3 (Web Explorer)", str(agent_metrics['tools_breakdown']['get_website_summary']))
            table.add_row("Cache Hit Rate", f"{agent_metrics['cache_hit_rate']:.1%}")
        
        console.print(table)
        console.print()
    
    async def get_user_input_with_timeout(self, timeout: int = 30) -> Optional[str]:
        """
        Get user input with timeout for conditional questions.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            User input or None if timeout
        """
        try:
            # Create a task for getting input
            loop = asyncio.get_event_loop()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[yellow]Aguardando resposta... (timeout em {task.fields[remaining]}s)[/yellow]"),
                console=console
            ) as progress:
                task = progress.add_task("waiting", remaining=timeout)
                
                # Use run_in_executor for blocking input
                input_task = loop.run_in_executor(None, Prompt.ask, "[bold cyan]Você[/bold cyan]")
                
                # Wait with timeout
                for remaining in range(timeout, 0, -1):
                    progress.update(task, remaining=remaining)
                    
                    # Check if input is ready
                    done, pending = await asyncio.wait([input_task], timeout=1)
                    
                    if done:
                        return await input_task
                
                # Timeout reached
                console.print("\n[yellow]Tempo esgotado! Continuando sem detalhes...[/yellow]\n")
                return None
                
        except Exception as e:
            if self.debug:
                console.print(f"[red]Erro no timeout: {e}[/red]")
            return None
    
    def process_message(self, user_message: str) -> Optional[str]:
        """
        Process user message with the agent.
        
        Args:
            user_message: User's message
            
        Returns:
            Agent's response or None if error
        """
        try:
            # Add user message to session
            self.session.add_message("user", user_message)
            
            # Client ID should always be available at this point
            # (obtained via argument or request_client_id())
            client_id = self.session.client_id
            
            if not client_id:
                console.print("[red]Erro: Client ID não disponível.[/red]")
                return None
            
            # Now show thinking indicator and execute agent
            with console.status("[bold green]Pensando..."):
                # Execute agent
                result = self.agent.run(
                    client_id=client_id,
                    chat_history=self.session.get_context_for_agent()
                )
            
            response = result.get('response', '')
            
            # Add agent response to session
            self.session.add_message("assistant", response)
            
            return response
            
        except Exception as e:
            console.print(f"[red]Erro ao processar mensagem: {e}[/red]")
            if self.debug:
                console.print_exception()
            return None
    
    def chat_loop(self):
        """Main chat loop."""
        console.print()
        
        while self.running:
            try:
                # Get user input
                user_input = Prompt.ask("[bold cyan]Você[/bold cyan]")
                
                if not user_input.strip():
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    if not self.handle_command(user_input):
                        break
                    continue
                
                # Process message
                response = self.process_message(user_input)
                
                if response:
                    # Display agent response
                    console.print(Panel(
                        response,
                        title="[green]Assistente[/green]",
                        border_style="green",
                        padding=(1, 2)
                    ))
                    console.print()
                    
                    # Check if response contains conditional question
                    if "sim" in response.lower() and "não" in response.lower() and "?" in response:
                        # This is likely the conditional question
                        console.print("[yellow]Dica: Responda 'sim' ou 'não' para continuar[/yellow]\n")
            
            except KeyboardInterrupt:
                self._signal_handler(None, None)
            except EOFError:
                console.print("\n[yellow] Até logo![/yellow]")
                break
            except Exception as e:
                console.print(f"[red] Erro: {e}[/red]")
                if self.debug:
                    console.print_exception()
    
    def run(self):
        """Run the conversational CLI."""
        self.print_welcome()
        
        # Check API key
        if not os.getenv("GOOGLE_API_KEY"):
            console.print("[red] Erro: GOOGLE_API_KEY não encontrada[/red]")
            console.print("[yellow] Configure a variável de ambiente GOOGLE_API_KEY[/yellow]")
            sys.exit(1)
        
        # Initialize agent
        self.initialize_agent()
        
        # Request client_id if not provided via argument
        if not self.client_id:
            if not self.request_client_id():
                # Failed to get valid client_id after 3 attempts
                console.print("[yellow] Até breve! Volte quando tiver seu Client ID.[/yellow]\n")
                sys.exit(0)
        else:
            # Client_id provided via argument - validate it
            console.print(f"[dim]✓ Validando Client ID {self.client_id}...[/dim]")
            from tools.sql_runner import get_client_profile
            response = get_client_profile(client_id=self.client_id)
            
            # Check if client was found (result will be None if not found)
            if not response.get('result'):
                console.print(
                    f"[red]✗ Client ID '{self.client_id}' não encontrado na base de dados.[/red]\n"
                    "[yellow]⚠ Verifique o Client ID e tente novamente.[/yellow]\n"
                )
                sys.exit(1)
            
            # Extract client data from result
            client_data = response['result']
            console.print(
                f"[green]✓ Cliente identificado com sucesso![/green]\n"
            )
            self.session.set_client_id(self.client_id)
            
            # Show personalized welcome message with capabilities
            client_name = client_data.get('client_name', 'Cliente')
            self.print_client_welcome(client_name)
        
        # Start chat loop
        try:
            self.chat_loop()
        except Exception as e:
            console.print(f"[red] Erro fatal: {e}[/red]")
            if self.debug:
                console.print_exception()
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="BEES AI - Assistente de Reabastecimento Inteligente"
    )
    parser.add_argument(
        '--client_id',
        type=str,
        help='Client ID pré-definido (ex: CLT-LNU555)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Ativar modo debug'
    )
    
    args = parser.parse_args()
    
    # Create and run CLI
    cli = ConversationalCLI(client_id=args.client_id, debug=args.debug)
    cli.run()


if __name__ == "__main__":
    main()
