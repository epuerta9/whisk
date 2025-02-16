import typer
from ..client import WhiskClient

app = typer.Typer(help="Client management commands")

@app.command()
def register(
    name: str = typer.Argument(..., help="Client name"),
    url: str = typer.Option("http://localhost:8000", help="Server URL")
):
    """Register a new client"""
    client = WhiskClient(url)
    result = client.register(name)
    typer.echo(f"Client registered: {result}")

def client(
    url: str = typer.Option(..., help="Server URL"),
    api_key: str = typer.Option(None, help="API key"),
):
    """Connect to a Whisk server"""
    # ... implementation ... 