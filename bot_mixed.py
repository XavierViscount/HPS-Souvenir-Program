import logging
import json
import os
import re
from collections import Counter

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.error import NetworkError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bouquet_generator import (
    ARRANGEMENT_STYLES,
    FLOWER_CATALOGUE,
    generate_bouquet,
    to_burmese_num,
)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN_MIXED", "").strip()
WEB_APP_URL = (
    os.environ.get("TELEGRAM_WEB_APP_URL", "https://xavierviscount.github.io/HPS-Souvenir-Program-Mixed/")
    or "https://xavierviscount.github.io/HPS-Souvenir-Program-Mixed/"
).strip()

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MAX_FLOWERS = 10

_KEY_SELECTED = "selected_flowers"
_KEY_STUDENT_ID = "student_id"
_KEY_AWAITING_STUDENT_ID = "awaiting_student_id"
_KEY_ARRANGEMENT = "arrangement"


def _build_keyboard(selected: list[int]) -> InlineKeyboardMarkup:
    rows = []
    counts = Counter(selected)
    for fid in sorted(FLOWER_CATALOGUE.keys()):
        info = FLOWER_CATALOGUE[fid]
        quantity = to_burmese_num(counts[fid])
        label = f"{info['emoji']} {info['name']} ×{quantity}"
        rows.append([
            InlineKeyboardButton("➖", callback_data=f"remove:{fid}"),
            InlineKeyboardButton(label, callback_data=f"noop:{fid}"),
            InlineKeyboardButton("➕", callback_data=f"add:{fid}"),
        ])

    rows.append([
        InlineKeyboardButton("ညီညာ", callback_data="layout:balanced"),
        InlineKeyboardButton("ကျစ်လျစ်", callback_data="layout:compact"),
        InlineKeyboardButton("ယပ်ပုံ", callback_data="layout:fan"),
    ])
    rows.append([InlineKeyboardButton("💐 ပန်းစည်းဖန်တီးမည်", callback_data="generate")])
    rows.append([InlineKeyboardButton("🧹 ပန်းရွေးချယ်မှုရှင်းမည်", callback_data="clear")])
    return InlineKeyboardMarkup(rows)


def _build_web_app_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🌸 ပန်းစည်း Mini App", web_app=WebAppInfo(url=WEB_APP_URL))]],
        resize_keyboard=True,
    )


def _picker_text(selected: list[int]) -> str:
    count = len(selected)
    count_mm = to_burmese_num(count)
    max_mm = to_burmese_num(MAX_FLOWERS)

    header = (
        "🌸 *Mixed Bouquet Bot* 🌸\n\n"
        "လိုချင်သော ပန်းအရေအတွက်ကို ➕ နှင့် ➖ ဖြင့် ရွေးချယ်ပါ (အများဆုံး ၁၀ ပွင့်)။\n"
        "ပြီးပါက *💐 ပန်းစည်းဖန်တီးမည်* ကို နှိပ်ပါ။\n\n"
    )
    counter = f"*ရွေးချယ်ထားသော ပန်းအရေအတွက်: {count_mm}/{max_mm} ပွင့်*\n"

    if not selected:
        detail = "\n_ပန်းများ မရွေးချယ်ရသေးပါ_"
    else:
        counts = Counter(selected)
        names = [
            f"{FLOWER_CATALOGUE[fid]['emoji']} {FLOWER_CATALOGUE[fid]['name']} ×{to_burmese_num(counts[fid])}"
            for fid in sorted(counts)
        ]
        detail = "\n" + "  •  ".join(names)

    return header + counter + detail


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[_KEY_SELECTED] = []
    context.user_data.pop(_KEY_STUDENT_ID, None)
    context.user_data.pop(_KEY_AWAITING_STUDENT_ID, None)

    if WEB_APP_URL:
        await update.message.reply_text(
            "မင်္ဂလာပါ 🌸\n\n"
            "အမှတ်တရပန်းစည်းကို ဖန်တီးရန် အောက်ပါခလုတ်ကို နှိပ်ပါ။",
            reply_markup=_build_web_app_keyboard(),
        )
        return

    context.user_data[_KEY_AWAITING_STUDENT_ID] = True
    await update.message.reply_text(
        "မင်္ဂလာပါ 🌸\n\n"
        "အမှတ်တရပန်းစည်းအတွက် ကျောင်းသား/ကျောင်းသူ၏ Student ID ကို ရိုက်ထည့်ပေးပါ။\n"
        "ဥပမာ - HPS-ISS9003"
    )


async def on_student_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get(_KEY_AWAITING_STUDENT_ID):
        return

    student_id = (update.message.text or "").strip()
    if not student_id:
        await update.message.reply_text(
            "Student ID ကို မတွေ့ရပါ။\n"
            "ဥပမာ - HPS-ISS9003\n"
            "ကျေးဇူးပြု၍ Student ID ကို ပြန်လည်ရိုက်ထည့်ပေးပါ။"
        )
        return

    context.user_data[_KEY_STUDENT_ID] = student_id
    context.user_data[_KEY_AWAITING_STUDENT_ID] = False
    context.user_data[_KEY_SELECTED] = []
    await update.message.reply_text(
        _picker_text([]),
        reply_markup=_build_keyboard([]),
        parse_mode="Markdown",
    )


def _parse_web_app_order(raw_data: str) -> tuple[str, list[int], str]:
    try:
        data = json.loads(raw_data)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("အော်ဒါအချက်အလက်ကို ဖတ်မရပါ။ Mini App မှ ပြန်လည်တင်ပေးပါ။") from exc

    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("အော်ဒါအချက်အလက် မမှန်ပါ။ Mini App မှ ပြန်လည်တင်ပေးပါ။")

    student_id = data.get("student_id")
    if not isinstance(student_id, str) or not student_id.strip() or len(student_id.strip()) > 48:
        raise ValueError("မှန်ကန်သော Student ID ကို ဖြည့်ပေးပါ။")

    mode = data.get("mode")
    if not isinstance(mode, str):
        raise ValueError("မှာယူမှုပုံစံ မမှန်ပါ။ Mini App မှ ပြန်လည်ရွေးချယ်ပေးပါ။")
    if mode == "all":
        selected = sorted(FLOWER_CATALOGUE)
    elif mode in {"individual", "single"}:
        selected = data.get("flower_ids")
        if not isinstance(selected, list) or any(
            isinstance(flower_id, bool)
            or not isinstance(flower_id, int)
            or flower_id not in FLOWER_CATALOGUE
            for flower_id in selected
        ):
            raise ValueError("ပန်းရွေးချယ်မှု မမှန်ပါ။ Mini App မှ ပြန်လည်ရွေးချယ်ပေးပါ။")
    else:
        raise ValueError("မှာယူမှုပုံစံ မမှန်ပါ။ Mini App မှ ပြန်လည်ရွေးချယ်ပေးပါ။")

    if not selected or len(selected) > MAX_FLOWERS:
        raise ValueError("ပန်း ၁ ပွင့်မှ ၁၀ ပွင့်အထိ ရွေးချယ်ပေးပါ။")
    if mode == "single" and len(set(selected)) != 1:
        raise ValueError("ပန်းတစ်မျိုးတည်းကိုသာ ရွေးချယ်ပေးပါ။")

    arrangement = data.get("arrangement", "balanced")
    if not isinstance(arrangement, str) or arrangement not in ARRANGEMENT_STYLES:
        raise ValueError("ပန်းစည်းပုံစံ မမှန်ပါ။ ပြန်လည်ရွေးချယ်ပေးပါ။")

    return student_id.strip(), selected, arrangement


def _souvenir_filename(student_id: str, flower_count: int) -> str:
    safe_student_id = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", student_id).strip(" ._")
    return f"{safe_student_id or 'student'} ({flower_count} flowers).png"


async def on_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user

    try:
        student_id, selected, arrangement = _parse_web_app_order(message.web_app_data.data)
    except ValueError as exc:
        await message.reply_text(str(exc))
        return

    try:
        photo_bytesio = generate_bouquet(
            selected_flowers=selected,
            output_path=None,
            donor_id=student_id,
            arrangement=arrangement,
        )
        selected_counts = Counter(selected)
        chosen_names = [
            f"{FLOWER_CATALOGUE[fid]['emoji']} {FLOWER_CATALOGUE[fid]['name']} ×{to_burmese_num(selected_counts[fid])}"
            for fid in sorted(selected_counts)
        ]
        caption = (
            f"💐 *မင်္ဂလာပါ {user.first_name}၊ သင်၏ အမှတ်တရ ပန်းစည်းလွှာ ရရှိပါပြီ!*\n\n"
            f"🌿 *ရွေးချယ်ထားသော ပန်းများ:*\n{'  •  '.join(chosen_names)}"
        )

        await message.reply_document(
            document=photo_bytesio,
            filename=_souvenir_filename(student_id, len(selected)),
            caption=caption,
            parse_mode="Markdown",
        )

        await message.reply_text("✅ အမှတ်တရကတ် ပေးပို့ပြီးပါပြီ။ အသစ်ပြုလုပ်ရန် Mini App ကို ပြန်ဖွင့်ပါ။")
    except Exception:
        logger.exception("Mixed Mini App bouquet generation failed for user %s", user.id)
        try:
            await message.reply_text("⚠️ အမှတ်တရကတ် ဖန်တီးရာတွင် အမှားဖြစ်ပေါ်ခဲ့ပါသည်။ ပြန်လည်ကြိုးစားပေးပါ။")
        except NetworkError:
            logger.warning("Could not notify user %s because Telegram is unreachable", user.id)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data
    selected: list[int] = context.user_data.setdefault(_KEY_SELECTED, [])

    if data.startswith("add:"):
        flower_id = int(data.split(":")[1])
        if len(selected) >= MAX_FLOWERS:
            await query.answer(f"အများဆုံး {to_burmese_num(MAX_FLOWERS)} ပွင့်သာ ရွေးချယ်နိုင်ပါသည်!", show_alert=True)
            return
        selected.append(flower_id)
        context.user_data[_KEY_SELECTED] = selected
        await query.answer()
        await query.edit_message_text(
            text=_picker_text(selected),
            reply_markup=_build_keyboard(selected),
            parse_mode="Markdown",
        )
        return

    if data.startswith("remove:"):
        flower_id = int(data.split(":")[1])
        if flower_id not in selected:
            await query.answer("ဤပန်းကို မရွေးချယ်ရသေးပါ။", show_alert=True)
            return
        selected.remove(flower_id)
        context.user_data[_KEY_SELECTED] = selected
        await query.answer()
        await query.edit_message_text(
            text=_picker_text(selected),
            reply_markup=_build_keyboard(selected),
            parse_mode="Markdown",
        )
        return

    if data.startswith("layout:"):
        arrangement = data.split(":", 1)[1]
        if arrangement not in ARRANGEMENT_STYLES:
            await query.answer("ပန်းစည်းပုံစံ မမှန်ပါ။", show_alert=True)
            return
        context.user_data[_KEY_ARRANGEMENT] = arrangement
        await query.answer()
        await query.edit_message_text(
            text=_picker_text(selected),
            reply_markup=_build_keyboard(selected),
            parse_mode="Markdown",
        )
        return

    if data == "clear":
        context.user_data[_KEY_SELECTED] = []
        await query.answer()
        await query.edit_message_text(
            text=_picker_text([]),
            reply_markup=_build_keyboard([]),
            parse_mode="Markdown",
        )
        return

    if data == "generate":
        if not selected:
            await query.answer("ကျေးဇူးပြု၍ ပန်း အနည်းဆုံး ၁ ပွင့် ရွေးချယ်ပေးပါခင်ဗျာ!", show_alert=True)
            return

        await query.answer()
        await query.edit_message_text(
            "⏳ ပန်းစည်းကို ဖန်တီးနေပါသည်...",
            parse_mode="Markdown",
        )

        try:
            photo_bytesio = generate_bouquet(
                selected_flowers=list(selected),
                output_path=None,
                donor_id=context.user_data.get(_KEY_STUDENT_ID, "#Mixed"),
                arrangement=context.user_data.get(_KEY_ARRANGEMENT, "balanced"),
            )
            selected_counts = Counter(selected)
            chosen_names = [
                f"{FLOWER_CATALOGUE[fid]['emoji']} {FLOWER_CATALOGUE[fid]['name']} ×{to_burmese_num(selected_counts[fid])}"
                for fid in sorted(selected_counts)
            ]
            caption = (
                f"💐 *မင်္ဂလာပါ၊ သင်၏ ပန်းစည်းလွှာ ရရှိပါပြီ!*\n\n"
                f"🌿 *ရွေးချယ်ထားသော ပန်းများ:*\n{'  •  '.join(chosen_names)}"
            )
            student_id = context.user_data.get(_KEY_STUDENT_ID, "student")
            filename = _souvenir_filename(student_id, len(selected))

            await query.message.reply_document(
                document=photo_bytesio,
                filename=filename,
                caption=caption,
                parse_mode="Markdown",
            )

            await query.edit_message_text(
                "✅ *ပန်းစည်းလွှာ ပေးပို့ပြီးပါပြီ!*\n\nအသစ်ပြုလုပ်ရန် /start ကို နှိပ်ပါ။",
                parse_mode="Markdown",
            )
            context.user_data[_KEY_SELECTED] = []
        except Exception:
            logger.exception("Mixed bouquet generation failed")
            await query.edit_message_text(
                "⚠️ ပန်းစည်းဖန်တီးရာတွင် အမှားအယွင်း ဖြစ်ပေါ်ခဲ့ပါသည်။",
            )

    if data.startswith("noop:"):
        await query.answer()


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN_MIXED in the environment before running bot_mixed.py")

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, on_web_app_data))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_student_id))
    application.add_handler(CallbackQueryHandler(on_callback))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
