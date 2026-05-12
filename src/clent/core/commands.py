def help_command():
    lines = []

    for name, cmd in COMMANDS.items():
        lines.append(f"/{name} - {cmd['description']}")

    return {
        "message": "\n".join(lines),
        "action": None,
    }

def bye_command():
    return {
        "message": "Goodbye!\n",
        "action": "exit",
    }

def list_sessions_command():
    return {
        "message": "",
        "action": "sessions",
    }

def delete_session_command():
    return {
        "message": "Session cleared.\n",
        "action": "clear",
    }

def new_chat_command():
    return {
        "message": "Starting a new chat...\n",
        "action": "new_chat",
    }

def resume_chat_command():
    return {
        "message": "",
        "action": "resume",
    }


COMMANDS = {
    "help": {
        "handler": help_command,
        "description": "Show available commands",
    },

    "bye": {
        "handler": bye_command,
        "description": "Exit the app",
    },

    "new": {
        "handler": new_chat_command,
        "description": "Create a new session and start chatting",
    },
    "sessions": {
        "handler": list_sessions_command,
        "description": "List all available sessions",
    },
    "resume": {
        "handler": resume_chat_command,
        "description": "Resume a previous session",
    },
    "rename": {
        "handler": None,  # TODO: implement rename_session_command
        "description": "Rename current session",
    },
    "compact": {
        "handler": None,  # TODO: implement compact_session_command
        "description": "Compact current session history",
    },
    "clear": {
        "handler": delete_session_command,
        "description": "Delete current session history",
    },
}


def commands(raw_cmd: str) -> dict:
    cmd = raw_cmd.strip().lower()

    if not cmd:
        return {
            "message": "Empty command",
            "action": None,
            "error": True,
        }
        
    if cmd == "?" or cmd == "help":
        print("Available commands:")
        cmd = "help"

    command = COMMANDS.get(cmd)

    if not command:
        return {
            "message": f"Unknown command: {cmd}",
            "action": None,
            "error": True,
        }

    return command["handler"]()