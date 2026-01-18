
from setuptools import setup, find_packages

setup(
    name="flunky",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic",
        "python-jose[cryptography]",
        "passlib[bcrypt]",
        "typer",
        "rich",
        "httpx",
    ],
    entry_points={
        "console_scripts": [
            "flunky=cli.main:app",
        ],
    },
)