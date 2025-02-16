import typer
from whisk import __version__

def version():
    """Show version information"""
    typer.echo(f"Whisk version {__version__}") 