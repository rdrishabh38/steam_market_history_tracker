# cli.py - Command-Line Interface Entry Point

import threading
import os
from download_history import run_download
from process_data import run_processing

CONFIG_FILE = 'config.json'

class ConsoleLogQueue:
    """A dummy queue that prints log messages directly to the console."""
    def put(self, message_tuple):
        message, color = message_tuple
        # We can ignore the color for the simple CLI
        print(message)

def main():
    """Main function for the command-line tool."""
    print("--- Steam Market Exporter (CLI Mode) ---")

    # Check if config file exists
    if not os.path.exists(CONFIG_FILE):
        print(f"\nERROR: '{CONFIG_FILE}' not found.")
        print("Please run the GUI application first to create and save your settings.")
        return # Exit gracefully

    # Create the objects needed by the core functions
    console_queue = ConsoleLogQueue()
    stop_event = threading.Event() # CLI can be stopped with Ctrl+C

    try:
        # Call the exact same core logic functions as the GUI
        print("\n--- Starting Phase 1: Download History ---")
        download_success = run_download(console_queue, stop_event)

        if download_success:
            print("\n--- Starting Phase 2: Process Data ---")
            run_processing(console_queue, stop_event)
            print("\n✅ Process completed successfully.")
        else:
            print("\n❌ Download phase failed. Halting process.")

    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user (Ctrl+C). Exiting.")
        stop_event.set()
    except Exception as e:
        print(f"\nAN UNEXPECTED ERROR OCCURRED: {e}")

if __name__ == "__main__":
    main()
