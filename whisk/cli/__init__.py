import typer
from .serve import serve
from .run import run
from .init import init
from .client import client
from .nats import nats
from .. import __version__

app = typer.Typer(help="Whisk CLI")

# Add all commands at the top level
app.command()(serve)
app.command()(run)
app.command()(init)
app.command()(client)
app.command()(nats)

@app.command()
def version():
    """Show version information"""
    typer.echo(f"Whisk version {__version__}")

@app.callback()
def callback():
    """Whisk CLI - A framework for building AI applications"""
    pass

def main():
    app() 