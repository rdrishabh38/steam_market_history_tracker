import pandas as pd
from bs4 import BeautifulSoup
import json
import os
import re

class DataProcessor:
    """
    Phase 2: Reads raw JSON files, parses transaction data from the
    embedded HTML, and saves it to a single Excel file.
    """
    def __init__(self, config_path: str = "config.json"):
        """Initializes the processor by loading configuration."""
        print("Initializing data processor...")
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            self.data_dir = config["raw_data_directory"]
            self.output_file = config["output_file_name"]
        except (FileNotFoundError, KeyError) as e:
            print(f"FATAL: Could not read configuration from '{config_path}'. Error: {e}")
            exit(1)
        print("Initialization complete.")

    def _parse_html_results(self, html_content: str) -> list:
        """
        Parses the 'results_html' string to extract structured transaction data.
        """
        if not html_content.strip():
            return []

        soup = BeautifulSoup(html_content, 'html.parser')
        rows = soup.find_all("div", class_="market_listing_row")
        transactions = []

        for row in rows:
            # Get unique Listing ID
            listing_id = row.get('id', 'N/A')

            # Determine transaction type (+ for buy, - for sell)
            gain_loss_div = row.find("div", class_="market_listing_gainorloss")
            action_char = gain_loss_div.text.strip() if gain_loss_div else '?'
            transaction_type = "Purchase" if action_char == '+' else "Sale"

            # Get item name
            item_name_span = row.find("span", class_="market_listing_item_name")
            item_name = item_name_span.text.strip() if item_name_span else "N/A"

            # Get price, clean it, and convert to a number
            price_span = row.find("span", class_="market_listing_price")
            price_str = price_span.text.strip() if price_span else "0.0"
            # Remove currency symbols, commas, and handle different formats
            price_cleaned = re.sub(r'[^\d.]', '', price_str)
            try:
                price = float(price_cleaned)
            except (ValueError, TypeError):
                price = 0.0

            # Get "Acted On" Date
            date_divs = row.find_all("div", class_="market_listing_listed_date")
            acted_on_date = date_divs[0].text.strip() if len(date_divs) > 0 else "N/A"
            
            transactions.append({
                "Listing ID": listing_id,
                "Date": acted_on_date,
                "Item Name": item_name,
                "Type": transaction_type,
                "Price": price
            })
            
        return transactions

    def run(self):
        """
        Main method to discover, read, parse, and save all transaction data.
        """
        print(f"--- Starting Phase 2: Processing Data from '{self.data_dir}' ---")

        # 1. Discover and sort all raw JSON files
        try:
            files = [f for f in os.listdir(self.data_dir) if f.endswith('.json')]
            # Sort files numerically based on the number in the filename
            files.sort(key=lambda x: int(re.search(r'\d+', x).group()))
        except FileNotFoundError:
            print(f"FATAL: The data directory '{self.data_dir}' does not exist. Please run the downloader first.")
            return

        if not files:
            print("No data files found to process.")
            return

        print(f"Found {len(files)} data files to process.")

        # 2. Loop through files and parse data
        all_transactions = []
        for filename in files:
            filepath = os.path.join(self.data_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                html_content = data.get("results_html", "")
                parsed_data = self._parse_html_results(html_content)
                all_transactions.extend(parsed_data)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not read or parse {filename}. Error: {e}")
        
        print(f"Successfully parsed a total of {len(all_transactions)} transactions.")

        if not all_transactions:
            print("No transactions were parsed. The output file will not be created.")
            return

        # 3. Save all data to a single Excel file
        print(f"Saving all transactions to '{self.output_file}'...")
        df = pd.DataFrame(all_transactions)
        
        # Reorder columns for better readability
        df = df[["Date", "Item Name", "Type", "Price", "Listing ID"]]
        
        df.to_excel(self.output_file, index=False)
        
        print(f"\n--- Phase 2 Complete ---")
        print(f"✅ Successfully created '{self.output_file}'.")

if __name__ == "__main__":
    processor = DataProcessor()
    processor.run()
