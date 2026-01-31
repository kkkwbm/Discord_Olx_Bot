# 🛒 Discord OLX Bot

An automated monitoring tool that brings OLX marketplace updates directly to your Discord server. Perfect for tracking specific items or categories with instant alerts.

## ✨ Features
* **Smart Scraping:** Efficiently parses OLX search results for new entries.
* **Subscription System:** Users can subscribe to specific search queries.
* **Database Integration:** Maintains an `olx_offers.db` to track history and `olx_subscriptions.db` for user preferences.
* **Reliable Persistence:** Handles state across restarts using SQLite and JSON caching.

## 🛠️ Technology Stack
* **Language:** Python 3.x
* **Core:** `discord.py`
* **Scraping:** `requests`, `BeautifulSoup4`
* **Storage:** SQLite & JSON

## 🚀 Setup
1. **Clone:** `git clone https://github.com/kkkwbm/Discord_Olx_Bot.git`
2. **Dependencies:** `pip install -r requirements.txt`
3. **Security:** Add your `DISCORD_TOKEN` to your environment variables (do not hardcode it in `main.py`).
4. **Execution:** `python main.py`
