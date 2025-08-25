import pandas as pd
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime

class DataProcessor:
    """
    Phase 2: Reads raw JSON files, parses detailed transaction data,
    infers the correct year for both list and sale dates, and saves
    it to a single Excel file.
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
            gain_loss_div = row.find("div", class_="market_listing_gainorloss")
            action_char = gain_loss_div.text.strip() if gain_loss_div else '?'
            transaction_type = "Purchase" if action_char == '+' else "Sale"
            
            item_name_span = row.find("span", class_="market_listing_item_name")
            item_name = item_name_span.text.strip() if item_name_span else "N/A"
            
            price_span = row.find("span", class_="market_listing_price")
            price_str = price_span.text.strip() if price_span else "0.0"
            price_cleaned = re.sub(r'[^\d.]', '', price_str)
            try:
                price = float(price_cleaned)
            except (ValueError, TypeError):
                price = 0.0
            
            date_divs = row.find_all("div", class_="market_listing_listed_date")
            acted_on_date = date_divs[0].text.strip() if len(date_divs) > 0 else "N/A"
            listed_on_date = date_divs[1].text.strip() if len(date_divs) > 1 else "N/A"
            
            transactions.append({
                "Acted On Date": acted_on_date,
                "Listed On Date": listed_on_date,
                "Item Name": item_name,
                "Type": transaction_type,
                "Price": price
            })
            
        return transactions

    def _add_years_to_dates(self, transactions: list) -> list:
        """
        Infers the correct year for both 'Acted On' and 'Listed On' dates.
        """
        print("Inferring year for each transaction date...")
        current_acted_on_year = datetime.now().year
        last_acted_on_month = 13

        month_map = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
        }

        # First pass: Determine the correct year for the 'Acted On Date'
        for transaction in transactions:
            acted_on_str = transaction.get("Acted On Date", "")
            if not acted_on_str or acted_on_str == "N/A" or len(acted_on_str.split()) < 2:
                transaction["inferred_acted_on_year"] = None
                continue

            # FIXED: Get the month from the second element of the split string
            acted_on_month_str = acted_on_str.split(' ')[1]
            current_acted_on_month = month_map.get(acted_on_month_str)
            
            if current_acted_on_month is None:
                transaction["inferred_acted_on_year"] = None
                continue

            if current_acted_on_month > last_acted_on_month:
                current_acted_on_year -= 1
            
            transaction["inferred_acted_on_year"] = current_acted_on_year
            last_acted_on_month = current_acted_on_month

        # Second pass: Use the correct 'Acted On' year to infer the 'Listed On' year
        for transaction in transactions:
            transaction["Sold/Purchased Date"] = transaction.get("Acted On Date", "N/A")
            transaction["Listed Date"] = transaction.get("Listed On Date", "N/A")
            
            acted_on_year = transaction.get("inferred_acted_on_year")
            
            if acted_on_year is not None:
                acted_on_str = transaction["Acted On Date"]
                listed_on_str = transaction["Listed On Date"]
                
                transaction["Sold/Purchased Date"] = f"{acted_on_str}, {acted_on_year}"
                
                if listed_on_str != "N/A" and len(acted_on_str.split()) > 1 and len(listed_on_str.split()) > 1:
                    # FIXED: Get months from the second element
                    acted_on_month = month_map.get(acted_on_str.split(' ')[1])
                    listed_on_month = month_map.get(listed_on_str.split(' ')[1])

                    if acted_on_month and listed_on_month:
                        listed_on_year = acted_on_year - 1 if listed_on_month > acted_on_month else acted_on_year
                        transaction["Listed Date"] = f"{listed_on_str}, {listed_on_year}"
            
            if "inferred_acted_on_year" in transaction:
                del transaction["inferred_acted_on_year"]
            if "Acted On Date" in transaction:
                del transaction["Acted On Date"]
            if "Listed On Date" in transaction:
                del transaction["Listed On Date"]

        return transactions

    def run(self):
        """
        Main method to discover, read, parse, and save all transaction data.
        """
        print(f"--- Starting Phase 2: Processing Data from '{self.data_dir}' ---")

        try:
            files = [f for f in os.listdir(self.data_dir) if f.endswith('.json')]
            files.sort(key=lambda x: int(re.search(r'\d+', x).group()))
        except FileNotFoundError:
            print(f"FATAL: The data directory '{self.data_dir}' does not exist. Please run the downloader first.")
            return

        if not files:
            print("No data files found to process.")
            return

        print(f"Found {len(files)} data files to process.")

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
        
        processed_transactions = self._add_years_to_dates(all_transactions)
        
        print(f"Saving all transactions to '{self.output_file}'...")
        df = pd.DataFrame(processed_transactions)
        
        df = df[["Sold/Purchased Date", "Listed Date", "Item Name", "Type", "Price"]]
        
        df.to_excel(self.output_file, index=False)
        
        print(f"\n--- Phase 2 Complete ---")
        print(f"✅ Successfully created '{self.output_file}' with complete dates.")

if __name__ == "__main__":
    processor = DataProcessor()
    processor.run()
