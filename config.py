QUIZ_TOPICS = {
    "capital": {
        "file": "data/countries_full.csv",
        "question_field": "Страна",
        "answer_field": "Столица",
        "image_field": "Картинка",
        "image_folder": "images/countries",
        "question_text": "🌍 <b>{question}</b>\nВыбери столицу"
    },

    "country": {
        "file": "data/countries_full.csv",
        "question_field": "Столица",
        "answer_field": "Страна",
        "image_field": "Картинка",
        "image_folder": "images/countries",
        "question_text": "🏳️ Столица: <b>{question}</b>\nВыбери страну"
    },

    "flags": {
        "file": "data/countries_full.csv",
        "question_field": "Страна",
        "answer_field": "Страна",
        "image_field": "Флаг",
        "image_folder": "images/flags",
        "question_text": "🚩 Чей это флаг?"
    },

    "rivers": {
        "file": "data/rivers.csv",
        "question_field": "Река",
        "answer_field": "Страна",
        "image_field": None,
        "image_folder": None,
        "question_text": "🌊 Где находится река <b>{question}</b>?"
    }
}