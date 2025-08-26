# app.py

import customtkinter as ctk
import json
import threading
import os
import queue

from download_history import run_download
from process_data import run_processing

CONFIG_FILE = 'config.json'

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Steam Market Exporter")
        self.state('zoomed')
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.log_queue = queue.Queue()
        
        # --- MODIFICATION: Add a thread-safe event for stopping ---
        self.stop_event = threading.Event()

        self.config_fields = [
            "sessionid", "steamLoginSecure", "browserid", "steamCountry",
            "steamparental", "raw_data_directory", "max_retries",
            "initial_backoff_seconds", "output_file_name"
        ]
        self.entries = {}

        self.create_widgets()
        self.load_config()
        self.after(100, self.process_log_queue)

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        settings_frame = ctk.CTkFrame(self)
        settings_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        # ... (rest of the settings_frame widgets are unchanged) ...
        title_label = ctk.CTkLabel(settings_frame, text="Exporter Settings", font=ctk.CTkFont(size=16, weight="bold"))
        title_label.pack(pady=12, padx=10, fill="x")

        for field in self.config_fields:
            label = ctk.CTkLabel(settings_frame, text=f"{field}:", anchor="w")
            label.pack(pady=(8, 2), padx=20, fill="x")
            
            entry = ctk.CTkEntry(settings_frame)
            entry.pack(pady=2, padx=20, fill="x")
            self.entries[field] = entry

        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        log_label = ctk.CTkLabel(log_frame, text="Logs", font=ctk.CTkFont(size=16, weight="bold"))
        log_label.pack(pady=12, padx=10, fill="x")
        self.log_textbox = ctk.CTkTextbox(log_frame, state="disabled", wrap="word")
        self.log_textbox.pack(pady=10, padx=10, fill="both", expand=True)

        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(0,10), sticky="ew")

        self.run_button = ctk.CTkButton(bottom_frame, text="Save Config and Run Scripts", command=self.save_and_run_threaded)
        self.run_button.pack(side="left", padx=10)

        # --- MODIFICATION: Add the Stop Button ---
        self.stop_button = ctk.CTkButton(bottom_frame, text="Stop", command=self.request_stop, state="disabled", fg_color="red", hover_color="#C00000")
        self.stop_button.pack(side="left", padx=10)

        self.status_label = ctk.CTkLabel(bottom_frame, text="Ready.", text_color="gray")
        self.status_label.pack(side="right", padx=10)

    # --- MODIFICATION: Add a method to set the stop event ---
    def request_stop(self):
        self.log_queue.put(("Stop request received. Finishing current operation...", "orange"))
        self.stop_event.set()
        self.stop_button.configure(state="disabled", text="Stopping...")

    def save_and_run_threaded(self):
        # --- MODIFICATION: Clear the stop event and manage button states ---
        self.stop_event.clear()
        self.run_button.configure(state="disabled")
        self.stop_button.configure(state="normal", text="Stop")
        
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        
        thread = threading.Thread(target=self.run_logic, daemon=True)
        thread.start()

    def run_logic(self):
        # --- MODIFICATION: Pass the stop_event to worker functions and update button states in finally ---
        try:
            # (The config saving logic is unchanged)
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
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=4)
            self.log_queue.put(("Configuration saved successfully.", "green"))

            # Call functions with the stop_event
            self.log_queue.put(("--- Starting Download ---", "yellow"))
            download_success = run_download(self.log_queue, self.stop_event)
            
            # Check if stopped during download
            if self.stop_event.is_set():
                self.log_queue.put(("Download process was stopped by user.", "orange"))
                return
            
            if download_success:
                self.log_queue.put(("--- Starting Processing ---", "yellow"))
                run_processing(self.log_queue, self.stop_event)
                
                # Check if stopped during processing
                if self.stop_event.is_set():
                    self.log_queue.put(("Processing was stopped by user.", "orange"))
                    return

                self.log_queue.put(("--- All scripts completed successfully! ---", "green"))
            else:
                self.log_queue.put(("Download script failed. Halting process.", "red"))

        except Exception as e:
            self.log_queue.put((f"A critical error occurred: {e}", "red"))
        finally:
            # Always reset button states when the thread finishes
            self.run_button.configure(state="normal")
            self.stop_button.configure(state="disabled", text="Stop")
    
    # ... (rest of the App class methods are unchanged) ...
    def log(self, message, color="white"):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")
        self.status_label.configure(text=message.strip(), text_color=color)

    def process_log_queue(self):
        try:
            while True:
                message, color = self.log_queue.get_nowait()
                self.log(message, color=color)
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_log_queue)

    def load_config(self):
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


if __name__ == "__main__":
    app = App()
    app.mainloop()