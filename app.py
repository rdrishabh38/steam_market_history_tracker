import customtkinter as ctk
import json
import threading
import os
import queue # For thread-safe communication

# --- KEY CHANGE: Import functions directly ---
from download_history import run_download
from process_data import run_processing

# --- Configuration ---
CONFIG_FILE = 'config.json'

# --- Main Application Class ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("Steam Market Exporter")
        self.state('zoomed')
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # --- Create a queue for thread communication ---
        self.log_queue = queue.Queue()

        # --- Define GUI Fields ---
        self.config_fields = [
            "sessionid", "steamLoginSecure", "browserid", "steamCountry",
            "steamparental", "raw_data_directory", "max_retries",
            "initial_backoff_seconds", "output_file_name"
        ]
        self.entries = {}

        # --- Create and Pack Widgets ---
        self.create_widgets()
        self.load_config()
        
        # --- Start polling the log queue ---
        self.after(100, self.process_log_queue)

    def center_window(self):
        """Centers the window on the screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def create_widgets(self):
        """Creates and lays out all the GUI widgets."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Left Frame for Settings ---
        settings_frame = ctk.CTkFrame(self)
        settings_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        title_label = ctk.CTkLabel(settings_frame, text="Exporter Settings", font=ctk.CTkFont(size=16, weight="bold"))
        title_label.pack(pady=12, padx=10, fill="x")

        for field in self.config_fields:
            label = ctk.CTkLabel(settings_frame, text=f"{field}:", anchor="w")
            label.pack(pady=(8, 2), padx=20, fill="x")
            
            entry = ctk.CTkEntry(settings_frame)
            entry.pack(pady=2, padx=20, fill="x")
            self.entries[field] = entry

        # --- Right Frame for Logs ---
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        
        log_label = ctk.CTkLabel(log_frame, text="Logs", font=ctk.CTkFont(size=16, weight="bold"))
        log_label.pack(pady=12, padx=10, fill="x")
        
        self.log_textbox = ctk.CTkTextbox(log_frame, state="disabled", wrap="word")
        self.log_textbox.pack(pady=10, padx=10, fill="both", expand=True)

        # --- Bottom Frame for Controls ---
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(0,10), sticky="ew")

        self.run_button = ctk.CTkButton(bottom_frame, text="Save Config and Run Scripts", command=self.save_and_run_threaded)
        self.run_button.pack(side="left", padx=10)

        self.status_label = ctk.CTkLabel(bottom_frame, text="Ready.", text_color="gray")
        self.status_label.pack(side="right", padx=10)

    def log(self, message, color="white"):
        """Helper function to add messages to the log textbox."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")
        self.status_label.configure(text=message.strip(), text_color=color)

    def process_log_queue(self):
        """Checks the queue for new log messages and updates the GUI."""
        try:
            while True:
                message, color = self.log_queue.get_nowait()
                self.log(message, color=color)
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_log_queue)

    def load_config(self):
        """Loads configuration from the nested JSON file."""
        self.log_queue.put(("Loading existing config...", "gray"))
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config_data = json.load(f)
                
                for field, value in config_data.items():
                    if field != "cookies" and field in self.entries:
                        self.entries[field].delete(0, "end")
                        self.entries[field].insert(0, str(value))
                
                if "cookies" in config_data:
                    for field, value in config_data["cookies"].items():
                        if field in self.entries:
                            self.entries[field].delete(0, "end")
                            self.entries[field].insert(0, str(value))
                            
                self.log_queue.put(("Config loaded successfully.", "green"))
            except (json.JSONDecodeError, IOError) as e:
                self.log_queue.put((f"Error loading config: {e}", "red"))
        else:
            self.log_queue.put(("No config file found. Please enter settings.", "gray"))

    def save_and_run_threaded(self):
        self.run_button.configure(state="disabled", text="Running...")
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        
        thread = threading.Thread(target=self.run_logic, daemon=True)
        thread.start()

    def run_logic(self):
        """Saves config and runs the imported functions directly."""
        # 1. Save Configuration
        self.log_queue.put(("Saving configuration...", "gray"))
        cookie_keys = {"sessionid", "steamLoginSecure", "browserid", "steamCountry", "steamparental"}
        config_data = {"cookies": {}}
        for field, entry in self.entries.items():
            value = entry.get()
            if field in cookie_keys:
                config_data["cookies"][field] = value
            else:
                if field in ["max_retries", "initial_backoff_seconds"]:
                    try: config_data[field] = int(value)
                    except ValueError: config_data[field] = 0
                else:
                    config_data[field] = value
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=4)
            self.log_queue.put(("Configuration saved successfully.", "green"))
        except IOError as e:
            self.log_queue.put((f"Error saving config: {e}", "red"))
            self.run_button.configure(state="normal", text="Save Config and Run Scripts")
            return

        # --- KEY CHANGE: Call functions directly instead of using subprocess ---
        try:
            self.log_queue.put(("--- Starting Download ---", "yellow"))
            download_success = run_download(self.log_queue)
            
            if download_success:
                self.log_queue.put(("--- Starting Processing ---", "yellow"))
                processing_success = run_processing(self.log_queue)
                if processing_success:
                    self.log_queue.put(("--- All scripts completed successfully! ---", "green"))
            else:
                self.log_queue.put(("Download script failed. Halting process.", "red"))

        except Exception as e:
            self.log_queue.put((f"A critical error occurred: {e}", "red"))
        finally:
            self.run_button.configure(state="normal", text="Save Config and Run Scripts")

# --- Main Execution ---
if __name__ == "__main__":
    # No longer need freeze_support() as we are not creating new processes
    app = App()
    app.mainloop()
