import telebot
from telebot import types
import sqlite3
import random
import spoonacular as sp


bot = telebot.TeleBot('')
api = sp.API('')


def init_db():
    """Инициализирует базу данных с таблицей рецептов."""
    conn = sqlite3.connect("recipes.db")
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ingredients TEXT NOT NULL,
            calories INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


init_db()


def add_recipe(name, ingredients_name, calories):
    """Добавляет рецепт в базу данных."""
    conn = sqlite3.connect("recipes.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO recipes (name, ingredients, calories) VALUES (?, ?, ?)",
        (name, ingredients_name, calories)
    )
    conn.commit()
    conn.close()


def get_random_recipe_by_ingredient(ingredient):
    """Возвращает случайный рецепт с указанным ингредиентом."""
    conn = sqlite3.connect("recipes.db")
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM recipes WHERE ingredients LIKE ?",
        (f'%{ingredient.lower()}%',)
    )
    recipes = cur.fetchall()
    conn.close()
    return random.choice(recipes) if recipes else None


user_data = {}


@bot.message_handler(commands=['start'])
def start(message):
    """Обработчик команды /start с созданием клавиатуры."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Добавить рецепт')
    btn2 = types.KeyboardButton('Подобрать рецепт')
    markup.row(btn1, btn2)
    btn3 = types.KeyboardButton('Составить рацион')
    btn4 = types.KeyboardButton('Кулинарный анекдот!')
    markup.row(btn3, btn4)
    bot.send_message(
        message.chat.id,
        "Привет! 👋 \nБот «Что на ужин?» может помочь придумать что "
        "приготовить или составить рацион 😊\nВыбери нужную команду 🍱",
        reply_markup=markup
    )


@bot.message_handler(content_types=['text'])
def main_func(message):
    """Основной обработчик текстовых сообщений."""
    chat_id = message.chat.id
    text = message.text.strip()

    if text == 'Добавить рецепт':
        user_data[chat_id] = {"step": "name"}
        bot.send_message(chat_id, "Введите название рецепта:")
    elif text == 'Подобрать рецепт':
        user_data[chat_id] = {"step": "search_ingredient"}
        bot.send_message(chat_id, "Введите ингредиент, который должен быть в рецепте:")
    elif text == 'Составить рацион':
        user_data[chat_id] = {"step": "search_calories"}
        bot.send_message(chat_id, "Введите количество калорий (целое число):")
    elif text == 'Кулинарный анекдот!':
        try:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('Хочу ещё один анекдот!😃', callback_data='joke'))
            response = api.get_a_random_food_joke()
            data = response.json()
            bot.reply_to(message, data['text'], reply_markup=markup)
        except Exception as e:
            bot.reply_to(message, f"Извините, не удалось получить анекдот. Ошибка: {str(e)}")
    elif chat_id in user_data:
        handle_user_data(chat_id, text, message)


def handle_user_data(chat_id, text, message):
    """Обрабатывает данные пользователя на разных этапах взаимодействия."""
    step = user_data[chat_id]["step"]

    if step == "name":
        user_data[chat_id]["name"] = text
        user_data[chat_id]["step"] = "ingredients"
        bot.send_message(chat_id, "Теперь введите ингредиенты через запятую:")

    elif step == "ingredients":
        user_data[chat_id]["ingredients"] = message.text.lower()
        user_data[chat_id]["step"] = "calories"
        bot.send_message(chat_id, "Введите калорийность одной порции (целое число):")

    elif step == "calories":
        try:
            calories = int(text)
            name = user_data[chat_id]["name"]
            ingredients = user_data[chat_id]["ingredients"]
            add_recipe(name, ingredients, calories)
            bot.send_message(chat_id, f"✅ Рецепт «{name}» успешно добавлен!")
            user_data.pop(chat_id)
        except ValueError:
            bot.send_message(chat_id, "Пожалуйста, введите калорийность целым числом")

    elif step == "search_ingredient":
        ingredient = text.lower()
        recipe = get_random_recipe_by_ingredient(ingredient)
        if recipe:
            _, name, ingredients, calories = recipe
            response = (f"🍽 Рецепт: {name}\n"
                       f"📋 Ингредиенты: {ingredients}\n"
                       f"🔥 Калорийность: {calories} ккал")
            bot.send_message(chat_id, response)
        else:
            bot.send_message(
                chat_id,
                f"Рецептов с ингредиентом '{ingredient}' не найдено 😔\n"
                f"Попробуйте изменить форму слова или ввести другой ингредиент!"
            )

    elif step == "search_calories":
        try:
            target_calories = int(text)
            conn = sqlite3.connect('recipes.db')
            cur = conn.cursor()
            cur.execute("SELECT * FROM recipes WHERE calories = ?", (target_calories,))
            exact_match = cur.fetchone()

            if exact_match:
                _, name, ingredients, calories = exact_match
                response = (f"🍽 Точное совпадение: {name}\n"
                           f"📋 Ингредиенты: {ingredients}\n"
                           f"🔥 Калорийность: {calories} ккал")
                bot.send_message(chat_id, response)
            else:
                cur.execute(
                    "SELECT * FROM recipes WHERE calories <= ? ORDER BY calories DESC LIMIT 1",
                    (target_calories,)
                )
                lower = cur.fetchone()
                cur.execute(
                    "SELECT * FROM recipes WHERE calories >= ? ORDER BY calories ASC LIMIT 1",
                    (target_calories,)
                )
                upper = cur.fetchone()
                response = []

                if lower:
                    _, name, ingredients, calories = lower
                    response.append(f"⬇️ Ближайший меньший:\n🍽 Рецепт: {name}\n"
                                  f"📋 Ингредиенты: {ingredients}\n"
                                  f"🔥 Калорийность: {calories} ккаl")

                if upper:
                    _, name, ingredients, calories = upper
                    response.append(f"⬆️ Ближайший больший:\n🍽 Рецепт: {name}\n"
                                  f"📋 Ингредиенты: {ingredients}\n"
                                  f"🔥 Калорийность: {calories} ккаl")

                if response:
                    bot.send_message(chat_id, "\n\n".join(response))
                else:
                    bot.send_message(chat_id, "К сожалению, подходящих рецептов не найдено 😔")
            conn.close()
        except ValueError:
            bot.send_message(chat_id, "Пожалуйста, введите целое число!")
        finally:
            user_data.pop(chat_id, None)


@bot.callback_query_handler(func=lambda callback: True)
def callback_message(callback):
    """Обрабатывает callback-запросы от инлайн-кнопок."""
    if callback.data == 'joke':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Хочу еще один анекдот!😃', callback_data='joke'))
        response = api.get_a_random_food_joke()
        data = response.json()
        bot.send_message(callback.message.chat.id, data['text'], reply_markup=markup)


if __name__ == '__main__':
    bot.polling(none_stop=True)