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