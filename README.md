# Tjk-Bot

Python bot that scrapes horse racing results from TJK (Türkiye Jokey Kulübü).

## Features

- ✅ Scrape daily race results
- ✅ Extract horse rankings and times
- ✅ Get jockey and trainer information
- ✅ Export data to CSV/Excel
- ✅ Automated data collection

## Requirements

- Python 3.8+
- Required packages in `requirements.txt`

## Installation

```bash
# Clone the repository
git clone https://github.com/canekremdura/Tjk-Bot.git
cd Tjk-Bot

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Run the bot
python tjk_bot.py

# Or with custom date
python tjk_bot.py --date "2024-01-15"
```

## Output

The bot exports data in the following format:

| Race No | Horse Name | Jockey | Rank | Time |
|---------|------------|--------|------|------|
| 1 | Horse A | Jockey X | 1 | 1:23.45 |

## Disclaimer

This bot is for educational purposes only. Please respect the website's terms of service and robots.txt file.

## License

MIT License

## Author

**Can Ekrem Dura**

[GitHub Profile](https://github.com/canekremdura)

---

*Check out my other projects:*
- [Mackolik-Bot](https://github.com/canekremdura/Mackolik-Bot) - Football match data scraper
- [csv-to-json-cli](https://github.com/canekremdura/csv-to-json-cli) - CSV to JSON converter
- [wp-custom-variation-swatches](https://github.com/canekremdura/wp-custom-variation-swatches) - WooCommerce swatches
