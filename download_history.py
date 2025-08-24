import requests
import json
import os
import time
import sys
import math

class SteamHistoryDownloader:
    """
    Phase 1: Fetches all Steam Market history as raw JSON files.
    - Performs a full download on the first run.
    - Performs efficient, targeted syncs on subsequent runs.
    """
    BASE_URL = "https://steamcommunity.com/market/myhistory/render/"
    STATE_FILE = "state.json" # Note: state.json is now only for the initial download.

    def __init__(self, config_path: str = "config.json"):
        """Initializes the downloader by loading configuration and setting up the session."""
        print("Initializing downloader...")
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            print(f"FATAL: Configuration file '{config_path}' not found.")
            sys.exit(1)
            
        # UPDATED: Validate the new cookies structure
        self.cookies = self.config.get("cookies")
        if not self.cookies or "YOUR_SESSIONID_COOKIE" in self.cookies.get("sessionid", ""):
            print("FATAL: Please update the 'cookies' object in 'config.json' with your actual Steam cookies.")
            sys.exit(1)
            
        self.data_dir = self.config.get("raw_data_directory", "data/raw_transactions")
        os.makedirs(self.data_dir, exist_ok=True)
        print(f"Raw JSON files will be saved in: '{self.data_dir}'")
        
        self.session = self._create_session()
        print("Initialization complete.")

    def _create_session(self) -> requests.Session:
        """Creates a requests session with necessary cookies and headers."""
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        })
        # UPDATED: Load all cookies from the config at once
        session.cookies.update(self.cookies)
        return session

    def _get_last_local_total_count(self) -> int:
        """Finds the last downloaded file and reads its 'total_count' value."""
        files = [os.path.join(self.data_dir, f) for f in os.listdir(self.data_dir) if f.endswith('.json')]
        if not files:
            return 0
        
        latest_file = max(files, key=os.path.getmtime)
        
        try:
            with open(latest_file, 'r') as f:
                data = json.load(f)
                return data.get("total_count", 0)
        except (json.JSONDecodeError, IOError, KeyError):
            print(f"Warning: Could not read total_count from the last file: {latest_file}")
            return 0

    def _fetch_batch_with_retries(self, start: int, count: int) -> dict | None:
        """Fetches a single batch of data, handling retries with exponential backoff."""
        params = {"query": "", "start": start, "count": count}
        retries = self.config.get("max_retries", 5)
        backoff_factor = self.config.get("initial_backoff_seconds", 5)
        
        for i in range(retries):
            try:
                time.sleep(2)
                response = self.session.get(self.BASE_URL, params=params, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    if 'Login' in data.get('results_html', ''):
                        raise requests.exceptions.RequestException("Authentication issue: Steam is asking to log in.")
                    if data.get("success"):
                        return data
                elif response.status_code in [401, 403]:
                    print("FATAL: Authentication failed (401/403). Your cookies are likely expired.")
                    return None
                elif response.status_code == 429 or response.status_code >= 500:
                    wait_time = backoff_factor * (2 ** i)
                    print(f"Warning: Received status {response.status_code}. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"Error: Received unexpected status code {response.status_code}. Aborting.")
                    return None
            except requests.exceptions.RequestException as e:
                wait_time = backoff_factor * (2 ** i)
                print(f"An error occurred: {e}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        print(f"FATAL: Failed to fetch data after {retries} retries.")
        return None

    def _run_full_download(self):
        """Performs a full download of all transactions, for the first run."""
        print("--- Performing First-Time Full Download ---")
        
        initial_data = self._fetch_batch_with_retries(start=0, count=1)
        if not initial_data: return
        
        total_count = initial_data.get("total_count", 0)
        if total_count == 0:
            print("No transactions found.")
            return
            
        print(f"Found a total of {total_count} transactions to download.")
        
        # Load state for resuming an interrupted initial download
        try:
            with open(self.STATE_FILE, 'r') as f: start = json.load(f).get("start", 0)
        except (IOError, json.JSONDecodeError):
            start = 0
            
        print(f"Starting download from index {start}.")
        batch_size = 100

        while start < total_count:
            data = self._fetch_batch_with_retries(start=start, count=batch_size)
            if not data: break

            filename = f"transactions_{str(start).zfill(6)}.json"
            filepath = os.path.join(self.data_dir, filename)
            with open(filepath, 'w') as f: json.dump(data, f, indent=2)
            print(f"Saved {filepath}")

            start += batch_size
            with open(self.STATE_FILE, 'w') as f: json.dump({"start": start}, f)
        
        print("\n--- Full Download Complete ---")

    def _run_sync(self):
        """Performs an efficient sync of only new transactions."""
        print("--- Performing Efficient Sync ---")
        
        local_total_count = self._get_last_local_total_count()
        if local_total_count == 0:
            print("Warning: Could not determine local state. Re-running full download.")
            self._run_full_download()
            return

        live_data = self._fetch_batch_with_retries(start=0, count=1)
        if not live_data: return
        live_total_count = live_data.get("total_count", 0)

        print(f"Local transaction count: {local_total_count}")
        print(f"Live transaction count:  {live_total_count}")
        
        new_items_count = live_total_count - local_total_count
        
        if new_items_count <= 0:
            print("\n✅ Already up to date.")
            return
            
        print(f"Found {new_items_count} new transaction(s) to sync.")
        
        batch_size = 100
        pages_to_sync = math.ceil(new_items_count / batch_size)
        print(f"This will require refreshing {pages_to_sync} page(s) of data.")
        
        for i in range(pages_to_sync):
            start = i * batch_size
            data = self._fetch_batch_with_retries(start=start, count=batch_size)
            if not data:
                print("Sync halted due to an error.")
                break
            
            filename = f"transactions_{str(start).zfill(6)}.json"
            filepath = os.path.join(self.data_dir, filename)
            with open(filepath, 'w') as f: json.dump(data, f, indent=2)
            print(f"Synced and saved {filepath}")
            
        print("\n--- Sync Complete ---")

    def run(self):
        """Determines whether to run a full download or an efficient sync."""
        if not os.listdir(self.data_dir):
            self._run_full_download()
        else:
            self._run_sync()

if __name__ == "__main__":
    downloader = SteamHistoryDownloader()
    downloader.run()
