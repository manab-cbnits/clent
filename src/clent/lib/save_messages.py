


def save_message(user_input: str, ai_message: str):
    try:
        # Save the messages to a JSON file

        print(f"Saving message...\nUser: {user_input}\nAI: {ai_message}")

        return {
            "success": True
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
