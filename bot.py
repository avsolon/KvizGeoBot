import os
import asyncio
from dotenv import load_dotenv

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

from quiz_engine import QuizEngine
from config import QUIZ_TOPICS

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

engine = QuizEngine(QUIZ_TOPICS)

# ===== меню =====
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏙 Столицы", callback_data="topic_capital")],
        [InlineKeyboardButton("🌍 Страны", callback_data="topic_country")],
        [InlineKeyboardButton("🚩 Флаги", callback_data="topic_flags")],
        [InlineKeyboardButton("🌊 Водная стихия", callback_data="topic_water")]
    ])

def reply_menu():
    return ReplyKeyboardMarkup(
        [["🏠 В меню"]],
        resize_keyboard=True
    )

# ===== старт =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "⬇️ Для возврата в Меню используй клавиатуру в строке чата",
        reply_markup=reply_menu()
    )

    await update.message.reply_text(
        "Привет! Выбери тему:",
        reply_markup=main_menu()
    )

# ===== обработка =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user = context.user_data

    # ===== выбор темы =====
    if data.startswith("topic_"):
        topic = data.replace("topic_", "")

        user.clear()
        user["topic"] = topic

        keyboard = [
            [InlineKeyboardButton("10", callback_data="start_10")],
            [InlineKeyboardButton("20", callback_data="start_20")],
            [InlineKeyboardButton("30", callback_data="start_30")],
            [InlineKeyboardButton("♾", callback_data="start_inf")]
        ]

        await query.message.reply_text(
            "Сколько вопросов?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ===== старт =====
    if data.startswith("start_"):
        topic = user.get("topic")

        user.clear()
        user["topic"] = topic
        user["score"] = 0

        if data == "start_inf":
            user["infinite"] = True
        else:
            total = int(data.split("_")[1])
            user["left"] = total
            user["total"] = total

        await send_question(query, context)
        return

    # ===== ответ =====
    if data.startswith("ans"):
        if user.get("answered"):
            return

        user["answered"] = True

        idx = int(data.split("_")[1])

        if user["answers"][idx] == user["correct"]:
            user["score"] += 1
            text = "✅ Верно!"
        else:
            text = f"❌ Неверно!\n<b>{user['correct']}</b>"

        await query.message.reply_text(text, parse_mode="HTML")

        if user.get("infinite"):
            await send_question(query, context)
            return

        user["left"] -= 1

        if user["left"] > 0:
            await send_question(query, context)
        else:
            await finish_game(query, context)

# async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()
#
#     data = query.data
#     user = context.user_data
#
#     # ===== выбор темы =====
#     if data.startswith("topic_"):
#         topic = data.replace("topic_", "")
#
#         user.clear()
#         user["topic"] = topic
#
#         keyboard = [
#             [InlineKeyboardButton("10", callback_data="start_10")],
#             [InlineKeyboardButton("20", callback_data="start_20")],
#             [InlineKeyboardButton("30", callback_data="start_30")],
#             [InlineKeyboardButton("♾", callback_data="start_inf")]
#         ]
#
#         await query.message.reply_text(
#             "Сколько вопросов?",
#             reply_markup=InlineKeyboardMarkup(keyboard)
#         )
#         return
#
#     # ===== старт =====
#     if data.startswith("start_"):
#         topic = user.get("topic")
#
#         user.clear()
#         user["topic"] = topic
#         user["score"] = 0
#
#         if data == "start_inf":
#             user["infinite"] = True
#         else:
#             total = int(data.split("_")[1])
#             user["left"] = total
#             user["total"] = total
#
#         await send_question(query, context)
#         return
#
#     # ===== ответ =====
#     if data.startswith("ans"):
#         if user.get("answered"):
#             return
#
#         user["answered"] = True
#
#         idx = int(data.split("_")[1])
#
#         if user["answers"][idx] == user["correct"]:
#             user["score"] += 1
#             text = "✅ Верно!"
#         else:
#             text = f"❌ Неверно!\n<b>{user['correct']}</b>"
#
#         await query.message.reply_text(text, parse_mode="HTML")
#
#         if user.get("infinite"):
#             await send_question(query, context)
#             return
#
#         user["left"] -= 1
#
#         if user["left"] > 0:
#             await send_question(query, context)
#         else:
#             await finish_game(query, context)

# ===== вопрос =====
async def send_question(query, context):
    user = context.user_data

    topic = user.get("topic")

    q = engine.generate(topic)

    user["correct"] = q["correct"]
    user["answers"] = q["answers"]
    user["answered"] = False

    keyboard = [
        [
            InlineKeyboardButton(q["answers"][0], callback_data="ans_0"),
            InlineKeyboardButton(q["answers"][1], callback_data="ans_1"),
        ],
        [
            InlineKeyboardButton(q["answers"][2], callback_data="ans_2"),
            InlineKeyboardButton(q["answers"][3], callback_data="ans_3"),
        ]
    ]

    image = q.get("image")

    # 🔥 если есть картинка / флаг
    if image:
        # 👉 если это URL (флаг)
        if image.startswith("http"):
            await query.message.reply_photo(
                photo=image,
                caption=q["question"],
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        # 👉 если это локальный файл
        elif q["image_folder"]:
            path = os.path.join(q["image_folder"], image)

            if os.path.exists(path):
                with open(path, "rb") as img:
                    await query.message.reply_photo(
                        photo=img,
                        caption=q["question"],
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    return

    # 👉 fallback (без картинки)
    await query.message.reply_text(
        q["question"],
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# async def send_question(query, context):
#     user = context.user_data
#
#     topic = user.get("topic")
#
#     q = engine.generate(topic)
#
#     user["correct"] = q["correct"]
#     user["answers"] = q["answers"]
#     user["answered"] = False
#
#     keyboard = [
#         [
#             InlineKeyboardButton(q["answers"][0], callback_data="ans_0"),
#             InlineKeyboardButton(q["answers"][1], callback_data="ans_1"),
#         ],
#         [
#             InlineKeyboardButton(q["answers"][2], callback_data="ans_2"),
#             InlineKeyboardButton(q["answers"][3], callback_data="ans_3"),
#         ]
#     ]
#
#     if q["image"] and q["image_folder"]:
#         path = os.path.join(q["image_folder"], q["image"])
#
#         if os.path.exists(path):
#             with open(path, "rb") as img:
#                 await query.message.reply_photo(
#                     photo=img,
#                     caption=q["question"],
#                     parse_mode="HTML",
#                     reply_markup=InlineKeyboardMarkup(keyboard)
#                 )
#             return
#
#     await query.message.reply_text(
#         q["question"],
#         parse_mode="HTML",
#         reply_markup=InlineKeyboardMarkup(keyboard)
#     )

# ===== завершение =====
async def finish_game(query, context):
    user = context.user_data

    score = user.get("score", 0)
    total = user.get("total", "∞")

    await query.message.reply_text(
        f"🎉 Результат: <b>{score}</b> из <b>{total}</b>\n"
        f"🔥 Точность: <b>{int(score / total * 100)}%</b>",
        parse_mode="HTML"
    )

    await asyncio.sleep(2)

    await query.message.reply_text(
        "Главное меню:",
        reply_markup=main_menu()
    )

    user.clear()

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if update.message.text == "🏠 В меню":
        context.user_data.clear()

        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu()
        )

# ===== запуск =====
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()