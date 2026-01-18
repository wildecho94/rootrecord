# commands/cmd_loader.py
# Edited Version: 1.42.20260110

"""
Dynamic command loader - auto-discovers and registers all *_cmd.py files in this folder
Future-proof: new commands are added automatically by just creating a new file
"""

import importlib.util
import os
from pathlib import Path

COMMANDS = {}  # cmd_name → handler object


def load_commands(dp):
    """
    Call this once during telegram plugin initialization.
    Example: load_commands(application)
    """
    folder = Path(__file__).parent.resolve()
    for path in sorted(folder.glob("*_cmd.py")):
        if path.name.startswith('__'):
            continue

        cmd_name = path.stem.replace("_cmd", "")
        module_name = f"commands.{path.stem}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "handler"):
                COMMANDS[cmd_name] = module.handler
                dp.add_handler(module.handler)
                print(f"[commands] Loaded /{cmd_name}")
            else:
                print(f"[commands] {path.name} missing required 'handler' attribute")
        except Exception as e:
            print(f"[commands] Failed to load {path.name}: {e}")


def get_loaded_commands():
    return sorted(COMMANDS.keys())