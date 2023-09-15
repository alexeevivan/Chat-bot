import logging
import os
import sqlite3
import html2text
from collections import defaultdict
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.types import InputFile, ParseMode, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from states import BotState
import config  # Import the file with bot settings (TOKEN)

logging.basicConfig(level=logging.INFO)
unique_users = set()

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
				response = line[1].strip().replace("(break)", "\n")
				image_path = line[2].strip()
				recipe = line[3].strip().replace("---", "\n- ").replace("(colon)", ":").replace("(break)", "\n")
				method = line[4].strip().replace("---", "\n-").replace("(colon)", ":").replace("(break)", "\n")
				glassware = line[5].strip().replace("---", "\n-")
				garnish = line[6].strip().replace("---", "\n-").replace("(colon)", ":")
				note = line[7].strip().replace("---", "\n- ").replace("(colon)", ":").replace("(break)", "\n")
				country = line[8].strip()
				history = line[9].strip().replace("---", "\n").replace("(colon)", ":").replace("(break)", "\n")

				cursor.execute(
					"INSERT OR REPLACE INTO responses (keyword, response, image_path, recipe, method, glassware, garnish, note, country, history) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
					(keyword, response, image_path, recipe, method, glassware, garnish, note, country, history)
				)

# Create the table and insert data if it's the first run
create_table()
insert_data_to_db()

# Dictionary to collect statistics
statistics = defaultdict(int)
# Dictionary to store user selected language
user_language = {}
# Welcome messages in different languages
welcome_messages = {
	"ru": "Привет\U0001F44B!\nЯ твой личный помощник в мире смешанных напитков. Я говорю на русском языке.\nОтправь название коктейля, и я расскажу всё о рецептуре его приготовления.",
	"en": "Hello\U0001F44B!\nI'm your personal assistant in the world of mixed drinks. I speak English.\nSend the name of a cocktail, and I'll tell you all about its recipe."
}
# Словарь с файлами для разных языков
language_files = {
    "ru": 'responses.txt',
    "en": 'responses_eng.txt',
}

# Command /setlang
@dp.message_handler(commands=["setlang"])
async def set_language(message: types.Message):
	user_id = message.from_user.id
	markup = InlineKeyboardMarkup()
	markup.add(
		InlineKeyboardButton(text="Русский", callback_data="set_language_ru"),
		InlineKeyboardButton(text="English", callback_data="set_language_en")
	)
	await message.answer("Выберите язык / Choose your language:", reply_markup=markup)

# Callback to set user's language
@dp.callback_query_handler(lambda query: query.data.startswith("set_language_"))
async def set_language(callback: CallbackQuery):
	user_id = callback.from_user.id
	language_code = callback.data.split("_")[2]

	# Store the selected language in the user_language dictionary
	user_language[user_id] = language_code

	# Send a welcome message in the selected language
	welcome_message = welcome_messages.get(language_code, welcome_messages["en"])
	await callback.message.answer(welcome_message)

	# Remove the language selection keyboard
	await callback.message.edit_reply_markup(reply_markup=None)

# Command /start
@dp.message_handler(Command("start"), state="*")
async def cmd_start(message: types.Message, state: FSMContext):
	user_id = message.from_user.id
	async with state.proxy() as data:
		if not data.get("greeted"):
			user_language_code = user_language.get(user_id, "en")
			welcome_message = welcome_messages.get(user_language_code, welcome_messages["en"])

			if user_language_code not in user_language:
				# Send language selection keyboard if the user hasn't selected a language
				markup = InlineKeyboardMarkup()
				markup.add(
					InlineKeyboardButton(text="Русский", callback_data="set_language_ru"),
					InlineKeyboardButton(text="English", callback_data="set_language_en")
				)
				await message.reply("Выберите язык / Choose your language:", reply_markup=markup)
			else:
				# Send the welcome message without a keyboard
				await message.reply(welcome_message, reply_markup=ReplyKeyboardRemove())

			data["greeted"] = True
		else:
			if user_language_code == "ru":
				await message.reply("С возвращением! Чем я могу вам помочь?")
			if user_language_code == "en":
				await message.reply("Welcome back! How can I help you?")
	await BotState.WaitForCocktailName.set()
	await state.finish()

# Command /restart_bot
@dp.message_handler(Command("restart_bot"), state="*")
async def cmd_restart_bot(message: types.Message, state: FSMContext):
	user_id = message.from_user.id
	async with state.proxy() as data:
		user_language_code = user_language.get(user_id, "ru")  # Получаем язык пользователя

		# Создаем клавиатуру с кнопками "Да" и "Нет"
		markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True, one_time_keyboard=True)
		if user_language_code == "ru":
			markup.add(KeyboardButton("Да"), KeyboardButton("Нет"))
		if user_language_code == "en":
			markup.add(KeyboardButton("Yes"), KeyboardButton("No"))

		# Создаем сообщение с учетом языка пользователя
		if user_language_code == "ru":
			confirmation_message = "Вы уверены, что хотите перезапустить бота? Вся история будет потеряна."
		else:
			confirmation_message = "Are you sure you want to restart the bot? All history will be lost."

		await message.reply(confirmation_message, reply_markup=markup)
		await BotState.RESTART_CONFIRMATION.set()


@dp.message_handler(lambda message: message.text.lower() in ["да", "нет", "yes", "no"], state=BotState.RESTART_CONFIRMATION)
async def restart_confirmation(message: types.Message, state: FSMContext):
	user_id = message.from_user.id
	async with state.proxy() as data:
		user_language_code = user_language.get(user_id, "ru")
		if message.text.lower() == "да" or "yes":
			await state.finish()  # Завершаем состояние подтверждения перезапуска
			if user_language_code == "ru":
				await message.reply("Бот был перезапущен.\nВоспользуйтесь командой \start для выбора возможных действий")
			if user_language_code == "en":
				await message.reply("The bot has been restarted.\nUse the \start command to select possible actions")

			# Спросите пользователя о выборе языка после перезапуска
			user_id = message.from_user.id
			user_language_code = user_language.get(user_id, "ru")
			welcome_message = welcome_messages.get(user_language_code, welcome_messages["ru"])

			if user_language_code not in user_language:
				# Send language selection keyboard if the user hasn't selected a language
				markup = InlineKeyboardMarkup()
				markup.add(
					InlineKeyboardButton(text="Русский", callback_data="set_language_ru"),
					InlineKeyboardButton(text="English", callback_data="set_language_en")
				)
				await message.reply("Выберите язык / Choose your language:", reply_markup=markup)
			else:
				# Send the welcome message without a keyboard
				await message.reply(welcome_message, reply_markup=ReplyKeyboardRemove())
		else:
			await state.finish()  # Завершаем состояние подтверждения перезапуска
			if user_language_code == "ru":
				await message.reply("Отменено. Бот продолжает работу.")
			if user_language_code == "en":
				await message.reply("Cancelled. The bot continues to work.")

@dp.message_handler(Command("статистика_бота_для_меня"))
async def cmd_statistics(message: types.Message):
	stat_text = "Статистика использования чат-бота:\n"

	issues_count = len(statistics)
	stat_text += f"\nВсего запросов: {issues_count}"

	user_count = len(unique_users)  # Подсчитываем количество уникальных пользователей
	stat_text += f"\nВсего пользователей: {user_count}"

	if statistics:
		most_common_request = max(statistics, key=lambda k: statistics[k][0])
		stat_text += f"\nСамый частый запрос: {most_common_request}"

	await message.reply(stat_text)

# Text messages handler
@dp.message_handler()
async def echo(message: types.Message):
	user_text = message.text.lower()
	user_id = message.from_user.id
	user_language_code = user_language.get(user_id, "ru")
	unique_users.add(user_id)

	if user_text in statistics:
		count, most_common_request = statistics[user_text]
		count += 1
		statistics[user_text] = (count, most_common_request)
	else:
		statistics[user_text] = (1, user_text)

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
			if user_language_code == "ru":
				await bot.send_message(
					chat_id=message.chat.id,
					text="Извините, я не могу найти ответ на Ваш запрос.\nПопробуйте в нём что-нибудь поменять."
				)
			if user_language_code == "en":
				await bot.send_message(
					chat_id=message.chat.id,
					text="Sorry, I can't find an answer to your query.\nTry to change something in it."
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