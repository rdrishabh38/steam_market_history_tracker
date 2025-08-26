# process_data.py

import pandas as pd
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime
import threading # For testing

# MODIFICATION: Add the StopException class here as well
class StopException(Exception):
    """Custom exception to signal a graceful stop."""
    pass

class DataProcessor:
    # MODIFICATION: Accept stop_event in __init__
    def __init__(self, log_queue, stop_event, config_path: str = "config.json"):
        self.log_queue = log_queue
        self.stop_event = stop_event # Store the stop event
        # ... (rest of __init__ is unchanged) ...
        self.log_queue.put(("Initializing data processor...", "gray"))
        with open(config_path, 'r') as f:
            config = json.load(f)
        self.data_dir = config["raw_data_directory"]
        self.output_file = config["output_file_name"]
        self.log_queue.put(("Initialization complete.", "gray"))

    # ... (_parse_html_results and _add_years_to_dates methods are unchanged) ...
    def _parse_html_results(self, html_content: str) -> list:
        if not html_content.strip(): return []
        soup = BeautifulSoup(html_content, 'html.parser')
        rows = soup.find_all("div", class_="market_listing_row")
        transactions = []
        for row in rows:
            gain_loss_div = row.find("div", class_="market_listing_gainorloss")
            action_char = gain_loss_div.text.strip() if gain_loss_div else '?'
            item_name_span = row.find("span", class_="market_listing_item_name")
            price_span = row.find("span", class_="market_listing_price")
            price_str = price_span.text.strip() if price_span else "0.0"
            price_cleaned = re.sub(r'[^\d.]', '', price_str)
            try: price = float(price_cleaned)
            except (ValueError, TypeError): price = 0.0
            date_divs = row.find_all("div", class_="market_listing_listed_date")
            transactions.append({ "Acted On Date": date_divs[0].text.strip() if len(date_divs) > 0 else "N/A", "Listed On Date": date_divs[1].text.strip() if len(date_divs) > 1 else "N/A", "Item Name": item_name_span.text.strip() if item_name_span else "N/A", "Type": "Purchase" if action_char == '+' else "Sale", "Price": price })
        return transactions

    def _add_years_to_dates(self, transactions: list) -> list:
        self.log_queue.put(("Inferring year for each transaction date...", "white"))
        current_acted_on_year = datetime.now().year
        last_acted_on_month = 13
        month_map = { 'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12 }
        for transaction in transactions:
            acted_on_str = transaction.get("Acted On Date", "")
            if not acted_on_str or acted_on_str == "N/A" or len(acted_on_str.split()) < 2:
                transaction["inferred_acted_on_year"] = None; continue
            acted_on_month_str = acted_on_str.split(' ')[1]
            current_acted_on_month = month_map.get(acted_on_month_str)
            if current_acted_on_month is None:
                transaction["inferred_acted_on_year"] = None; continue
            if current_acted_on_month > last_acted_on_month:
                current_acted_on_year -= 1
            transaction["inferred_acted_on_year"] = current_acted_on_year
            last_acted_on_month = current_acted_on_month
        for transaction in transactions:
            transaction["Sold/Purchased Date"] = transaction.get("Acted On Date", "N/A")
            transaction["Listed Date"] = transaction.get("Listed On Date", "N/A")
            acted_on_year = transaction.get("inferred_acted_on_year")
            if acted_on_year is not None:
                acted_on_str = transaction["Acted On Date"]
                listed_on_str = transaction["Listed On Date"]
                transaction["Sold/Purchased Date"] = f"{acted_on_str}, {acted_on_year}"
                if listed_on_str != "N/A" and len(acted_on_str.split()) > 1 and len(listed_on_str.split()) > 1:
                    acted_on_month = month_map.get(acted_on_str.split(' ')[1])
                    listed_on_month = month_map.get(listed_on_str.split(' ')[1])
                    if acted_on_month and listed_on_month:
                        listed_on_year = acted_on_year - 1 if listed_on_month > acted_on_month else acted_on_year
                        transaction["Listed Date"] = f"{listed_on_str}, {listed_on_year}"
            del transaction["inferred_acted_on_year"]
            del transaction["Acted On Date"]
            del transaction["Listed On Date"]
        return transactions

    def run(self):
        self.log_queue.put((f"--- Processing Data from '{self.data_dir}' ---", "cyan"))
        
        if not os.path.exists(self.data_dir):
            raise FileNotFoundError(f"The data directory '{self.data_dir}' does not exist.")

        files = [f for f in os.listdir(self.data_dir) if f.endswith('.json')]
        if not files:
            self.log_queue.put(("No data files found to process.", "orange"))
            return
        files.sort(key=lambda x: int(re.search(r'\d+', x).group()))
        self.log_queue.put((f"Found {len(files)} data files to process.", "white"))

        all_transactions = []
        for filename in files:
            # MODIFICATION: Check for stop signal in main loop
            if self.stop_event.is_set(): raise StopException()
            # ... (rest of loop is unchanged) ...
            filepath = os.path.join(self.data_dir, filename)
            try:
                with open(filepath, 'r') as f: data = json.load(f)
                parsed_data = self._parse_html_results(data.get("results_html", ""))
                all_transactions.extend(parsed_data)
            except (json.JSONDecodeError, IOError) as e:
                self.log_queue.put((f"Warning: Could not parse {filename}. Error: {e}", "orange"))
        
        # Check if stop was requested during the loop
        if self.stop_event.is_set(): raise StopException()

        self.log_queue.put((f"Successfully parsed {len(all_transactions)} transactions.", "white"))
        if not all_transactions:
            self.log_queue.put(("No transactions were parsed. Output file will not be created.", "orange"))
            return
        
        processed_transactions = self._add_years_to_dates(all_transactions)
        self.log_queue.put((f"Saving all transactions to '{self.output_file}'...", "white"))
        df = pd.DataFrame(processed_transactions)
        df = df[["Sold/Purchased Date", "Listed Date", "Item Name", "Type", "Price"]]
        df.to_excel(self.output_file, index=False)
        self.log_queue.put((f"\n--- Processing Complete ---", "green"))
        self.log_queue.put((f"✅ Successfully created '{self.output_file}'", "green"))


# MODIFICATION: Update the main function signature and add StopException handling
def run_processing(log_queue, stop_event):
    try:
        processor = DataProcessor(log_queue, stop_event)
        processor.run()
        return True
    except StopException:
        # This is not an error, just a requested stop
        return True
    except Exception as e:
        log_queue.put((f"FATAL ERROR in processing script: {e}", "red"))
        return False

# This block allows you to test the script directly
if __name__ == "__main__":
    class DummyQueue:
        def put(self, message):
            print(f"LOG: {message[0]} (Color: {message[1]})")

    print("--- Running process_data.py in standalone test mode ---")
    run_processing(DummyQueue(), threading.Event())