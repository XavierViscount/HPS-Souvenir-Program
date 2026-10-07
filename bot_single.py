import logging
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()
from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.error import NetworkError
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bouquet_generator import (
    FLOWER_CATALOGUE,
    generate_single_bouquet,
    to_burmese_num,
)

BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN_SINGLE", "YOUR_SINGLE_BOT_TOKEN_HERE").strip()
WEB_APP_URL: str = os.environ.get(
    "TELEGRAM_WEB_APP_URL_SINGLE", 
    "https://your-github-username.github.io/HPS-Souvenir-Program-Single/"
).strip()

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MAX_FLOWERS = 10


def _build_web_app_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(
            "🌸 Open flower order form",
            web_app=WebAppInfo(url=WEB_APP_URL),
        )]],
        resize_keyboard=True,
        is_persistent=True,
    )


def _parse_web_app_order(raw_data: str) -> tuple[str, int, int]:
    try:
        data = json.loads(raw_data)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Order data could not be read. Please reopen the order form.") from exc

    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Order data is invalid. Please reopen the order form.")

    student_id = data.get("student_id")
    if not isinstance(student_id, str) or not student_id.strip() or len(student_id.strip()) > 48:
        raise ValueError("Please enter a valid Student ID.")

    flower_id = data.get("flower_id")
    if isinstance(flower_id, bool) or not isinstance(flower_id, int) or flower_id not in FLOWER_CATALOGUE:
        raise ValueError("Please select a valid flower.")

    quantity = data.get("quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= MAX_FLOWERS:
        raise ValueError("Choose a quantity from 1 to 10.")

    return student_id.strip(), flower_id, quantity


def _souvenir_filename(student_id: str, flower_key: str, quantity: int) -> str:
    safe_id  = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", student_id).strip(" ._")
    safe_key = flower_key.capitalize()
    return f"{safe_id or 'student'} - {safe_key} x{quantity}.png"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "မင်္ဂလာပါ 🌸\n\n"
        "အမှတ်တရပန်းစည်းအတွက် အောက်ပါခလုတ်ကို နှိပ်ပြီး ဝဘ်ဖောင်တွင် မှာယူပေးပါ။",
        reply_markup=_build_web_app_keyboard(),
    )


async def on_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user    = update.effective_user

    # ── 1. Parse order from Mini App ─────────────────────────────────────────
    try:
        student_id, flower_id, quantity = _parse_web_app_order(message.web_app_data.data)
    except ValueError as exc:
        await message.reply_text(str(exc))
        return

    flower = FLOWER_CATALOGUE[flower_id]

    # ── 2. Send "generating" notice ───────────────────────────────────────────
    wait_msg = await message.reply_text("⏳ ပန်းစည်းကို ဖန်တီးနေပါသည်…")

    # ── 3. Generate the souvenir card ─────────────────────────────────────────
    try:
        photo_bytesio = generate_single_bouquet(
            flower_id=flower_id,
            quantity=quantity,
            output_path=None,
            donor_id=student_id,
        )

        # ── 4. Build caption ──────────────────────────────────────────────
        caption = (
            f"💐 မင်္ဂလာပါ {user.first_name}၊ သင်၏ အမှတ်တရ ပန်းစည်းလွှာ ရရှိပါပြီ!\n\n"
            f"Student ID : {student_id}\n"
            f"{flower['emoji']} {flower['name']} × {to_burmese_num(quantity)} ပွင့်\n\n"
            "🙏 လှူဒါန်းမှုအတွက် ကျေးဇူးအထူးတင်ရှိပါသည်။\n"
            "သင်၏ ထောက်ပံ့မှုသည် ကျောင်း၏ ဖွံ့ဖြိုးတိုးတက်မှုအတွက် "
            "အလွန်တန်ဖိုးရှိပါသည်။ 🌸"
        )

        # ── 5. Send finished card as document ─────────────────────────────
        filename = _souvenir_filename(student_id, flower["key"], quantity)
        await message.reply_document(
            document=photo_bytesio,
            filename=filename,
            read_timeout=120,
            write_timeout=120,
        )

        await message.reply_text(final_text)
        final_text = "✅ အသစ်မှာယူရန် /start ကို နှိပ်ပါ။"

    except FileNotFoundError as exc:
        logger.error("Premade image missing: %s", exc)
        await message.reply_text(
            "ဤပန်းအမျိုးအစားနှင့် အရေအတွက်အတွက် ပုံကို မတင်ရသေးပါ။ "
            "ကျေးဇူးပြု၍ နောက်မှ ပြန်လည်ကြိုးစားပေးပါ။"
        )
    except NetworkError:
        logger.exception("Could not send single souvenir card to user %s", user.id)
        await message.reply_text("⚠️ Telegram နှင့် ချိတ်ဆက်မှု ပြတ်တောက်နေပါသည်။ ပြန်လည်ကြိုးစားပေးပါ။")
    except Exception:
        logger.exception("Single bouquet generation failed for user %s", user.id)
        await message.reply_text("⚠️ အမှတ်တရကတ် ပေးပို့ရာတွင် အမှားဖြစ်ပေါ်ခဲ့ပါသည်။")
    finally:
        try:
            await wait_msg.delete()
        except Exception:
            pass


def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_SINGLE_BOT_TOKEN_HERE":
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN_SINGLE in the environment before running bot_single.py")
    if not WEB_APP_URL or WEB_APP_URL.startswith("https://your-github-username"):
        raise RuntimeError("Set TELEGRAM_WEB_APP_URL_SINGLE to the deployed single app HTTPS URL before running bot_single.py")

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, on_web_app_data))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
