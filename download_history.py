import requests
import json
import os
import time
import sys

class SteamHistoryDownloader:
    """
    Phase 1: Fetches all Steam Market history as raw JSON files.
    Handles rate limiting, session expiry, and resumes from the last run.
    """
    BASE_URL = "https://steamcommunity.com/market/myhistory/render/"
    STATE_FILE = "state.json"

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

    def _load_state(self) -> int:
        """Loads the starting index from the state file."""
        if os.path.exists(self.STATE_FILE):
            try:
                with open(self.STATE_FILE, 'r') as f:
                    state = json.load(f)
                    return state.get("start", 0)
            except (json.JSONDecodeError, IOError):
                return 0
        return 0

    def _save_state(self, start: int):
        """Saves the next starting index to the state file."""
        with open(self.STATE_FILE, 'w') as f:
            json.dump({"start": start}, f)

    def _fetch_batch_with_retries(self, start: int, count: int) -> dict | None:
        """
        Fetches a single batch of data, handling retries with exponential backoff.
        """
        params = {"query": "", "start": start, "count": count}
        retries = self.config.get("max_retries", 5)
        backoff_factor = self.config.get("initial_backoff_seconds", 5)
        
        for i in range(retries):
            try:
                time.sleep(2)
                response = self.session.get(self.BASE_URL, params=params, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    # UPDATED: Check for the login message in the response
                    if 'Login' in data.get('results_html', ''):
                        print("Warning: Steam is asking to log in. Your cookies may be incorrect or expired. Retrying...")
                        # This will trigger the backoff and retry logic
                        raise requests.exceptions.RequestException("Authentication issue detected in response HTML.")
                    if data.get("success"):
                        return data
                    else:
                        print(f"Warning: API call successful but 'success' is false. Retrying...")

                elif response.status_code in [401, 403]:
                    print(f"response is - {response.text}")
                    print("FATAL: Authentication failed (401/403). Your cookies are likely expired. Please update config.json.")
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

        print(f"FATAL: Failed to fetch data after {retries} retries. Aborting.")
        return None

    def run(self):
        """Main method to run the entire data ingestion process."""
        print("--- Starting Phase 1: Data Ingestion ---")
        
        print("Fetching total transaction count...")
        initial_data = self._fetch_batch_with_retries(start=0, count=1)
        if not initial_data:
            print("Could not fetch initial data. Exiting.")
            return
            
        total_count = initial_data.get("total_count", 0)
        if total_count == 0:
            print("No transactions found in your history. This might be due to incorrect cookies.")
            return
            
        print(f"Found a total of {total_count} transactions.")
        
        start = self._load_state()
        print(f"Resuming download from index {start}.")
        
        batch_size = 100

        while start < total_count:
            print(f"Fetching records {start} to {start + batch_size} of {total_count}...")
            
            data = self._fetch_batch_with_retries(start=start, count=batch_size)

            if not data:
                print("Download process halted due to unrecoverable error.")
                break

            filename = f"transactions_{str(start).zfill(6)}.json"
            filepath = os.path.join(self.data_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"Successfully saved {filepath}")

            start += batch_size
            self._save_state(start)

        print("\n--- Phase 1: Data Ingestion Complete ---")
        print(f"All available raw JSON files are saved in the '{self.data_dir}' directory.")


if __name__ == "__main__":
    downloader = SteamHistoryDownloader()
    downloader.run()
