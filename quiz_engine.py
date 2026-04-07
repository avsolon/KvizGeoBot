import csv
import random

class QuizEngine:
    def __init__(self, config):
        self.config = config
        self.cache = {}

    def load_data(self, topic):
        if topic not in self.cache:
            file = self.config[topic]["file"]

            with open(file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.cache[topic] = list(reader)

        return self.cache[topic]

    def generate(self, topic):
        cfg = self.config[topic]
        data = self.load_data(topic)

        row = random.choice(data)

        correct = row[cfg["answer_field"]]

        pool = list({
            d[cfg["answer_field"]]
            for d in data
            if d[cfg["answer_field"]] != correct
        })

        wrong = random.sample(pool, min(3, len(pool)))
        answers = wrong + [correct]
        random.shuffle(answers)

        return {
            "question": cfg["question_text"].format(
                question=row[cfg["question_field"]]
            ),
            "correct": correct,
            "answers": answers,
            "image": row.get(cfg["image_field"]),
            "image_folder": cfg["image_folder"]
        }