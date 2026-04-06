import csv
import random
import os
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
import asyncio
import time

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# ===== загрузка данных =====
data = []
with open("countries.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        data.append(row)


# ===== генерация вопроса =====
def generate_question(mode):
    row = random.choice(data)

    if mode == "capital":
        correct = row["Столица"]
        pool = list({d["Столица"] for d in data if d["Столица"] != correct})
        question = f"🌍 <b>{row['Страна']}</b>\nВыбери столицу"

    else:
        correct = row["Страна"]
        pool = list({d["Страна"] for d in data if d["Страна"] != correct})
        question = f"🏳️ Столица: <b>{row['Столица']}</b>\nВыбери страну"

    # защита от падения
    if len(pool) < 3:
        wrong = pool
    else:
        wrong = random.sample(pool, 3)

    answers = wrong + [correct]
    random.shuffle(answers)

    return {
        "question": question,
        "correct": correct,
        "answers": answers,
        "image": row["Картинка"]
    }


# ===== меню =====
def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏙 Столицы", callback_data="mode_capital"),
            InlineKeyboardButton("🌍 Страны", callback_data="mode_country"),
        ]
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
            "Привет! Я Квиз-Бот!\n" 
            "Используй нижнюю клавиатуру для выхода в меню\n" 
            "Выбери режим игры:",
        reply_markup=main_menu()
    )


# ===== обработка =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data_cb = query.data
    print("CLICK:", data_cb)

    user_data = context.user_data

    # ===== МЕНЮ =====
    if data_cb == "menu":
        user_data.clear()
        await query.message.edit_text("Главное меню:", reply_markup=main_menu())
        return

    # ===== РЕЖИМ =====
    if data_cb == "mode_capital":
        mode = "capital"
    elif data_cb == "mode_country":
        mode = "country"
    else:
        mode = None

    if mode:
        user_data.clear()
        user_data["mode"] = mode

        keyboard = [
            [InlineKeyboardButton("10 вопросов", callback_data="start_10")],
            [InlineKeyboardButton("20 вопросов", callback_data="start_20")],
            [InlineKeyboardButton("30 вопросов", callback_data="start_30")],
            [InlineKeyboardButton("♾ Безлимит", callback_data="start_inf")],
            [InlineKeyboardButton("🏠 В меню", callback_data="menu")]
        ]

        await query.message.edit_text(
            "Сколько вопросов?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ===== БЕЗЛИМИТ ВЫБОР =====
    if data_cb == "start_inf":
        keyboard = [
            [InlineKeyboardButton("1 ошибка", callback_data="inf_1")],
            [InlineKeyboardButton("3 ошибки", callback_data="inf_3")],
            [InlineKeyboardButton("⏱ На время", callback_data="inf_time")],
            [InlineKeyboardButton("🏠 В меню", callback_data="menu")]
        ]

        await query.message.edit_text(
            "Выбери режим:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ===== БЕЗЛИМИТ СТАРТ =====
    if data_cb.startswith("inf_"):
        user_data.clear()

        user_data["infinite"] = True
        user_data["score"] = 0

        if data_cb == "inf_1":
            user_data["lives"] = 1
        elif data_cb == "inf_3":
            user_data["lives"] = 3
        elif data_cb == "inf_time":
            import time
            user_data["time_mode"] = True
            user_data["end_time"] = time.time() + 60

        await send_question(query, context)
        return

    # ===== ОБЫЧНЫЙ СТАРТ =====
    if data_cb.startswith("start_"):
        total = int(data_cb.split("_")[1])

        user_data.clear()
        user_data["infinite"] = False
        user_data["total"] = total
        user_data["left"] = total
        user_data["score"] = 0

        await send_question(query, context)
        return

    # ===== ОТВЕТ =====
    if data_cb.startswith("ans"):
        if user_data.get("answered"):
            return

        user_data["answered"] = True

        idx = int(data_cb.split("_")[1])
        answers = user_data["answers"]
        correct = user_data["correct"]

        is_correct = answers[idx] == correct

        if is_correct:
            user_data["score"] += 1
            text = "✅ Верно!"
        else:
            text = f"❌ Неверно!\n<b>{correct}</b>"

        await query.message.reply_text(text, parse_mode="HTML")

        # ===== БЕЗЛИМИТ =====
        if user_data.get("infinite"):

            if "lives" in user_data:
                if not is_correct:
                    user_data["lives"] -= 1

                if user_data["lives"] <= 0:
                    await finish_game(query, context)
                    return

            if user_data.get("time_mode"):
                import time
                if time.time() >= user_data["end_time"]:
                    await finish_game(query, context)
                    return

            await send_question(query, context)
            return

        # ===== ОБЫЧНЫЙ =====
        user_data["left"] -= 1

        if user_data["left"] > 0:
            await send_question(query, context)
        else:
            await finish_game(query, context)

# async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()
#
#     data_cb = query.data
#     user_data = context.user_data
#
#     # ===== в меню =====
#     if data_cb == "menu":
#         user_data.clear()
#         await query.message.edit_text("Главное меню:", reply_markup=main_menu())
#         return
#
#     # ===== выбор режима =====
#     if data_cb.startswith("mode"):
#         mode = data_cb.split("_")[1]
#         user_data.clear()
#         user_data["mode"] = mode
#
#         keyboard = [
#             [InlineKeyboardButton(f"{n} вопросов", callback_data=f"start_{n}")]
#             for n in [10, 20, 30]
#         ]
#
#         # 👇 добавляем безлимит
#         keyboard.append([InlineKeyboardButton("♾ Безлимит", callback_data="start_inf")])
#         keyboard.append([InlineKeyboardButton("🏠 В меню", callback_data="menu")])
#
#         await query.message.edit_text(
#             "Выбери количество вопросов?",
#             reply_markup=InlineKeyboardMarkup(keyboard)
#         )
#         return
#
#     # ===== старт =====
#     if data_cb == "start_inf":
#         keyboard = [
#             [InlineKeyboardButton("1 ошибка", callback_data="inf_1")],
#             [InlineKeyboardButton("3 ошибки", callback_data="inf_3")],
#             [InlineKeyboardButton("⏱ На время", callback_data="inf_time")],
#             [InlineKeyboardButton("🏠 В меню", callback_data="menu")]
#         ]
#
#         await query.message.edit_text(
#             "Выбери режим:",
#             reply_markup=InlineKeyboardMarkup(keyboard)
#         )
#         return
#
#     if data_cb.startswith("inf"):
#         user_data.clear()
#
#         mode = data_cb.split("_")[1]
#
#         user_data["infinite"] = True
#         user_data["score"] = 0
#
#         if mode == "1":
#             user_data["lives"] = 1
#         elif mode == "3":
#             user_data["lives"] = 3
#         elif mode == "time":
#             user_data["time_mode"] = True
#             user_data["end_time"] = time.time() + 60
#
#         await send_question(query, context)
#         return
#
#     if data_cb.startswith("start"):
#         total = int(data_cb.split("_")[1])
#
#         user_data["infinite"] = False
#         user_data["total"] = total
#         user_data["left"] = total
#         user_data["score"] = 0
#
#         await send_question(query, context)
#         return
#
#     # ===== ответ =====
#     if data_cb.startswith("ans"):
#         if user_data.get("answered"):
#             return
#
#         user_data["answered"] = True
#
#         idx = int(data_cb.split("_")[1])
#         answers = user_data["answers"]
#         correct = user_data["correct"]
#
#         if answers[idx] == correct:
#             user_data["score"] += 1
#             text = "✅ Верно!"
#         else:
#             text = f"❌ Неверно!\nПравильный ответ: <b>{correct}</b>"
#
#         await query.message.reply_text(
#             text,
#             parse_mode="HTML"
#         )
#
#         user_data["left"] -= 1
#
#         if user_data["left"] > 0:
#             await send_question(query, context)
#         else:
#             score = user_data["score"]
#             total = user_data["total"]
#
#             # финальное сообщение
#             await query.message.reply_text(
#                 f"🎉 <b>Квиз завершён!</b>\n\n"
#                     f"📊 Результат: <b>{score}/{total}</b>\n"
#                     f"🔥 Точность: <b>{int(score/total*100)}%</b>",
#                 parse_mode="HTML"
#             )
#
#             # пауза 3 секунды
#             await asyncio.sleep(3)
#
#             # возврат в меню
#             await query.message.reply_text(
#                 "Главное меню:",
#                 reply_markup=main_menu()
#             )


# ===== отправка вопроса =====
async def send_question(query, context):
    user_data = context.user_data

    q = generate_question(user_data["mode"])

    user_data["correct"] = q["correct"]
    user_data["answers"] = q["answers"]
    user_data["answered"] = False

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

    img_path = os.path.join("images", q["image"])

    # DEBUG лог
    print("IMG:", img_path)

    if os.path.exists(img_path):
        with open(img_path, "rb") as img:
            await query.message.reply_photo(
                photo=img,
                caption=q["question"],
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        await query.message.reply_text(
            f"{q['question']}\n\n(⚠️ нет картинки)",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def finish_game(query, context):
    user_data = context.user_data

    score = user_data.get("score", 0)
    total = user_data.get("total", "∞")

    await query.message.reply_text(
        f"🎉 <b>Завершено!</b>\n\n"
        f"Результат: <b>{score}</b> из <b>{total}</b>",
        parse_mode="HTML"
    )

    await asyncio.sleep(3)

    await query.message.reply_text(
        "Главное меню:",
        reply_markup=main_menu()
    )
    user_data.clear()

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🏠 В меню":
        context.user_data.clear()

        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu()
        )


# ===== main =====
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()


# import csv
# import random
# import os
# from telegram import (
#     Update,
#     InlineKeyboardButton,
#     InlineKeyboardMarkup,
#     InputFile
# )
# from telegram.ext import (
#     Application,
#     CommandHandler,
#     CallbackQueryHandler,
#     ContextTypes
# )
# from dotenv import load_dotenv
# import os
#
# load_dotenv()
#
# TOKEN = os.getenv("BOT_TOKEN")
#
# # ====== Загрузка данных ======
# data = []
#
# with open("countries.csv", encoding="utf-8") as f:
#     reader = csv.DictReader(f)
#     for row in reader:
#         data.append(row)
#
#
# # ====== Генерация вопроса ======
# def generate_question(mode):
#     row = random.choice(data)
#
#     if mode == "capital":
#         correct = row["Столица"]
#         pool = [d["Столица"] for d in data if d["Столица"] != correct]
#
#         question = f"🌍 Угадай столицу страны:\n<b>{row['Страна']}</b>"
#
#     else:
#         correct = row["Страна"]
#         pool = [d["Страна"] for d in data if d["Страна"] != correct]
#
#         question = f"🏳️ Угадай страну:\nСтолица — <b>{row['Столица']}</b>"
#
#     wrong_answers = random.sample(pool, 3)
#     answers = wrong_answers + [correct]
#     random.shuffle(answers)
#
#     return {
#         "question": question,
#         "correct": correct,
#         "answers": answers,
#         "image": row["Картинка"]
#     }
#
#
# # ====== /start ======
# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     keyboard = [
#         [
#             InlineKeyboardButton("🏙 Угадай столицу", callback_data="mode_capital"),
#             InlineKeyboardButton("🌍 Угадай страну", callback_data="mode_country"),
#         ]
#     ]
#
#     await update.message.reply_text(
#         "Привет! Выбери режим:",
#         reply_markup=InlineKeyboardMarkup(keyboard)
#     )
#
#
# # ====== Обработка кнопок ======
# async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()
#
#     data_cb = query.data
#     user_data = context.user_data
#
#     # ===== выбор режима =====
#     if data_cb.startswith("mode"):
#         mode = data_cb.split("_")[1]
#         user_data.clear()
#         user_data["mode"] = mode
#
#         keyboard = [
#             [InlineKeyboardButton(f"{n} вопросов", callback_data=f"start_{n}")]
#             for n in [10, 20, 30]
#         ]
#
#         await query.message.reply_text(
#             "Выбери количество вопросов:",
#             reply_markup=InlineKeyboardMarkup(keyboard)
#         )
#
#     # ===== старт игры =====
#     elif data_cb.startswith("start"):
#         total = int(data_cb.split("_")[1])
#
#         user_data["total"] = total
#         user_data["left"] = total
#         user_data["score"] = 0
#
#         await send_question(query, context)
#
#     # ===== ответ =====
#     elif data_cb.startswith("ans"):
#         if user_data.get("answered"):
#             return  # защита от повторного клика
#
#         user_data["answered"] = True
#
#         selected_index = int(data_cb.split("_")[1])
#         answers = user_data["answers"]
#         correct = user_data["correct"]
#
#         if answers[selected_index] == correct:
#             user_data["score"] += 1
#             text = "✅ Верно!"
#         else:
#             text = f"❌ Ошибка!\nПравильный ответ: <b>{correct}</b>"
#
#         await query.message.reply_text(text, parse_mode="HTML")
#
#         user_data["left"] -= 1
#
#         if user_data["left"] > 0:
#             await send_question(query, context)
#         else:
#             score = user_data["score"]
#             total = user_data["total"]
#
#             await query.message.reply_text(
#                 f"🎯 Результат: <b>{score}/{total}</b>",
#                 parse_mode="HTML"
#             )
#
#             user_data.clear()
#
#
# # ====== Отправка вопроса ======
# async def send_question(query, context):
#     user_data = context.user_data
#
#     q = generate_question(user_data["mode"])
#
#     user_data["correct"] = q["correct"]
#     user_data["answers"] = q["answers"]
#     user_data["answered"] = False
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
#     img_path = os.path.join("images", q["image"])
#
#     if os.path.exists(img_path):
#         await query.message.reply_photo(
#             photo=InputFile(img_path),
#             caption=q["question"],
#             reply_markup=InlineKeyboardMarkup(keyboard),
#             parse_mode="HTML"
#         )
#     else:
#         await query.message.reply_text(
#             q["question"],
#             reply_markup=InlineKeyboardMarkup(keyboard),
#             parse_mode="HTML"
#         )
#
#
# # ====== MAIN ======
# def main():
#     app = Application.builder().token(TOKEN).build()
#
#     app.add_handler(CommandHandler("start", start))
#     app.add_handler(CallbackQueryHandler(handle_callback))
#
#     print("Bot started...")
#     app.run_polling()
#
#
# if __name__ == "__main__":
#     main()