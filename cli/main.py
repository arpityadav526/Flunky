import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from cli.api_client import register_func
from cli.config import save_token
from cli.api_client import login_user
from cli.config import delete_token, is_locked_in_lmao




app= typer.Typer(help="FLUNKY - YOUR TASK MANAGEMENT CLI")
console=Console()



## REGISTER COMMAND ##
@app.command()
def register():
    console.print(Panel.fit("📝 User Registration", style="bold blue"))
    username=Prompt.ask("Username")
    e_mail=Prompt.ask("E-mail")
    password=Prompt.ask("Password", password=True)
    try:
        user_data=register_func(username=username, e_mail=e_mail ,password=password)
        console.print(f"✅ Registered successfully! Welcome, {user_data['username']}!", style="green")
    except Exception as e:
        console.print(f"❌ Registration failed: {str(e)}", style="red")
        console.print(f"✅ Would Register : {username} , { e_mail}", style="green" )



## LOGIN COMMAND ##
@app.command()
def login():
    console.print(Panel.fit("🔐 User Login", style="bold green"))

    username=Prompt.ask("Username")
    password=Prompt.ask("Password", password=True)


    try:
    # Call the API and get token
        token = login_user(username, password)

    # Save token to config file
        save_token(token)

        console.print("✅ Logged in successfully!", style="green")

    except Exception as e:
        console.print(f"❌ Login failed: {str(e)}", style="red")



## LOGOUT COMMAND ##
@app.command()
def logout():

    if not is_locked_in_lmao():
        console.print("⚠️  You're not logged in!", style="yellow")
        return

    delete_token()
    console.print("👋 Logged out successfully!", style="yellow")




if __name__=="__main__":
    app()


