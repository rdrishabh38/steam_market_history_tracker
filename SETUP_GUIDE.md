# Setup Guide: Your Steam Market Helper

Let's get your Steam Market helper ready! We'll do this in a few easy steps, like building with LEGOs. Just follow along, and you'll have your Excel file in no time.

---
## Part 1: Get the Main Tool (Install Python)

First, we need to install Python, which is the language our helper speaks.

1.  **Go to the Python Website:** Click this link to go to the official Python download page: [python.org/downloads](https://www.python.org/downloads/)

2.  **Download Python:** Click the big yellow button that says "Download Python". It will download the installer file.
    

3.  **Run the Installer (Very Important Step!):**
    * Open the file you just downloaded.
    * A new window will pop up. At the bottom of this window, you **must** check the box that says **`Add python.exe to PATH`**. This is like putting your tool in the right toolbox so the computer can find it later.
    * After checking the box, click **`Install Now`**.
    

---
## Part 2: Get the Helper's Files (The Project)

Now, let's get the files for our helper program.

1.  **Go to the Project Page:** Go to the project's GitHub page - [Steam Market History Tracker](https://github.com/rdrishabh38/steam_market_history_tracker)
    

2.  **Download the Files:** Click the green **`< > Code`** button, then click **`Download ZIP`**. This will save all the project files in a single zip folder.
    

3.  **Unzip the Folder:**
    * Go to your `Downloads` folder and find the zip file you just downloaded.
    * Right-click on it and choose **`Extract All...`**.
    
    * A good place to extract it is your **Desktop**. Click `Extract`. You will now have a normal folder on your Desktop with all the project files.

---
## Part 3: Give the Helper Your Secret Keys (Configure Cookies)

The helper needs your "secret handshake" to log in to Steam for you. These are called cookies.

1.  **Get a Cookie Tool:** We'll use a simple and safe browser extension. Go to the Chrome Web Store and add **Cookie-Editor** to your browser: [Cookie-Editor Extension](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm).
    

2.  **Log in to Steam:** In Chrome, log in to `steamcommunity.com`. If you have a Parental Pin, unlock it now.

3.  **Copy Your Keys:**
    * Go to your [Market History page](https://steamcommunity.com/market/myhistory).
    * Click the **Cookie-Editor** icon (🍪) in your browser's toolbar.
    * A list will appear. Find the cookie named **`sessionid`**, and copy its "Value".
    

4.  **Paste Your Keys:**
    * Go to the project folder on your Desktop and open the `config.json` file with Notepad.
    * Paste the value you copied next to `"sessionid":`.
    * Repeat this process for the other three required cookies: `steamLoginSecure`, `browserid`, and `steamCountry`.
    
    
5.  **Save the file** and close Notepad.

---
## Part 4: Teach the Helper New Tricks (Install Libraries)

Our helper needs some extra tools to work with Excel files.

1.  **Open the Command Window:**
    * Go into the project folder on your Desktop.
    * Click in the address bar at the top of the window.
    * Delete the text there, type **`cmd`**, and press **Enter**. A black command window will pop up, already in the right folder!
    

2.  **Install the Tools:** Copy the command below, paste it into the black window, and press **Enter**.

    ```
    pip install -r requirements.txt
    ```
    Wait for it to finish installing.
    

---
## Part 5: Run the Helper! 🎉

You're all set! It's time to run the program.

1.  **Run the Downloader (Phase 1):** In the same black command window, type or paste the following and press **Enter**:

    ```
    python download_history.py
    ```
    This will start downloading all your transactions. If you have a lot, this might take a while.
    

2.  **Create the Excel File (Phase 2):** Once the downloader is finished, type or paste the next command and press **Enter**:

    ```
    python process_data.py
    ```
    This will read all the downloaded data and create your Excel file.
    

3.  **Find Your File:** Look inside your project folder. You will now see a file named **`steam_market_history.xlsx`**. You're done!
