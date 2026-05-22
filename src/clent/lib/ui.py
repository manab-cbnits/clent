"""Rich UI utilities for status, progress, and formatted output."""

from contextlib import contextmanager
from rich.console import Console
from rich.panel import Panel
from typing import Generator, Any

console = Console()


def print_header(title: str, color: str = "cyan") -> None:
    """Print a formatted section header."""
    console.print()
    console.print(f"[bold {color}]-- {title} --[/bold {color}]")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green][OK][/green] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[red][ERROR][/red] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[blue][INFO][/blue] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow][!][/yellow] {message}")


@contextmanager
def status(message: str, spinner: str = "dots") -> Generator[Any, Any, Any]:
    """
    Context manager for showing a status message with spinner.

    Usage:
        with status("Loading data..."):
            # do work here
            pass
    """
    with console.status(f"[bold cyan]{message}[/bold cyan]", spinner=spinner):
        yield


def print_panel(content: str, title: str = "", color: str = "cyan") -> None:
    """Print content in a formatted panel."""
    panel = Panel(
        content,
        title=title,
        border_style=color,
        padding=(0, 1),
    )
    console.print(panel)


def print_step(step_number: int, description: str, status_text: str = "") -> None:
    """Print a numbered step."""
    if status_text:
        console.print(
            f"[bold yellow][{step_number}][/bold yellow] {description} [dim]({status_text})[/dim]"
        )
    else:
        console.print(f"[bold yellow][{step_number}][/bold yellow] {description}")
