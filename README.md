# 🏇 Tjk-Bot

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Selenium](https://img.shields.io/badge/Selenium-Automation-green.svg)
![Pandas](https://img.shields.io/badge/Pandas-Data_Analysis-yellow.svg)
![License](https://img.shields.io/badge/License-MIT-purple.svg)

An automated Python scraper designed to extract comprehensive horse racing results, schedules, and detailed statistics directly from TJK (Türkiye Jokey Kulübü) website.

## 🌟 Features

*   **Daily Race Results:** Scrapes detailed results for all races on a given day.
*   **Horse & Jockey Stats:** Extracts performance metrics, odds, and placement data.
*   **Export Options:** Saves the scraped data cleanly into structured formats (`.csv`, `.json`).
*   **Undetected:** Utilizes `undetected_chromedriver` to ensure stable and uninterrupted scraping sessions.

## 🛠️ Prerequisites

*   Python 3.8 or higher
*   Google Chrome installed on your machine

## ⚙️ Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/canekremdura/Tjk-Bot.git
    cd Tjk-Bot
    ```

2.  **Set up a virtual environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use: venv\Scripts\activate
    ```

3.  **Install the required packages:**
    ```bash
    pip install beautifulsoup4 pandas selenium undetected-chromedriver
    ```

## 🚀 Usage

Execute the scraper via the command line:

```bash
python scraper.py
```

*Upon execution, the bot will fetch the latest racing data. Check the script file to modify parameters like specific dates or tracks.*

## 📁 Output Data

By default, the scraped data will be parsed and saved into the current working directory as:
*   `tjk_data_[DATE].csv`
*   `tjk_data_[DATE].json`

## ⚠️ Disclaimer

This tool is built for educational and analytical purposes. Please respect the website's Terms of Service and `robots.txt`. Do not hammer the servers with excessive requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
