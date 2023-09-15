# states.py
from aiogram.dispatcher.filters.state import State, StatesGroup

class BotState(StatesGroup):
	INITIAL = State()  # Начальное состояние
	RESTART_CONFIRMATION = State()  # Состояние подтверждения перезапуска