# Файл: database.py

import sqlite3
import os
import sys
from datetime import datetime
import re
import hashlib

# --- Определение пути к базе данных ---
if getattr(sys, 'frozen', False):
    BASE_PATH = os.path.dirname(sys.executable)
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_PATH, "assistant.db")

class DatabaseManager:
    """Класс для управления всеми операциями с базой данных SQLite."""

    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self._create_tables()
        

    def _get_connection(self):
        """Создает и возвращает соединение с базой данных."""
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row  # Позволяет обращаться к колонкам по имени
        return con

    def _create_tables(self):
        """Создает таблицы, если они еще не существуют."""
        with self._get_connection() as con:
            cursor = con.cursor()
            # Таблица для заметок и папок (древовидная структура)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_id INTEGER,
                    type TEXT NOT NULL CHECK(type IN ('folder', 'note')),
                    title TEXT,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_pinned INTEGER DEFAULT 0,
                    is_hidden INTEGER DEFAULT 0,
                    password_hash TEXT,
                    FOREIGN KEY (parent_id) REFERENCES notes (id) ON DELETE CASCADE
                )
            """)
            
            # Таблица для списков задач
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    order_index INTEGER
                )
            """)

            # Таблица для самих задач
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    list_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    is_completed INTEGER DEFAULT 0,
                    order_index INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (list_id) REFERENCES task_lists (id) ON DELETE CASCADE
                )
            """)
            
            # Триггеры для автоматического обновления поля updated_at
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_note_timestamp
                AFTER UPDATE ON notes
                FOR EACH ROW
                BEGIN
                    UPDATE notes SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
                END;
            """)

            # Проверяем, есть ли хоть один список задач, если нет - создаем "Default"
            cursor.execute("SELECT COUNT(*) FROM task_lists")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO task_lists (name, order_index) VALUES (?, ?)", ("Default", 0))

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS security (
                    id INTEGER PRIMARY KEY CHECK (id = 1), -- Гарантирует только одну строку
                    password_hash TEXT,
                    question1 TEXT,
                    answer1_hash TEXT,
                    question2 TEXT,
                    answer2_hash TEXT
                )
            """)

            con.commit()

    # --- Методы для работы с Заметками и Папками ---

    def get_note_tree(self):
        """
        Извлекает все заметки и папки и строит из них древовидную структуру.
        Возвращает список словарей.
        """
        with self._get_connection() as con:
            cursor = con.cursor()
            cursor.execute("SELECT id, parent_id, type, title, is_pinned FROM notes ORDER BY title COLLATE NOCASE")
            rows = cursor.fetchall()
            
            nodes = {row['id']: dict(row) for row in rows}
            tree = []
            
            for node_id, node in nodes.items():
                if node['parent_id'] is None:
                    tree.append(node)
                else:
                    parent = nodes.get(node['parent_id'])
                    if parent:
                        if 'children' not in parent:
                            parent['children'] = []
                        parent['children'].append(node)
            
            # Сортировка: сначала папки, потом заметки, затем по названию
            def sort_key(item):
                is_folder = 1 if item['type'] == 'folder' else 2
                is_pinned = 0 if item.get('is_pinned', 0) else 1
                return (is_pinned, is_folder, item['title'])

            def sort_tree(nodes_list):
                nodes_list.sort(key=sort_key)
                for node in nodes_list:
                    if 'children' in node:
                        sort_tree(node['children'])
            
            sort_tree(tree)
            return tree
            
    def get_all_notes_flat(self):
        """Возвращает плоский список всех заметок со всем их содержимым."""
        with self._get_connection() as con:
            cursor = con.cursor()
            cursor.execute("SELECT id, content, created_at FROM notes WHERE type = 'note'")
            return [dict(row) for row in cursor.fetchall()]

    def get_all_notes_for_refresh(self):
        """Возвращает плоский список всех заметок с полями для обновления UI."""
        with self._get_connection() as con:
            cursor = con.cursor()
            cursor.execute("SELECT id, title, is_pinned FROM notes WHERE type = 'note'")
            return [dict(row) for row in cursor.fetchall()]

    def get_note_details(self, note_id):
        """Возвращает полную информацию о заметке по ее ID."""
        with self._get_connection() as con:
            cursor = con.cursor()
            cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_note(self, parent_id, title="Новая заметка", content=""):
        """Создает новую заметку."""
        # --- НОВАЯ ЛОГИКА: Генерируем title без хештегов ---
        if not title and content:
            first_line = content.split('\n', 1)[0].strip()
            # Удаляем все символы # из первой строки для создания заголовка
            clean_title = re.sub(r'#', '', first_line).strip()
            title = clean_title or "Новая заметка"
        elif title:
            clean_title = re.sub(r'#', '', title).strip()
            title = clean_title or "Новая заметка"
        # --- КОНЕЦ НОВОЙ ЛОГИКИ ---
            
        with self._get_connection() as con:
            cursor = con.cursor()
            cursor.execute(
                "INSERT INTO notes (parent_id, type, title, content) VALUES (?, 'note', ?, ?)",
                (parent_id, title, content)
            )
            con.commit()
            return cursor.lastrowid

    def create_folder(self, parent_id, title="Новая папка"):
        """Создает новую папку."""
        with self._get_connection() as con:
            cursor = con.cursor()
            cursor.execute(
                "INSERT INTO notes (parent_id, type, title) VALUES (?, 'folder', ?)",
                (parent_id, title)
            )
            con.commit()
            return cursor.lastrowid

    def update_note_content(self, note_id, title, content):
        """Обновляет заголовок и содержимое заметки."""
        # --- НОВАЯ ЛОГИКА: Очищаем title от хештегов ---
        if title:
            clean_title = re.sub(r'#', '', title).strip()
            title = clean_title or "Обновленная заметка"
        # --- КОНЕЦ НОВОЙ ЛОГИКИ ---
        
        with self._get_connection() as con:
            con.execute(
                "UPDATE notes SET title = ?, content = ? WHERE id = ?",
                (title, content, note_id)
            )
            con.commit()

    def delete_note_or_folder(self, item_id):
        """Удаляет заметку или папку (и все ее содержимое)."""
        with self._get_connection() as con:
            # Благодаря ON DELETE CASCADE, удаление папки удалит все вложенные элементы.
            con.execute("DELETE FROM notes WHERE id = ?", (item_id,))
            con.commit()

        # --- НОВЫЕ МЕТОДЫ ДЛЯ ПЕРЕМЕЩЕНИЯ ---
    def move_item(self, item_id, new_parent_id):
        """Перемещает заметку или папку к новому родителю."""
        with self._get_connection() as con:
            # new_parent_id может быть None для перемещения в корень
            con.execute("UPDATE notes SET parent_id = ? WHERE id = ?", (new_parent_id, item_id))
            con.commit()

    def update_item_parent_and_order(self, item_id, new_parent_id, siblings_ids):
        """
        Обновляет родителя для элемента и порядок всех элементов
        на том же уровне.
        """
        with self._get_connection() as con:
            cursor = con.cursor()
            # 1. Обновляем родителя для перетаскиваемого элемента
            cursor.execute("UPDATE notes SET parent_id = ? WHERE id = ?", (new_parent_id, item_id))
            
            # 2. Обновляем порядок для всех "соседей"
            # (эта часть пока не используется, но будет полезна для сортировки)
            # for index, sibling_id in enumerate(siblings_ids):
            #     cursor.execute("UPDATE notes SET order_index = ? WHERE id = ?", (index, sibling_id))

            con.commit()

    def get_parent_id(self, item_id):
        """Возвращает ID родителя для указанного элемента."""
        with self._get_connection() as con:
            cursor = con.cursor()
            cursor.execute("SELECT parent_id FROM notes WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            return row['parent_id'] if row else None
    # --- КОНЕЦ НОВЫХ МЕТОДОВ ---


    # --- Методы для работы с Задачами ---

    def get_all_task_lists(self):
        """Возвращает все списки задач."""
        with self._get_connection() as con:
            cursor = con.cursor()
            cursor.execute("SELECT id, name FROM task_lists ORDER BY order_index, name")
            return [dict(row) for row in cursor.fetchall()]

    def get_tasks_for_list(self, list_id):
        """Возвращает все задачи для конкретного списка."""
        with self._get_connection() as con:
            cursor = con.cursor()
            cursor.execute(
                "SELECT id, content, is_completed FROM tasks WHERE list_id = ? ORDER BY order_index, created_at",
                (list_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def add_task(self, list_id, content):
        """Добавляет новую задачу в список."""
        with self._get_connection() as con:
            con.execute(
                "INSERT INTO tasks (list_id, content) VALUES (?, ?)",
                (list_id, content)
            )
            con.commit()

    def update_task(self, task_id, new_content=None, is_completed=None):
        """Обновляет текст или статус выполнения задачи."""
        with self._get_connection() as con:
            if new_content is not None:
                con.execute("UPDATE tasks SET content = ? WHERE id = ?", (new_content, task_id))
            if is_completed is not None:
                con.execute("UPDATE tasks SET is_completed = ? WHERE id = ?", (is_completed, task_id))
            con.commit()

    def delete_task(self, task_id):
        """Удаляет задачу."""
        with self._get_connection() as con:
            con.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            con.commit()

    def update_tasks_order(self, list_id, ordered_task_ids):
        """Обновляет порядок задач в списке."""
        with self._get_connection() as con:
            cursor = con.cursor()
            for index, task_id in enumerate(ordered_task_ids):
                cursor.execute(
                    "UPDATE tasks SET order_index = ? WHERE id = ? AND list_id = ?",
                    (index, task_id, list_id)
                )
            con.commit()


        # --- НОВЫЕ МЕТОДЫ ДЛЯ СПИСКОВ ЗАДАЧ ---
    def add_task_list(self, name):
        """Добавляет новый список задач."""
        with self._get_connection() as con:
            cursor = con.cursor()
            cursor.execute("SELECT MAX(order_index) FROM task_lists")
            max_order = cursor.fetchone()[0]
            next_order = (max_order or 0) + 1
            cursor.execute("INSERT INTO task_lists (name, order_index) VALUES (?, ?)", (name, next_order))
            con.commit()
            return cursor.lastrowid

    def rename_task_list(self, list_id, new_name):
        """Переименовывает список задач."""
        with self._get_connection() as con:
            con.execute("UPDATE task_lists SET name = ? WHERE id = ?", (new_name, list_id))
            con.commit()

    def delete_task_list(self, list_id):
        """Удаляет список задач и все задачи в нем."""
        with self._get_connection() as con:
            # ON DELETE CASCADE в схеме автоматически удалит все задачи
            con.execute("DELETE FROM task_lists WHERE id = ?", (list_id,))
            con.commit()

    def rename_item(self, item_id, new_title):
        """Обновляет ТОЛЬКО заголовок заметки или папки."""
        clean_title = re.sub(r'#', '', new_title).strip()
        if not clean_title:
            clean_title = "Без названия"
            
        with self._get_connection() as con:
            con.execute(
                "UPDATE notes SET title = ? WHERE id = ?",
                (clean_title, item_id)
            )
            con.commit()

    # --- НОВЫЙ МЕТОД ПОИСКА ---
    def search_notes(self, search_text="", tag=""):
        """
        Ищет заметки по тексту и/или тегу.
        Возвращает список ID подходящих заметок.
        """
        with self._get_connection() as con:
            cursor = con.cursor()
            
            query = "SELECT id FROM notes WHERE type = 'note'"
            params = []
            
            if search_text:
                # Ищем в заголовке ИЛИ в контенте
                query += " AND (title LIKE ? OR content LIKE ?)"
                params.extend([f'%{search_text}%', f'%{search_text}%'])
            
            if tag:
                # Ищем тег как отдельное слово
                query += " AND content LIKE ?"
                params.append(f'%#{tag}%')
            
            cursor.execute(query, params)
            return [row['id'] for row in cursor.fetchall()]

    def get_all_tags(self):
        """Извлекает все теги из всех заметок."""
        with self._get_connection() as con:
            cursor = con.cursor()
            cursor.execute("SELECT content FROM notes WHERE type = 'note'")
            all_content = [row['content'] for row in cursor.fetchall() if row['content']]
            
            tags = set()
            for text in all_content:
                found = re.findall(r'#(\w+)', text)
                tags.update(found)
            return sorted(list(tags))
    # --- КОНЕЦ ---
    def remove_tag_from_all_notes(self, tag):
        """Удаляет указанный тег (#tag) из всех заметок."""
        with self._get_connection() as con:
            cursor = con.cursor()
            cursor.execute("SELECT id, content FROM notes WHERE type = 'note' AND content LIKE ?", (f'%#{tag}%',))
            notes_to_update = cursor.fetchall()

            for note in notes_to_update:
                note_id = note['id']
                old_content = note['content']
                # Заменяем тег, учитывая, что он может быть отдельным словом
                new_content = re.sub(r'\s*#' + re.escape(tag) + r'\b', ' ', old_content).strip()
                
                # Обновляем заголовок, если он изменился
                new_title = new_content.split('\n', 1)[0].strip() or "Без названия"
                clean_title = re.sub(r'#', '', new_title).strip()

                con.execute(
                    "UPDATE notes SET title = ?, content = ? WHERE id = ?",
                    (new_content, clean_title, note_id)
                )
            con.commit()

    # --- НОВЫЕ МЕТОДЫ ДЛЯ БЕЗОПАСНОСТИ ---
    def _hash_string(self, text):
        """Хеширует строку с использованием SHA-256."""
        if not text:
            return None
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def is_password_set(self):
        """Проверяет, установлен ли пароль в приложении."""
        with self._get_connection() as con:
            cursor = con.cursor()
            cursor.execute("SELECT password_hash FROM security WHERE id = 1")
            row = cursor.fetchone()
            return row is not None and row['password_hash'] is not None

    def set_password_and_questions(self, password, q1, a1, q2, a2):
        """
        Устанавливает или обновляет пароль и контрольные вопросы.
        """
        with self._get_connection() as con:
            cursor = con.cursor()
            cursor.execute("SELECT * FROM security WHERE id = 1")
            existing = cursor.fetchone()

            # --- УПРОЩЕННАЯ И НАДЕЖНАЯ ЛОГИКА ---
            pass_hash = self._hash_string(password) if password else (existing['password_hash'] if existing and password is None else None)
            
            # Если ответ не предоставлен, сохраняем старый хэш ответа, если он был
            ans1_hash = self._hash_string(a1.lower().strip()) if a1 else (existing['answer1_hash'] if existing and a1 is None else None)
            ans2_hash = self._hash_string(a2.lower().strip()) if a2 else (existing['answer2_hash'] if existing and a2 is None else None)

            # Если записи еще нет, создаем ее
            if not existing:
                con.execute(
                    "INSERT INTO security (id, password_hash, question1, answer1_hash, question2, answer2_hash) VALUES (1, ?, ?, ?, ?, ?)",
                    (pass_hash, q1, ans1_hash, q2, ans2_hash)
                )
            else: # Иначе, обновляем
                con.execute(
                    """
                    UPDATE security SET
                        password_hash = ?, question1 = ?, answer1_hash = ?,
                        question2 = ?, answer2_hash = ?
                    WHERE id = 1
                    """,
                    (pass_hash, q1, ans1_hash, q2, ans2_hash)
                )
            
            con.commit()
            # --- КОНЕЦ ---

    def check_password(self, password):
        """Проверяет правильность введенного пароля."""
        if not self.is_password_set():
            return True # Если пароль не установлен, доступ разрешен
        
        pass_hash = self._hash_string(password)
        with self._get_connection() as con:
            cursor = con.cursor()
            cursor.execute("SELECT password_hash FROM security WHERE id = 1")
            row = cursor.fetchone()
            return row and row['password_hash'] == pass_hash

    def get_security_questions(self):
        """Возвращает контрольные вопросы."""
        with self._get_connection() as con:
            cursor = con.cursor()
            cursor.execute("SELECT question1, question2 FROM security WHERE id = 1")
            row = cursor.fetchone()
            return (row['question1'], row['question2']) if row else (None, None)

    def check_security_answers(self, a1, a2):
        """Проверяет ответы на контрольные вопросы."""
        # --- ИСПРАВЛЕНИЕ: Хешируем введенные ответы ПЕРЕД сравнением ---
        ans1_hash_to_check = self._hash_string(a1.lower().strip())
        ans2_hash_to_check = self._hash_string(a2.lower().strip())
        # --- КОНЕЦ ---

        with self._get_connection() as con:
            cursor = con.cursor()
            cursor.execute("SELECT answer1_hash, answer2_hash FROM security WHERE id = 1")
            row = cursor.fetchone()
            
            # Сравниваем хэш с хэшем
            return (row and 
                    row['answer1_hash'] == ans1_hash_to_check and
                    (row['answer2_hash'] == ans2_hash_to_check or not row['answer2_hash'])) # Учитываем, что второго ответа может не быть

    def reset_all_data(self):
        """Создает флаг для сброса данных при следующем запуске."""
        try:
            flag_file = os.path.join(BASE_PATH, "_reset.flag")
            with open(flag_file, 'w') as f:
                f.write('reset')
            return True
        except Exception as e:
            print(f"Ошибка при создании флага сброса: {e}")
            return False
    # --- КОНЕЦ ---

    
    def get_full_note_tree(self):
        """Извлекает полное дерево заметок со всем содержимым."""
        with self._get_connection() as con:
            cursor = con.cursor()
            # Выбираем все поля
            cursor.execute("SELECT id, parent_id, type, title, content, is_pinned FROM notes ORDER BY title COLLATE NOCASE")
            rows = cursor.fetchall()
            
            nodes = {row['id']: dict(row) for row in rows}
            tree = []
            
            for node_id, node in nodes.items():
                if node['parent_id'] is None:
                    tree.append(node)
                else:
                    parent = nodes.get(node['parent_id'])
                    if parent:
                        if 'children' not in parent:
                            parent['children'] = []
                        parent['children'].append(node)
            
            def sort_key(item):
                is_folder = 1 if item['type'] == 'folder' else 2
                return (is_folder, item['title'])

            def sort_tree(nodes_list):
                nodes_list.sort(key=sort_key)
                for node in nodes_list:
                    if 'children' in node:
                        sort_tree(node['children'])
            
            sort_tree(tree)
            return tree