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

*(Note: `requirements.txt` installs `python-telegram-bot` and `Pillow` (PIL))*

## Running the Bots

The simplest way to run the project is using the included launcher script, which starts **both** bots simultaneously:

```powershell
python run_two_bots.py
```

### How the Launcher Works:
- `run_two_bots.py` automatically injects the necessary bot tokens into the environment so you do not need to manually configure them.
- It spins up both `bot_single.py` and `bot_mixed.py` in the background.
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