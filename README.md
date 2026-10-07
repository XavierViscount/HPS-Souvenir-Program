# Fundraising Flower Generator Bots

This project contains two Telegram bots (Single-flower Bot and Mixed-flower Bot) designed for a school fundraising campaign. It generates customized digital flower bouquets as souvenir images.

The project runs via long polling, meaning it doesn't require a public IP, domain name, or webhook. It just needs an active internet connection.

## Prerequisites

1. **Operating System:** Windows is required out of the box because the image generation relies on the Windows Myanmar Unicode fonts (`C:\Windows\Fonts\mmrtext.ttf` or `mmrtextb.ttf`).
2. **Python:** Ensure you have **Python 3.10** or newer installed.
3. **Environment:** Keep the project structure intact. The code looks for image assets specifically inside the `assets/` and `PremadeFlowers/` folders.

## Setup Instructions

1. **Open PowerShell** in the project directory.
2. **Create a virtual environment (optional but recommended):**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```
   *(This installs `python-telegram-bot`, `Pillow`, `python-dotenv`, and `psutil`)*

4. **Configure your environment variables:**
   - Rename the provided `.env.example` file to `.env`
   - Open `.env` in a text editor.
   - Replace the placeholder tokens (`YOUR_SINGLE_BOT_TOKEN_HERE`, etc.) with your actual Telegram bot tokens from BotFather.
   - If you deployed your web apps to GitHub Pages, replace the `YOUR_GITHUB_USERNAME` placeholders with your actual GitHub username URL.

## Running the Bots

The simplest way to run the project is using the included launcher script, which starts **both** bots simultaneously:

```powershell
python run_two_bots.py
```

### How the Launcher Works:
- `run_two_bots.py` automatically loads your credentials from the `.env` file so you do not need to manually configure environment variables in your terminal.
- It automatically checks for and terminates any old "ghost" versions of the bot that might be lingering in the background from previous crashes.
- It spins up both `bot_single.py` and `bot_mixed.py` side-by-side.
- Press `Ctrl+C` in your terminal to gracefully stop both bots.

### Testing the bots:
Once running, open Telegram and send `/start` to the respective bots. You should be greeted with a WebApp button (or an inline keyboard prompt). Try making an order to verify that it generates and replies with a digital souvenir card image.

## (Optional) Running as a Background Task

If you want the bots to run continuously in the background without keeping a command window open, you can configure Windows Task Scheduler:

1. Open Task Scheduler and **Create Task**.
2. **General:** Select "Run whether user is logged on or not".
3. **Triggers:** Add an "At startup" trigger.
4. **Actions:** 
   - **Program/script:** Path to your python executable (e.g., `.\.venv\Scripts\python.exe` or global `python.exe`)
   - **Add arguments:** `run_two_bots.py`
   - **Start in:** The absolute path to this project folder.
5. Save the task.

---
**Note on tokens:** The Telegram API only allows one active polling session per token. Do not run the bots on two different computers at the same time, or Telegram will disconnect them repeatedly.