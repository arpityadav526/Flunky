import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table



app= typer.Typer(help="FLUNKY - YOUR TASK MANAGEMENT CLI")
console=Console()



## REGISTER COMMAND ##
@app.command()
def register():
    console.print(Panel.fit("📝 User Registration", style="bold blue"))
    username=Prompt.ask("Username")
    e_mail=Prompt.ask("E-mail")
    password=Prompt.ask("Password", password=True)

    console.print(f"✅ Would Register : {username} , { e_mail}", style="green" )



## LOGIN COMMAND ##
@app.command()
def login():
    console.print(Panel.fit("🔐 User Login", style="bold green"))

    username=Prompt.ask("Username")
    password=Prompt.ask("Password", password=True)

    console.print(f"✅ Would login with these credentials", style="green")



## LOGOUT COMMAND ##
@app.command()
def logout ():
    console.print("👋 Logged out successfully!", style="yellow")




if __name__=="__main__":
    app()


