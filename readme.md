# Steam Market History Exporter

A two-phase Python script that downloads your complete Steam Community Market transaction history and processes it into a clean, organized Excel file for profit/loss analysis.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)


# If you are having trouble setting up the project, here's an even simpler [setup guide](https://github.com/rdrishabh38/steam_market_history_tracker/blob/master/SETUP_GUIDE.md) for you


## Overview

This project is designed to overcome the limitations of viewing and analyzing your transaction history on the Steam website. It automates the entire process of fetching and organizing your market data. The process is split into two distinct phases for robustness and flexibility:

1.  **Phase 1: Ingestion (`download_history.py`)**
    * Connects to the Steam API using your browser's session cookies.
    * Performs a full download of your entire transaction history on the first run.
    * On subsequent runs, it performs a highly efficient sync to fetch only new transactions.
    * Handles API rate limits with exponential backoff and gracefully manages session cookie expiration.
    * Saves all raw data as JSON files, creating a local, offline-first backup.

2.  **Phase 2: Processing (`process_data.py`)**
    * Reads the locally saved raw JSON files.
    * Parses the complex HTML embedded in the API responses to extract key data.
    * Structures the data into a clean, readable format.
    * Exports the final dataset to an `.xlsx` file with columns for Date, Item Name, Type (Purchase/Sale), and Price.

## Setup and Installation

Follow these steps to get the project running on your local machine.

### 1. Clone the Repository

```bash
git clone https://github.com/rdrishabh38/steam_market_history_tracker.git
cd steam_market_history_tracker
```

### 2. Install Dependencies

It's recommended to use a virtual environment. The project requires a few Python libraries. You can install them using pip:

```bash
pip install -r requirements.txt
```

### 3. Get Your Cookies:

The most reliable method is using a browser extension like Cookie-Editor for Chrome or Firefox.

* Log in to steamcommunity.com in your browser.

* If you use Steam's Parental Pin (Family View), you must unlock it first by entering your PIN.

* Navigate to your Market History page.

* Click the Cookie-Editor extension icon and copy the values for sessionid, steamLoginSecure, browserid, steamCountry and steamparental into your config.json file.


### 4. Configure the Application

Before running the scripts, you must provide your Steam session cookies for authentication.

* Navigate to the file in the project's root directory named ```config.json```.

* Update the fields in the JSON file as per your requirement:

    ```bash
    {
        "cookies": 
            {
            "sessionid": "ENTER_YOUR_SESSIONID_VALUE_HERE",
            "steamLoginSecure": "ENTER_YOUR_SESSIONID_VALUE_HERE",
            "browserid": "ENTER_YOUR_BROWSERID_VALUE_HERE",
            "steamCountry": "ENTER_YOUR_STEAMCOUNTRY_VALUE_HERE",
            "steamparental": "ENTER_YOUR_STEAM_PARENTAL_VALUE_HERE"
            },
        "raw_data_directory": "data/raw_transactions",
        "max_retries": 5,
        "initial_backoff_seconds": 5,
        "output_file_name": "steam_market_history.xlsx"
    }

## ⚠️ Important Security Warning
# Your steamLoginSecure cookie is like a temporary password for your account. Never share this cookie with anyone. If someone gets this value, they can gain access to your Steam account. Treat it with the same level of security as your actual password

## How to Run

The project must be run in two phases, in order.

### Phase 1: Download Transaction History

This script connects to Steam to download your data. Run it first.

```bash
python download_history.py
```

* On the **first run**, this will download your entire transaction history, which may take some time depending on its size.
* On **subsequent runs**, it will quickly sync only the new transactions made since the last run.

### Phase 2: Process Data into Excel

After downloading the data, run this script to generate your spreadsheet.

```bash
python process_data.py
```

* This script works entirely offline using the JSON files downloaded in Phase 1.
* It will create a file named `steam_market_history.xlsx` (or as configured) in the project's root directory. You can re-run this script at any time without re-downloading data.

---
## Project Structure

```
.
├── data/
│   └── raw_transactions/   # Stores raw JSON files from Phase 1
├── download_history.py     # Phase 1: Downloader script
├── process_data.py         # Phase 2: Processor script
├── config.json             # User configuration (cookies, paths)
├── state.json              # Tracks progress of the initial download
└── steam_market_history.xlsx # Final Excel output file
```

---
## Troubleshooting

### `FATAL: Authentication failed (401/403)`

This is the most common error and means your session cookies are invalid or have expired.

**Solution:**
1.  Log out of `steamcommunity.com` in your browser.
2.  Log back in to generate a fresh session.
3.  If applicable, unlock Family View with your PIN.
4.  Copy the new cookie values and update your `config.json` file.
5.  Run the script again.


##  Known Issues

* Since history results do not usually include the year of the date, the program must make a best guess for the year. If you have gaps larger than a year in your history results you may experience issues. This issue may or may not be resolved in the future.

* Any refunded transactions will persist if they were not refunded at the time of loading. There is no way to remove them from your results at this point unless you clear your entire listing data and reload all the transactions again.

* Pending transactions are treated as completed transactions. More than 99% of the time these are completed successfully. In the event they don't go through, please delete all the historical JSON files from ```Phase 1``` and re-execute the entire process for accuracy.

---
##  License

This project is protected under the [GPL-3.0 license](https://choosealicense.com/licenses) License. For more details, refer to the [LICENSE](https://github.com/rdrishabh38/steam_market_history_tracker/blob/master/LICENSE.md) file.
