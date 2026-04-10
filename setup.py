from setuptools import setup, find_packages

setup(
    name="flunky",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic",
        "python-jose",
        "passlib[bcrypt]",
        "python-dotenv",
        "python-multipart",
        "typer",
        "rich",
        "httpx",
        "requests",
        "email-validator",
        "jinja2",
    ],
    entry_points={
        "console_scripts": [
            "flunky=cli.main:app",
        ],
    },
)