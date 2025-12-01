#!/usr/bin/env python3
"""
SRRD Bot - A simple bot application
"""

def main():
    print("=" * 50)
    print("SRRD Bot initialized successfully!")
    print("=" * 50)
    print("\nBot is running. Press Ctrl+C to exit.")
    
    try:
        while True:
            user_input = input("\nYou: ")
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("Bot: Goodbye!")
                break
            
            response = f"Bot: You said: {user_input}"
            print(response)
    except KeyboardInterrupt:
        print("\n\nBot: Shutting down gracefully...")
    except EOFError:
        print("\n\nBot: Running in non-interactive mode...")
        print("Bot: Use environment variables or config to customize behavior")

if __name__ == "__main__":
    main()
