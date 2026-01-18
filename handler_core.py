# rootrecord/handler_core.py
from pathlib import Path

BASE_DIR = Path(__file__).parent
HANDLER_FOLDER = BASE_DIR / "Handler_Files"

def ensure_handler_folder():
    HANDLER_FOLDER.mkdir(exist_ok=True)
    init = HANDLER_FOLDER / "__init__.py"
    if not init.exists():
        init.touch()
        print(f"  Created __init__.py in Handler_Files")


def initialize():
    ensure_handler_folder()
    print("Handler Core ready")


if __name__ == "__main__":
    initialize()