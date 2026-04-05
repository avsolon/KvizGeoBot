import csv
import random
import os
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
    ContextTypes
)
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

# ====== Загрузка данных ======
data = []

with open("countries.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        data.append(row)


# ====== Генерация вопроса ======
def generate_question(mode):
    row = random.choice(data)

    if mode == "capital":
        correct = row["Столица"]
        pool = [d["Столица"] for d in data if d["Столица"] != correct]

        question = f"🌍 Угадай столицу страны:\n<b>{row['Страна']}</b>"

    else:
        correct = row["Страна"]
        pool = [d["Страна"] for d in data if d["Страна"] != correct]

        question = f"🏳️ Угадай страну:\nСтолица — <b>{row['Столица']}</b>"

    wrong_answers = random.sample(pool, 3)
    answers = wrong_answers + [correct]
    random.shuffle(answers)

    return {
        "question": question,
        "correct": correct,
        "answers": answers,
        "image": row["Картинка"]
    }


# ====== /start ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🏙 Угадай столицу", callback_data="mode_capital"),
            InlineKeyboardButton("🌍 Угадай страну", callback_data="mode_country"),
        ]
    ]

    await update.message.reply_text(
        "Привет! Выбери режим:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ====== Обработка кнопок ======
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data_cb = query.data
    user_data = context.user_data

    # ===== выбор режима =====
    if data_cb.startswith("mode"):
        mode = data_cb.split("_")[1]
        user_data.clear()
        user_data["mode"] = mode

        keyboard = [
            [InlineKeyboardButton(f"{n} вопросов", callback_data=f"start_{n}")]
            for n in [10, 20, 30]
        ]

        await query.message.reply_text(
            "Выбери количество вопросов:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ===== старт игры =====
    elif data_cb.startswith("start"):
        total = int(data_cb.split("_")[1])

        user_data["total"] = total
        user_data["left"] = total
        user_data["score"] = 0

        await send_question(query, context)

    # ===== ответ =====
    elif data_cb.startswith("ans"):
        if user_data.get("answered"):
            return  # защита от повторного клика

        user_data["answered"] = True

        selected_index = int(data_cb.split("_")[1])
        answers = user_data["answers"]
        correct = user_data["correct"]

        if answers[selected_index] == correct:
            user_data["score"] += 1
            text = "✅ Верно!"
        else:
            text = f"❌ Ошибка!\nПравильный ответ: <b>{correct}</b>"

        await query.message.reply_text(text, parse_mode="HTML")

        user_data["left"] -= 1

        if user_data["left"] > 0:
            await send_question(query, context)
        else:
            score = user_data["score"]
            total = user_data["total"]

            await query.message.reply_text(
                f"🎯 Результат: <b>{score}/{total}</b>",
                parse_mode="HTML"
            )

            user_data.clear()


# ====== Отправка вопроса ======
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

    if os.path.exists(img_path):
        await query.message.reply_photo(
            photo=InputFile(img_path),
            caption=q["question"],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    else:
        await query.message.reply_text(
            q["question"],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )


# ====== MAIN ======
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()