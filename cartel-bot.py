import logging
import os
import sqlite3
import html2text
from collections import defaultdict
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.types import InputFile, ParseMode
from aiogram.utils import executor

import config  # Import the file with bot settings (TOKEN)

logging.basicConfig(level=logging.INFO)

# Initialize the bot and state storage
bot = Bot(token=config.TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Connect to the database and create the table
def create_table():
    with sqlite3.connect("bot.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                keyword TEXT PRIMARY KEY,
                response TEXT NOT NULL,
                image_path TEXT NOT NULL,
                recipe TEXT NOT NULL,
                method TEXT NOT NULL,
                glassware TEXT NOT NULL,
                garnish TEXT NOT NULL,
                note TEXT NOT NULL,
                country TEXT NOT NULL,
                history TEXT NOT NULL
            )
        """)

# Insert data from the file into the database
def insert_data_to_db():
    with sqlite3.connect("bot.db") as conn:
        cursor = conn.cursor()

        with open("responses.txt", "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip().split(":")
                keyword = line[0].strip().lower()
                response = line[1].strip()
                image_path = line[2].strip()
                recipe = line[3].strip().replace("---", "\n- ").replace("(break)", "\n")
                method = line[4].strip().replace("---", "\n-").replace("(colon)", ":")
                glassware = line[5].strip().replace("---", "\n-")
                garnish = line[6].strip().replace("---", "\n-").replace("(colon)", ":")
                note = line[7].strip().replace("---", "\n- ").replace("(colon)", ":").replace("(break)", "\n")
                country = line[8].strip()
                history = line[9].strip().replace("---", "\n").replace("(colon)", ":")

                cursor.execute(
                    "INSERT OR REPLACE INTO responses (keyword, response, image_path, recipe, method, glassware, garnish, note, country, history) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (keyword, response, image_path, recipe, method, glassware, garnish, note, country, history)
                )

# Create the table and insert data if it's the first run
create_table()
insert_data_to_db()

# Dictionary to collect statistics
statistics = defaultdict(int)

# Command /start
@dp.message_handler(Command("start"))
async def cmd_start(message: types.Message):
    await message.reply("Привет\U0001F44B!\nЯ твой личный помощник в мире напитков.\nОтправь название коктейля, и я расскажу всё о рецептуре его приготовления>")

# Command /статистика_бота_для_меня
@dp.message_handler(Command("статистика_бота_для_меня"))
async def cmd_statistics(message: types.Message):
    stat_text = "Статистика использования чат-бота:\n"
    for user_id, count in statistics.items():
        user = await bot.get_chat(user_id)
        username = user.username or user.first_name or user_id
        stat_text += f"Пользователь {username}: {count} запросов\n"

    user_count = len(statistics)
    stat_text += f"\nВсего пользователей: {user_count}"

    if statistics:
        most_common_request = max(statistics, key=statistics.get)
        stat_text += f"\nСамый частый запрос: {most_common_request}"

    await message.reply(stat_text)

# Text messages handler
@dp.message_handler()
async def echo(message: types.Message):
    user_text = message.text.lower()

    user_id = message.from_user.id
    statistics[user_id] += 1

    with sqlite3.connect("bot.db") as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT response, image_path, recipe, method, glassware, garnish, note, country, history FROM responses WHERE keyword = ?", (user_text,))
        data = cursor.fetchone()

        if data:
            response, image_path, recipe, method, glassware, garnish, note, country, history = data

            full_response = f"""
{response}

{recipe}

{method}

{glassware}

{garnish}

{note}

━━━━━━━━━━━━━━━━━━━━
{country}

{history}
"""

            with open(image_path, "rb") as photo:
                # Отправляем только фотографию без подписи
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=InputFile(photo),
                    caption=None  # Устанавливаем подпись как None, чтобы не было подписи у фотографии
                )

            # Отправляем текст как отдельное сообщение без подписи
            await bot.send_message(
                chat_id=message.chat.id,
                text=full_response,
                parse_mode=ParseMode.HTML
            )
        else:
            await bot.send_message(
                chat_id=message.chat.id,
                text="Извините, я не могу найти ответ на Ваш запрос.\nПопробуйте в нём что-нибудь поменять."
            )

# Запускаем проверку соединения с Telegram API перед запуском бота
def check_connection(dp):
    try:
        bot.get_me()
        logging.info("Соединение с Telegram API успешно установлено")
    except Exception as e:
        logging.exception("Ошибка при проверке соединения с Telegram API: %s", e)

if __name__ == "__main__":
    dp.middleware.setup(LoggingMiddleware())
    executor.start_polling(dp)
