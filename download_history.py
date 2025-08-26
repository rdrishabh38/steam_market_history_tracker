# download_history.py

import requests
import json
import os
import time
import math
import threading

# --- MODIFICATION: Make STATE_FILE a global constant ---
STATE_FILE = "state.json"

class StopException(Exception):
    """Custom exception to signal a graceful stop."""
    pass

class SteamHistoryDownloader:
    BASE_URL = "https://steamcommunity.com/market/myhistory/render/"

    def __init__(self, log_queue, stop_event, config_path: str = "config.json"):
        self.log_queue = log_queue
        self.stop_event = stop_event
        self.log_queue.put(("Initializing downloader...", "gray"))

        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
        self.cookies = self.config.get("cookies")
        if not self.cookies or not self.cookies.get("sessionid"):
            raise ValueError("Please update the 'cookies' object in 'config.json'.")
            
        self.data_dir = self.config.get("raw_data_directory", "data/raw_transactions")
        os.makedirs(self.data_dir, exist_ok=True)
        self.log_queue.put((f"Raw JSON files will be saved in: '{self.data_dir}'", "white"))
        
        self.session = self._create_session()
        self.log_queue.put(("Initialization complete.", "gray"))

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        })
        session.cookies.update(self.cookies)
        return session

    def _get_last_local_total_count(self) -> int:
        files = [os.path.join(self.data_dir, f) for f in os.listdir(self.data_dir) if f.endswith('.json')]
        if not files: return 0
        
        latest_file = max(files, key=os.path.getmtime)
        try:
            with open(latest_file, 'r') as f:
                return json.load(f).get("total_count", 0)
        except (json.JSONDecodeError, IOError, KeyError):
            self.log_queue.put((f"Warning: Could not read total_count from {latest_file}", "orange"))
            return 0

    def _fetch_batch_with_retries(self, start: int, count: int) -> dict | None:
        params = {"query": "", "start": start, "count": count}
        retries = self.config.get("max_retries", 5)
        backoff_factor = self.config.get("initial_backoff_seconds", 5)
        
        for i in range(retries):
            if self.stop_event.is_set(): raise StopException()
            try:
                self.stop_event.wait(2)
                if self.stop_event.is_set(): raise StopException()

                response = self.session.get(self.BASE_URL, params=params, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    if 'Login' in data.get('results_html', ''):
                        raise requests.exceptions.RequestException("Authentication issue: Steam is asking to log in.")
                    if data.get("success"):
                        return data
                elif response.status_code in [401, 403]:
                    raise requests.exceptions.RequestException("Authentication failed (401/403). Your cookies are likely expired.")
                
                wait_time = backoff_factor * (2 ** i)
                self.log_queue.put((f"Warning: Received status {response.status_code}. Retrying in {wait_time}s...", "orange"))
                self.stop_event.wait(wait_time)
            except requests.exceptions.RequestException as e:
                wait_time = backoff_factor * (2 ** i)
                self.log_queue.put((f"An error occurred: {e}. Retrying in {wait_time}s...", "orange"))
                self.stop_event.wait(wait_time)
        
        raise ConnectionError(f"Failed to fetch data after {retries} retries.")

    def _run_full_download(self):
        self.log_queue.put(("--- Performing Full Download / Resume ---", "cyan"))
        initial_data = self._fetch_batch_with_retries(start=0, count=1)
        if not initial_data: return
        
        total_count = initial_data.get("total_count", 0)
        if total_count == 0:
            self.log_queue.put(("No transactions found.", "white"))
            return
            
        self.log_queue.put((f"Found a total of {total_count} transactions to download.", "white"))
        
        # --- RE-INTRODUCED LOGIC: Load state to resume an interrupted download ---
        try:
            with open(STATE_FILE, 'r') as f:
                start = json.load(f).get("start", 0)
        except (IOError, json.JSONDecodeError):
            start = 0
            
        self.log_queue.put((f"Starting/Resuming download from index {start}.", "white"))
        batch_size = 100

        while start < total_count:
            if self.stop_event.is_set():
                self.log_queue.put(("Download paused by user.", "orange"))
                break # Exit the loop but don't mark as complete
            
            data = self._fetch_batch_with_retries(start=start, count=batch_size)
            if not data: break

            filename = f"transactions_{str(start).zfill(6)}.json"
            filepath = os.path.join(self.data_dir, filename)
            with open(filepath, 'w') as f: json.dump(data, f, indent=2)
            
            num_results = len(data.get('results', []))
            self.log_queue.put((f"Saved {os.path.basename(filepath)} ({start + num_results} / {total_count})", "white"))

            start += batch_size
            # Save progress after every successful batch
            with open(STATE_FILE, 'w') as f:
                json.dump({"start": start, "initial_download_complete": False}, f)
        
        # --- MODIFICATION: Only mark as complete if the loop finishes naturally ---
        if start >= total_count:
            self.log_queue.put(("\n--- Full Download Complete ---", "green"))
            with open(STATE_FILE, 'w') as f:
                json.dump({"start": start, "initial_download_complete": True}, f)

    def _run_sync(self):
        self.log_queue.put(("--- Performing Efficient Sync ---", "cyan"))
        local_total_count = self._get_last_local_total_count()
        # This check is now just for logging, not for decision making
        if local_total_count == 0:
             self.log_queue.put(("No local files found to compare against. Will fetch latest.", "orange"))

        live_data = self._fetch_batch_with_retries(start=0, count=1)
        if not live_data: return
        live_total_count = live_data.get("total_count", 0)

        self.log_queue.put((f"Local transaction count: {local_total_count}", "white"))
        self.log_queue.put((f"Live transaction count:  {live_total_count}", "white"))
        
        new_items_count = live_total_count - local_total_count
        if new_items_count <= 0:
            self.log_queue.put(("\n✅ Already up to date.", "green"))
            return
            
        self.log_queue.put((f"Found {new_items_count} new transaction(s) to sync.", "white"))
        
        batch_size = 100
        pages_to_sync = math.ceil(new_items_count / batch_size)
        self.log_queue.put((f"This will require refreshing {pages_to_sync} page(s) of data.", "white"))
        
        for i in range(pages_to_sync):
            if self.stop_event.is_set(): break
            start = i * batch_size
            data = self._fetch_batch_with_retries(start=start, count=batch_size)
            if not data:
                self.log_queue.put(("Sync halted due to an error.", "red"))
                break
            
            filename = f"transactions_{str(start).zfill(6)}.json"
            filepath = os.path.join(self.data_dir, filename)
            with open(filepath, 'w') as f: json.dump(data, f, indent=2)
            self.log_queue.put((f"Synced and saved {os.path.basename(filepath)}", "white"))
            
        self.log_queue.put(("\n--- Sync Complete ---", "green"))

    # --- MODIFICATION: The main run logic now checks the state file ---
    def run(self):
        """Determines whether to run a full download/resume or an efficient sync."""
        state = {}
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
        except (IOError, json.JSONDecodeError):
            self.log_queue.put(("No state file found, starting fresh.", "gray"))

        if not state.get("initial_download_complete", False):
            self._run_full_download()
        else:
            self._run_sync()

def run_download(log_queue, stop_event):
    try:
        downloader = SteamHistoryDownloader(log_queue, stop_event)
        downloader.run()
        return True
    except StopException:
        return True
    except Exception as e:
        log_queue.put((f"FATAL ERROR in download script: {e}", "red"))
        return False

if __name__ == "__main__":
    class DummyQueue:
        def put(self, message):
            print(f"LOG: {message[0]} (Color: {message[1]})")
            
    print("--- Running download_history.py in standalone test mode ---")
    run_download(DummyQueue(), threading.Event())
