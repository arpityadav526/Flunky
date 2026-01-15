import json
from pathlib import Path
from typing  import Optional

## Define config directory and file ##
CONFIG_DIR=Path.home() / "./flunky"
CONFIG_FILE=CONFIG_DIR / "config.json"


def save_token(token: str)->None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data={
        "access_token": token
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, ident=2)


def load_token()->Optional[str]:
    if not CONFIG_FILE.exists():
        return None
    try:
        with open (CONFIG_FILE, "r")as f:
            data=json.load(f)

        return data.get("access_token")
    except(json.JSONDecodeError, KeyError):
        return None





def delete_token(token: str)-> None:
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()


def is_locked_in_lmao()->bool:
    token=load_token()
    return token is not None












