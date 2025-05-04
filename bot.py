import os
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Конфигурация бота
BOT_TOKEN = '7582181232:AAHq281v3UmM19PFbzm6aKTuxqWm0VOSON4'
ADMIN_ID = 821813435  # Замените на ваш Telegram ID

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Создаем папки для хранения данных
if not os.path.exists('data'):
    os.makedirs('data')
if not os.path.exists('data/files'):
    os.makedirs('data/files')

# Инициализация базы данных
conn = sqlite3.connect('data/bot_database.db')
cursor = conn.cursor()

# Создаем таблицы, если они не существуют
cursor.execute('''
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    file_id TEXT,
    file_name TEXT,
    file_type TEXT,
    caption TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

# Состояния FSM
class Form(StatesGroup):
    note_title = State()
    note_content = State()
    edit_note = State()
    edit_note_content = State()
    file_upload = State()
    file_caption = State()

# Проверка на администратора
def is_admin(user_id):
    return user_id == ADMIN_ID

# Главное меню
def get_main_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton('📝 Заметки'))
    menu.add(KeyboardButton('📁 Файлы'))
    return menu

# Меню заметок
def get_notes_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton('📋 Список заметок'))
    menu.add(KeyboardButton('➕ Новая заметка'))
    menu.add(KeyboardButton('🔙 Назад'))
    return menu

# Меню файлов
def get_files_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton('📂 Список файлов'))
    menu.add(KeyboardButton('⬆️ Загрузить файл'))
    menu.add(KeyboardButton('🔙 Назад'))
    return menu

# Кнопки отмены
def get_cancel_button():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('❌ Отмена'))

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен. Вы не администратор.")
        return
    
    await message.answer("👋 Добро пожаловать в админ-панель!", reply_markup=get_main_menu())

# Обработчик кнопки "Назад"
@dp.message_handler(lambda message: message.text == '🔙 Назад')
async def cmd_back(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer("Главное меню:", reply_markup=get_main_menu())

# Обработчик кнопки "Заметки"
@dp.message_handler(lambda message: message.text == '📝 Заметки')
async def cmd_notes(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer("Меню заметок:", reply_markup=get_notes_menu())

# Обработчик кнопки "Файлы"
@dp.message_handler(lambda message: message.text == '📁 Файлы')
async def cmd_files(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer("Меню файлов:", reply_markup=get_files_menu())

# Обработчик кнопки "Список заметок"
@dp.message_handler(lambda message: message.text == '📋 Список заметок')
async def cmd_notes_list(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    cursor.execute('SELECT id, title FROM notes WHERE user_id = ? ORDER BY created_at DESC', (message.from_user.id,))
    notes = cursor.fetchall()
    
    if not notes:
        await message.answer("У вас пока нет заметок.")
        return
    
    keyboard = InlineKeyboardMarkup()
    for note in notes:
        keyboard.add(InlineKeyboardButton(note[1], callback_data=f'view_note_{note[0]}'))
    
    await message.answer("Ваши заметки:", reply_markup=keyboard)

# Обработчик кнопки "Новая заметка"
@dp.message_handler(lambda message: message.text == '➕ Новая заметка')
async def cmd_new_note(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    await Form.note_title.set()
    await message.answer("Введите название заметки:", reply_markup=get_cancel_button())

# Обработчик отмены
@dp.message_handler(lambda message: message.text == '❌ Отмена', state='*')
async def cmd_cancel(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.finish()
    await message.answer("Действие отменено.", reply_markup=get_main_menu())

# Обработчик ввода названия заметки
@dp.message_handler(state=Form.note_title)
async def process_note_title(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['note_title'] = message.text
    
    await Form.next()
    await message.answer("Введите содержание заметки:")

# Обработчик ввода содержания заметки
@dp.message_handler(state=Form.note_content)
async def process_note_content(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        title = data['note_title']
        content = message.text
        
        cursor.execute('INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)', 
                      (message.from_user.id, title, content))
        conn.commit()
        
        await message.answer(f"Заметка '{title}' успешно сохранена!", reply_markup=get_main_menu())
    
    await state.finish()

# Обработчик просмотра заметки
@dp.callback_query_handler(lambda c: c.data.startswith('view_note_'))
async def callback_view_note(callback_query: types.CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        return
    
    note_id = callback_query.data.split('_')[-1]
    
    cursor.execute('SELECT title, content FROM notes WHERE id = ? AND user_id = ?', 
                  (note_id, callback_query.from_user.id))
    note = cursor.fetchone()
    
    if note:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("✏️ Редактировать", callback_data=f'edit_note_{note_id}'))
        keyboard.add(InlineKeyboardButton("🗑️ Удалить", callback_data=f'delete_note_{note_id}'))
        
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, 
                             f"📌 <b>{note[0]}</b>\n\n{note[1]}", 
                             parse_mode='HTML', 
                             reply_markup=keyboard)
    else:
        await bot.answer_callback_query(callback_query.id, "Заметка не найдена.")

# Обработчик редактирования заметки
@dp.callback_query_handler(lambda c: c.data.startswith('edit_note_'))
async def callback_edit_note(callback_query: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback_query.from_user.id):
        return
    
    note_id = callback_query.data.split('_')[-1]
    
    async with state.proxy() as data:
        data['note_id'] = note_id
    
    await Form.edit_note_content.set()
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, 
                          "Введите новое содержание заметки:", 
                          reply_markup=get_cancel_button())

# Обработчик сохранения изменений заметки
@dp.message_handler(state=Form.edit_note_content)
async def process_edit_note_content(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        note_id = data['note_id']
        new_content = message.text
        
        cursor.execute('UPDATE notes SET content = ? WHERE id = ? AND user_id = ?', 
                      (new_content, note_id, message.from_user.id))
        conn.commit()
        
        cursor.execute('SELECT title FROM notes WHERE id = ?', (note_id,))
        title = cursor.fetchone()[0]
        
        await message.answer(f"Заметка '{title}' успешно обновлена!", reply_markup=get_main_menu())
    
    await state.finish()

# Обработчик удаления заметки
@dp.callback_query_handler(lambda c: c.data.startswith('delete_note_'))
async def callback_delete_note(callback_query: types.CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        return
    
    note_id = callback_query.data.split('_')[-1]
    
    cursor.execute('SELECT title FROM notes WHERE id = ? AND user_id = ?', 
                  (note_id, callback_query.from_user.id))
    note = cursor.fetchone()
    
    if note:
        cursor.execute('DELETE FROM notes WHERE id = ?', (note_id,))
        conn.commit()
        
        await bot.answer_callback_query(callback_query.id, f"Заметка '{note[0]}' удалена")
        await bot.send_message(callback_query.from_user.id, 
                             "Заметка удалена.", 
                             reply_markup=get_main_menu())
    else:
        await bot.answer_callback_query(callback_query.id, "Заметка не найдена.")

# Обработчик кнопки "Список файлов"
@dp.message_handler(lambda message: message.text == '📂 Список файлов')
async def cmd_files_list(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    cursor.execute('SELECT id, file_name, file_type FROM files WHERE user_id = ? ORDER BY uploaded_at DESC', 
                  (message.from_user.id,))
    files = cursor.fetchall()
    
    if not files:
        await message.answer("У вас пока нет файлов.")
        return
    
    keyboard = InlineKeyboardMarkup()
    for file in files:
        keyboard.add(InlineKeyboardButton(f"{file[1]} ({file[2]})", callback_data=f'view_file_{file[0]}'))
    
    await message.answer("Ваши файлы:", reply_markup=keyboard)

# Обработчик кнопки "Загрузить файл"
@dp.message_handler(lambda message: message.text == '⬆️ Загрузить файл')
async def cmd_upload_file(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    await Form.file_upload.set()
    await message.answer("Отправьте файл для загрузки:", reply_markup=get_cancel_button())

# Обработчик загрузки файла
@dp.message_handler(content_types=['document', 'photo', 'video', 'audio'], state=Form.file_upload)
async def process_file_upload(message: types.Message, state: FSMContext):
    file_id = None
    file_name = None
    file_type = None
    
    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name
        file_type = message.document.mime_type
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_name = f"photo_{file_id}.jpg"
        file_type = "image/jpeg"
    elif message.video:
        file_id = message.video.file_id
        file_name = message.video.file_name if message.video.file_name else f"video_{file_id}.mp4"
        file_type = message.video.mime_type
    elif message.audio:
        file_id = message.audio.file_id
        file_name = message.audio.file_name if message.audio.file_name else f"audio_{file_id}.mp3"
        file_type = message.audio.mime_type
    
    if file_id:
        async with state.proxy() as data:
            data['file_id'] = file_id
            data['file_name'] = file_name
            data['file_type'] = file_type
        
        await Form.next()
        await message.answer("Введите описание для файла (или нажмите 'Пропустить'):", 
                            reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
                            .add(KeyboardButton('Пропустить'))
                            .add(KeyboardButton('❌ Отмена')))
    else:
        await message.answer("Не удалось обработать файл. Попробуйте еще раз.")

# Обработчик описания файла
@dp.message_handler(state=Form.file_caption)
async def process_file_caption(message: types.Message, state: FSMContext):
    caption = message.text if message.text != 'Пропустить' else None
    
    async with state.proxy() as data:
        file_id = data['file_id']
        file_name = data['file_name']
        file_type = data['file_type']
        
        cursor.execute('INSERT INTO files (user_id, file_id, file_name, file_type, caption) VALUES (?, ?, ?, ?, ?)', 
                      (message.from_user.id, file_id, file_name, file_type, caption))
        conn.commit()
        
        await message.answer(f"Файл '{file_name}' успешно сохранен!", reply_markup=get_main_menu())
    
    await state.finish()

# Обработчик просмотра файла
@dp.callback_query_handler(lambda c: c.data.startswith('view_file_'))
async def callback_view_file(callback_query: types.CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        return
    
    file_id = callback_query.data.split('_')[-1]
    
    cursor.execute('SELECT file_id, file_name, file_type, caption FROM files WHERE id = ? AND user_id = ?', 
                  (file_id, callback_query.from_user.id))
    file_data = cursor.fetchone()
    
    if file_data:
        file_id, file_name, file_type, caption = file_data
        caption_text = f"📄 <b>{file_name}</b>\n\n{caption if caption else 'Без описания'}"
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🗑️ Удалить", callback_data=f'delete_file_{file_id}'))
        
        try:
            if file_type.startswith('image'):
                await bot.send_photo(callback_query.from_user.id, file_id, caption=caption_text, 
                                   parse_mode='HTML', reply_markup=keyboard)
            elif file_type.startswith('video'):
                await bot.send_video(callback_query.from_user.id, file_id, caption=caption_text, 
                                   parse_mode='HTML', reply_markup=keyboard)
            elif file_type.startswith('audio'):
                await bot.send_audio(callback_query.from_user.id, file_id, caption=caption_text, 
                                   parse_mode='HTML', reply_markup=keyboard)
            else:
                await bot.send_document(callback_query.from_user.id, file_id, caption=caption_text, 
                                      parse_mode='HTML', reply_markup=keyboard)
        except Exception as e:
            await bot.send_message(callback_query.from_user.id, 
                                 f"Не удалось отправить файл. Ошибка: {str(e)}")
        
        await bot.answer_callback_query(callback_query.id)
    else:
        await bot.answer_callback_query(callback_query.id, "Файл не найден.")

# Обработчик удаления файла
@dp.callback_query_handler(lambda c: c.data.startswith('delete_file_'))
async def callback_delete_file(callback_query: types.CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        return
    
    file_db_id = callback_query.data.split('_')[-1]
    
    cursor.execute('SELECT file_name FROM files WHERE id = ? AND user_id = ?', 
                  (file_db_id, callback_query.from_user.id))
    file_data = cursor.fetchone()
    
    if file_data:
        cursor.execute('DELETE FROM files WHERE id = ?', (file_db_id,))
        conn.commit()
        
        await bot.answer_callback_query(callback_query.id, f"Файл '{file_data[0]}' удален")
        await bot.send_message(callback_query.from_user.id, 
                             "Файл удален.", 
                             reply_markup=get_main_menu())
    else:
        await bot.answer_callback_query(callback_query.id, "Файл не найден.")

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    executor.start_polling(dp, skip_updates=True)