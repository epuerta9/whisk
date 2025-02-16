import typer
from pathlib import Path
from cookiecutter.main import cookiecutter

app = typer.Typer(help="Project initialization commands")

@app.command()
def init(
    name: str = typer.Argument(..., help="Project name"),
    template: str = typer.Option("basic", help="Template to use"),
):
    """Initialize a new Whisk project"""
    cookiecutter(
        template,
        output_dir=Path(name)
    ) 