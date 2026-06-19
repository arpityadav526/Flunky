from rich.theme import Theme
from rich.console import Console

# Define the custom theme for Flunky CLI
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "prompt": "magenta",
    "highlight": "bold magenta",
    "banner": "bold cyan"
})

# Create a globally available console instance with the theme
console = Console(theme=custom_theme)
