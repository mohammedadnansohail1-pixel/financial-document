"""
Command Line Interface for Financial Report Intelligence System
Provides easy interaction with the system via terminal
"""

import click
import requests
import json
from typing import Optional
from datetime import datetime
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
from rich.panel import Panel
from rich import print as rprint

console = Console()


class FinRAGCLI:
    """CLI client for FinRAG system"""

    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url.rstrip('/')
        self.session = requests.Session()

    def query(
        self,
        query: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        k: int = 20,
        use_citation: bool = True
    ):
        """
        Query the financial RAG system
        """
        payload = {
            "query": query,
            "k": k,
            "use_citation": use_citation
        }

        if start_date and end_date:
            payload["temporal_context"] = {
                "start_date": start_date,
                "end_date": end_date
            }

        try:
            response = self.session.post(
                f"{self.api_url}/api/v1/query",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error: {e}[/red]")
            return None

    def upload_document(
        self,
        file_path: str,
        document_type: str,
        company: str,
        filing_date: str,
        cik: Optional[str] = None
    ):
        """
        Upload a financial document
        """
        path = Path(file_path)

        if not path.exists():
            console.print(f"[red]File not found: {file_path}[/red]")
            return None

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        payload = {
            "document_id": path.stem,
            "document_type": document_type,
            "company": company,
            "cik": cik,
            "filing_date": filing_date,
            "content": content
        }

        try:
            response = self.session.post(
                f"{self.api_url}/api/v1/documents/upload",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error: {e}[/red]")
            return None

    def check_compliance(
        self,
        file_path: str,
        document_type: str,
        company: str,
        jurisdiction: str = "US"
    ):
        """
        Check compliance of a document
        """
        path = Path(file_path)

        if not path.exists():
            console.print(f"[red]File not found: {file_path}[/red]")
            return None

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        payload = {
            "document_id": path.stem,
            "document_type": document_type,
            "company": company,
            "content": content,
            "jurisdiction": jurisdiction
        }

        try:
            response = self.session.post(
                f"{self.api_url}/api/v1/compliance/check",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error: {e}[/red]")
            return None

    def temporal_analysis(
        self,
        company: str,
        start_date: str,
        end_date: str,
        metrics: list
    ):
        """
        Perform temporal analysis
        """
        payload = {
            "company": company,
            "start_date": start_date,
            "end_date": end_date,
            "metrics": metrics
        }

        try:
            response = self.session.post(
                f"{self.api_url}/api/v1/temporal/analyze",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error: {e}[/red]")
            return None

    def health_check(self):
        """
        Check system health
        """
        try:
            response = self.session.get(f"{self.api_url}/health", timeout=5)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error: {e}[/red]")
            return None

    def get_stats(self):
        """
        Get system statistics
        """
        try:
            response = self.session.get(f"{self.api_url}/api/v1/system/stats", timeout=5)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error: {e}[/red]")
            return None


# Click CLI commands
@click.group()
@click.option('--api-url', default='http://localhost:8000', help='API URL')
@click.pass_context
def cli(ctx, api_url):
    """Financial Report Intelligence CLI"""
    ctx.ensure_object(dict)
    ctx.obj['client'] = FinRAGCLI(api_url=api_url)


@cli.command()
@click.argument('query')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.option('--k', default=20, help='Number of results')
@click.option('--no-citations', is_flag=True, help='Disable citations')
@click.pass_context
def query(ctx, query, start_date, end_date, k, no_citations):
    """Query the financial RAG system"""
    client = ctx.obj['client']

    with console.status("[bold green]Querying..."):
        result = client.query(
            query=query,
            start_date=start_date,
            end_date=end_date,
            k=k,
            use_citation=not no_citations
        )

    if result:
        # Display answer
        console.print("\n[bold cyan]Answer:[/bold cyan]")
        console.print(Panel(result['answer'], border_style="green"))

        # Display metadata
        console.print(f"\n[bold]Confidence:[/bold] {result['confidence']:.2%}")
        console.print(f"[bold]Hallucination Score:[/bold] {result['hallucination_score']:.2%}")
        console.print(f"[bold]Sources:[/bold] {result['source_count']}")

        # Display citations
        if result.get('citations'):
            console.print(f"\n[bold cyan]Citations ({len(result['citations'])}):[/bold cyan]")

            table = Table(show_header=True)
            table.add_column("#", style="cyan")
            table.add_column("Source", style="green")
            table.add_column("Type", style="yellow")
            table.add_column("Confidence", style="magenta")

            for i, citation in enumerate(result['citations'][:10], 1):
                table.add_row(
                    str(i),
                    citation['source_document'][:30] + "...",
                    citation['source_type'],
                    f"{citation['confidence']:.2%}"
                )

            console.print(table)


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--type', 'document_type', required=True, help='Document type (10-K, 10-Q, etc.)')
@click.option('--company', required=True, help='Company name')
@click.option('--date', 'filing_date', required=True, help='Filing date (YYYY-MM-DD)')
@click.option('--cik', help='CIK number')
@click.pass_context
def upload(ctx, file_path, document_type, company, filing_date, cik):
    """Upload a financial document"""
    client = ctx.obj['client']

    with console.status("[bold green]Uploading document..."):
        result = client.upload_document(
            file_path=file_path,
            document_type=document_type,
            company=company,
            filing_date=filing_date,
            cik=cik
        )

    if result:
        console.print("\n[bold green]Upload successful![/bold green]")
        console.print(f"Document ID: {result.get('document_id')}")
        console.print(f"Chunks processed: {result.get('chunks_processed')}")
        console.print(f"Entities extracted: {result.get('entities_extracted')}")
        console.print(f"KG nodes created: {result.get('kg_nodes_created')}")
        console.print(f"KG edges created: {result.get('kg_edges_created')}")


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--type', 'document_type', required=True, help='Document type')
@click.option('--company', required=True, help='Company name')
@click.option('--jurisdiction', default='US', help='Jurisdiction (US, EU)')
@click.pass_context
def compliance(ctx, file_path, document_type, company, jurisdiction):
    """Check compliance of a document"""
    client = ctx.obj['client']

    with console.status("[bold green]Checking compliance..."):
        result = client.check_compliance(
            file_path=file_path,
            document_type=document_type,
            company=company,
            jurisdiction=jurisdiction
        )

    if result:
        # Display compliance status
        status = "[green]COMPLIANT[/green]" if result['compliant'] else "[red]NON-COMPLIANT[/red]"
        console.print(f"\n[bold]Status:[/bold] {status}")

        # Display violations
        if result.get('violations'):
            console.print(f"\n[bold red]Violations ({len(result['violations'])}):[/bold red]")

            for v in result['violations']:
                console.print(Panel(
                    f"[bold]{v['regulation']}[/bold]\n"
                    f"Severity: {v['severity']}\n"
                    f"Description: {v['description']}\n"
                    f"Recommendation: {v.get('recommendation', 'N/A')}",
                    border_style="red"
                ))

        # Display warnings
        if result.get('warnings'):
            console.print(f"\n[bold yellow]Warnings ({len(result['warnings'])}):[/bold yellow]")
            for w in result['warnings']:
                console.print(f"  - {w.get('message')}")

        # Display risk scores
        if result.get('risk_scores'):
            console.print("\n[bold]Risk Scores:[/bold]")

            table = Table(show_header=True)
            table.add_column("Risk Type", style="cyan")
            table.add_column("Score", style="yellow")
            table.add_column("Level", style="magenta")

            for risk_type, score in result['risk_scores'].items():
                level = "LOW" if score < 0.3 else "MEDIUM" if score < 0.6 else "HIGH"
                color = "green" if score < 0.3 else "yellow" if score < 0.6 else "red"

                table.add_row(
                    risk_type,
                    f"{score:.2f}",
                    f"[{color}]{level}[/{color}]"
                )

            console.print(table)


@cli.command()
@click.option('--company', required=True, help='Company name')
@click.option('--start-date', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', required=True, help='End date (YYYY-MM-DD)')
@click.option('--metrics', required=True, help='Comma-separated metrics')
@click.pass_context
def analyze(ctx, company, start_date, end_date, metrics):
    """Perform temporal analysis"""
    client = ctx.obj['client']
    metrics_list = [m.strip() for m in metrics.split(',')]

    with console.status("[bold green]Analyzing..."):
        result = client.temporal_analysis(
            company=company,
            start_date=start_date,
            end_date=end_date,
            metrics=metrics_list
        )

    if result:
        console.print(f"\n[bold cyan]Temporal Analysis: {company}[/bold cyan]")
        console.print(f"Period: {start_date} to {end_date}\n")

        # Display trends
        if result.get('trends'):
            console.print("[bold]Trends:[/bold]")

            for period, trends in result['trends'].items():
                if trends:
                    console.print(f"\n  {period.upper()}:")
                    for metric, trend in trends.items():
                        direction = trend['direction'].upper()
                        magnitude = trend['magnitude']
                        confidence = trend['confidence']

                        direction_color = "green" if direction == "UP" else "red" if direction == "DOWN" else "yellow"

                        console.print(
                            f"    [{direction_color}]{metric}[/{direction_color}]: "
                            f"{direction} ({magnitude:+.1f}%) [confidence: {confidence:.2f}]"
                        )

        # Display events
        if result.get('events'):
            console.print(f"\n[bold]Anomalous Events ({len(result['events'])}):[/bold]")

            for event in result['events'][:5]:
                console.print(
                    f"  - {event['event_type'].upper()} on {event['timestamp'][:10]} "
                    f"(severity: {event['severity']:.2f})"
                )


@cli.command()
@click.pass_context
def health(ctx):
    """Check system health"""
    client = ctx.obj['client']

    with console.status("[bold green]Checking health..."):
        result = client.health_check()

    if result:
        console.print("\n[bold green]System Status: Healthy[/bold green]")
        console.print(f"Timestamp: {result.get('timestamp')}")

        if result.get('components'):
            table = Table(show_header=True)
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="green")

            for component, status in result['components'].items():
                table.add_row(component, status)

            console.print(table)


@cli.command()
@click.pass_context
def stats(ctx):
    """Get system statistics"""
    client = ctx.obj['client']

    with console.status("[bold green]Fetching statistics..."):
        result = client.get_stats()

    if result:
        console.print("\n[bold cyan]System Statistics[/bold cyan]")
        console.print(f"Timestamp: {result.get('timestamp')}\n")

        console.print(f"[bold]Documents Indexed:[/bold] {result.get('documents_indexed')}")

        if result.get('knowledge_graph'):
            kg = result['knowledge_graph']
            console.print(f"\n[bold]Knowledge Graph:[/bold]")
            console.print(f"  Total Nodes: {kg.get('total_nodes')}")
            console.print(f"  Total Edges: {kg.get('total_edges')}")

            if kg.get('node_types'):
                console.print("\n  Node Types:")
                for node_type, count in kg['node_types'].items():
                    console.print(f"    - {node_type}: {count}")


@cli.command()
def interactive():
    """Start interactive mode"""
    console.print(Panel.fit(
        "[bold cyan]Financial Report Intelligence - Interactive Mode[/bold cyan]\n"
        "Type 'help' for commands, 'exit' to quit",
        border_style="cyan"
    ))

    client = FinRAGCLI()

    while True:
        try:
            user_input = console.input("\n[bold green]finrag>[/bold green] ")

            if user_input.lower() in ['exit', 'quit']:
                console.print("[yellow]Goodbye![/yellow]")
                break

            elif user_input.lower() == 'help':
                console.print("""
Available commands:
  query <question>       - Query the system
  upload <file>          - Upload a document
  compliance <file>      - Check compliance
  health                 - Check system health
  stats                  - View system statistics
  exit                   - Exit interactive mode
                """)

            elif user_input.lower() == 'health':
                result = client.health_check()
                if result:
                    console.print(f"[green]System healthy[/green]: {result.get('status')}")

            elif user_input.lower() == 'stats':
                result = client.get_stats()
                if result:
                    console.print(json.dumps(result, indent=2))

            elif user_input.startswith('query '):
                question = user_input[6:].strip()
                result = client.query(question)

                if result:
                    console.print(f"\n[cyan]Answer:[/cyan] {result['answer']}")
                    console.print(f"Confidence: {result['confidence']:.2%}")

            else:
                console.print("[yellow]Unknown command. Type 'help' for available commands.[/yellow]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
            continue
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


def main():
    """Main entry point"""
    try:
        cli(obj={})
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
