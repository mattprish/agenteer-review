from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает основную клавиатуру"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📄 Загрузить статью")],
            [KeyboardButton(text="ℹ️ Помощь"), KeyboardButton(text="⚙️ О системе")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

def get_help_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру помощи"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📖 Как использовать", callback_data="help_usage")],
            [InlineKeyboardButton(text="🔧 Технические требования", callback_data="help_tech")],
            [InlineKeyboardButton(text="❓ FAQ", callback_data="help_faq")]
        ]
    )
    return keyboard

def get_back_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру с кнопкой назад"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_help")]
        ]
    )
    return keyboard

def get_processing_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру во время обработки"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏹ Отменить", callback_data="cancel_processing")]
        ]
    )
    return keyboard

def get_results_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для результатов"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Загрузить новую статью", callback_data="new_paper")],
            [InlineKeyboardButton(text="📊 Подробный отчет", callback_data="detailed_report")]
        ]
    )
    return keyboard