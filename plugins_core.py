# rootrecord/plugins_core.py
from pathlib import Path

BASE_DIR = Path(__file__).parent
PLUGIN_FOLDER = BASE_DIR / "Plugin_Files"

def ensure_plugin_folder():
    PLUGIN_FOLDER.mkdir(exist_ok=True)
    init = PLUGIN_FOLDER / "__init__.py"
    if not init.exists():
        init.touch()
        print(f"  Created __init__.py in Plugin_Files")


def initialize():
    ensure_plugin_folder()
    print("Plugins Core ready")


if __name__ == "__main__":
    initialize()