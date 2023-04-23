import logging
from aiogram import Bot, Dispatcher, executor, types

# настройка логирования
logging.basicConfig(level=logging.INFO)

# создание объекта бота
bot = Bot(token='ваш токен')

# создание диспетчера
dp = Dispatcher(bot)

# загрузка ответов из файла
with open('answers.txt', 'r', encoding='utf-8') as f:
    answers = f.readlines()
    answers = [line.strip() for line in answers]

# обработка команды /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Я бот, который отвечает на ваши вопросы. Что вас интересует?")

# обработка сообщений
@dp.message_handler()
async def answer(message: types.Message):
    if message.text.lower() in answers:
        # находим индекс ответа в списке
        index = answers.index(message.text.lower())
        with open('responses.txt', 'r', encoding='utf-8') as f:
            # находим ответ по индексу
            response = f.readlines()[index].strip()
        await message.answer(response)
    else:
        await message.answer("Извините, я не понимаю, о чем вы говорите. Попробуйте спросить что-то другое.")

# запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)