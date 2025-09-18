import sys
import json
import os
import re
import shutil
from datetime import datetime
from glob import glob

from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QScrollArea,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QHBoxLayout, QCheckBox, QTextEdit, QSplitter,
    QStyle, QMenu, QDialog, QFileDialog, QDialogButtonBox,
    QRadioButton, QMessageBox, QSpinBox, QInputDialog, QComboBox,
    QFontComboBox, QButtonGroup, QColorDialog, QTabWidget, QStatusBar,
    QToolButton, QAbstractItemView, QFrame, QPlainTextEdit, QAbstractSpinBox,
    QTreeWidget, QTreeWidgetItem, QSlider, QStackedWidget, QStyleOption, QGridLayout, QSizePolicy, QSizeGrip, QMainWindow, QLayout,
    QGroupBox
)
from PyQt6.QtCore import (
    Qt, QPoint, QRectF, QUrl, QPropertyAnimation, QEasingCurve, pyqtSignal, QByteArray,
    QSize, QTimer, QEvent, QParallelAnimationGroup, QObject, QDateTime, QRect, QMargins, QPointF
)
from PyQt6.QtGui import (
    QAction, QMouseEvent, QPainter, QPixmap, QColor, QFont, QIcon, QTextCursor,
    QScreen, QKeySequence, QShortcut, QLinearGradient, QPolygonF, QPalette, QFontDatabase, QTextOption
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtSvg import QSvgRenderer

from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrinter
# Если QPdfWriter не импортируется из QtGui, попробуйте этот вариант
try:
    from PyQt6.QtGui import QPdfWriter
except ImportError:
    from PyQt6.QtPrintSupport import QPdfWriter
    
from PyQt6.QtWidgets import QTextBrowser
import markdown

from database import DatabaseManager

# --- Файлы и константы ---

if getattr(sys, 'frozen', False):
    BASE_PATH = os.path.dirname(sys.executable)
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

SETTINGS_FILE = os.path.join(BASE_PATH, "settings.json")
DATA_FILE = os.path.join(BASE_PATH, "data.json")
BACKUP_DIR = os.path.join(BASE_PATH, "backups")


DEFAULT_SETTINGS = {
    "language": "ru_RU",
    "theme": "light",
    "trigger_pos": "right",
    "accent_color": "#00aa88",
    "notes_tree_enabled": True,

    "light_theme_bg": "#f8f9fa",
    "light_theme_text": "#212529",
    "light_theme_list_text": "#212529",
    "dark_theme_bg": "#2b2b2b",
    "dark_theme_text": "#e6e6e6",
    "dark_theme_list_text": "#bbbbbb",

    "zen_bg_path": "",
    "zen_light_theme_bg": "#F5F5DC",
    "zen_dark_theme_bg": "#1c1c1c",
    "zen_editor_opacity": 85,
    "zen_padding_horiz": 20,
    "zen_padding_vert": 5,
    "zen_font_family": "Candara",
    "zen_font_size": 16,
    "zen_font_color": "",
    "zen_alignment": "left",

    "popup_notes_splitter_sizes": [200, 200],
    "popup_main_splitter_sizes": [250, 400],

    "window_v_splitter_proportions": [0.7, 0.3], # (лево+центр) / право
    "window_h_splitter_proportions": [0.35, 0.65], # лево / центр

    "window_geometry": "",
    "window_left_visible": True,
    "window_right_visible": True,
    "window_editor_font_size": 0,
    "window_min_width_left": 260,
    "window_min_width_right": 380,
    "window_min_width_center": 400,

    "editor_padding_top": 8,
    "editor_padding_bottom": 8,
    "editor_padding_left": 10,
    "editor_padding_right": 10,

    "autosave_interval_sec": 10,
    "task_templates": ["Позвонить ...", "Купить ...", "Написать ...", "Сделать ..."],

    # Новые настройки для бэкапов
    "backup_interval_min": 60,
    "backup_max_count": 10,

    "pdf_font_family": "Times New Roman",
    "pdf_font_size": 11,
    "pdf_text_color": "#000000",
    "pdf_bg_color": "#ffffff",
    "pdf_margin_top": 20,
    "pdf_margin_bottom": 20,
    "pdf_margin_left": 15,
    "pdf_margin_right": 15,
    "popup_editor_font_size": 12,
    "startup_mode": "panel", # "panel", "window"
    "zen_background_type": "procedural", # "color", "procedural", "image"
}

POMODORO_WORK_TIME = 25 * 60
POMODORO_BREAK_TIME = 5 * 60

def resolve_path(relative_or_absolute_path):
    """Преобразует относительный путь в абсолютный, оставляя абсолютные без изменений."""
    if not relative_or_absolute_path:
        return ""
    if os.path.isabs(relative_or_absolute_path):
        return relative_or_absolute_path
    return os.path.join(BASE_PATH, relative_or_absolute_path)

# --- Утилиты ---

def theme_colors(settings: dict):
    """Возвращает набор цветов в зависимости от выбранной темы."""
    theme = settings.get("theme", "light")
    accent = settings.get("accent_color", "#007bff")
    if theme == "dark":
        bg = settings.get("dark_theme_bg", "#1e1e1e")
        text = settings.get("dark_theme_text", "#e6e6e6")
        list_text = settings.get("dark_theme_list_text", "#bbbbbb")
        is_dark = True
    else:
        bg = settings.get("light_theme_bg", "#ffffff")
        text = settings.get("light_theme_text", "#212529")
        list_text = settings.get("light_theme_list_text", "#212529")
        is_dark = False
    return is_dark, accent, bg, text, list_text

# --- НОВАЯ ФУНКЦИЯ ---
def get_scrollbar_style(settings: dict) -> str: # Убираем accent_color из аргументов
    """Генерирует CSS для стилизации полос прокрутки."""
    is_dark, _, bg, text_color, _ = theme_colors(settings)
    
    # --- НОВЫЕ ЦВЕТА ДЛЯ СКРОЛЛБАРА ---
    # Берем основной цвет текста и делаем его полупрозрачным
    handle_color = QColor(text_color)
    handle_color.setAlpha(80) # ~30% прозрачности
    
    # При наведении делаем его чуть более заметным
    handle_hover_color = QColor(text_color)
    handle_hover_color.setAlpha(120) # ~50% прозрачности
    
    handle_bg = handle_color.name(QColor.NameFormat.HexArgb)
    handle_hover_bg = handle_hover_color.name(QColor.NameFormat.HexArgb)

    pane_bg = "rgba(0,0,0,0.05)" if is_dark else "rgba(255,255,255,0.5)"

    return f"""
        QScrollBar:vertical {{
            border: none;
            background: {pane_bg}; /* Добавляем фон для области прокрутки */
            width: 10px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {handle_bg};
            min-height: 25px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {handle_hover_bg};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none; /* Убираем фон у пустой области */
        }}
        
        QScrollBar:horizontal {{
            border: none;
            background: {pane_bg};
            height: 10px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {handle_bg};
            min-width: 25px;
            border-radius: 5px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {handle_hover_bg};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}
    """

def get_global_dialog_stylesheet(settings):
    is_dark, accent, bg, text, _ = theme_colors(settings)
    comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
    border = "#555" if is_dark else "#ced4da"
    
    return f"""
        QMessageBox, QInputDialog {{
            background-color: {bg};
        }}
        QMessageBox QLabel, QInputDialog QLabel {{
            color: {text};
            background-color: transparent; /* <-- ВОТ КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ */
        }}
        /* Это стилизует виджет, который содержит иконку (например, 'X' или '!') */
        QMessageBox QLabel#qt_msgboxex_icon_label {{
            background-color: transparent;
        }}
        QMessageBox QPushButton, QInputDialog QPushButton {{
            background-color: {comp_bg}; color: {text}; border: 1px solid {border};
            padding: 6px 12px; border-radius: 4px; min-width: 80px;
        }}
        QMessageBox QPushButton:hover, QInputDialog QPushButton:hover {{
            border-color: {accent};
        }}
    """


# --- НОВЫЙ УНИВЕРСАЛЬНЫЙ СТИЛИСТ ДЛЯ MARKDOWN ---
def generate_markdown_css(settings: dict, for_pdf=False) -> str:
    """Генерирует CSS для предпросмотра Markdown и экспорта в PDF."""
    is_dark_theme, accent, bg, text, _ = theme_colors(settings)
    
    if for_pdf:
        bg_color = settings.get("pdf_bg_color", "#ffffff")
        text_color = settings.get("pdf_text_color", "#000000")
        font_family = settings.get("pdf_font_family", "Times New Roman")
        font_size = settings.get("pdf_font_size", 11)
        header_color = text_color
        component_bg = "#f0f0f0"
        border_color = "#cccccc"
    else:
        header_color = text 
        bg_color = QColor(bg).lighter(115).name() if is_dark_theme else QColor(bg).darker(105).name()
        text_color = text
        font_family = settings.get("zen_font_family", "sans-serif")
        font_size = settings.get("zen_font_size", 12)
        component_bg = QColor(bg_color).lighter(110).name() if is_dark_theme else QColor(bg_color).darker(102).name()
        border_color = QColor(text_color).lighter(150).name() if is_dark_theme else QColor(text_color).darker(150).name()

    alignment = "justify" if settings.get("zen_alignment") == "justify" else "left"
    body_style_css = f"""
            background-color: {bg_color};
            color: {text_color};
            font-family: "{font_family}";
            font-size: {font_size}pt;
            text-align: {alignment};
            /*line-height: 1.5; */
        """

    return f"""
    <style>
        h1, h2, h3, h4, h5, h6 {{
            color: {header_color};
            border-bottom: 1px solid {header_color};
            padding-bottom: 3px;
            margin-top: 1.2em;
            margin-bottom: 0.8em;
            font-weight: bold; /* Делаем их жирными, чтобы они выделялись */
        }}
        a {{ color: {accent}; text-decoration: none; }}
        code {{
            background-color: {component_bg};
            padding: 2px 5px;
            border-radius: 4px;
            font-family: "Courier New", monospace;
        }}
        pre {{
            background-color: {component_bg};
            padding: 10px;
            border: 1px solid {border_color};
            border-radius: 6px;
            white-space: pre-wrap;
        }}
        pre code {{ background-color: transparent; padding: 0; }}
        blockquote {{
            border-left: 3px solid {accent};
            padding-left: 12px;
            margin-left: 5px;
            color: #777777;
            font-style: italic;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 1em;
        }}
        th, td {{
            border: 1px solid {border_color};
            padding: 6px 10px;
        }}
        th {{
            background-color: {component_bg};
            font-weight: bold;
        }}
        ul, ol {{
            padding-left: 25px;
        }}
    </style>
    """

def update_style_for_dialogs(settings):
    """Применяет стили к глобальным диалогам."""
    dialog_style = get_global_dialog_stylesheet(settings)
    QApplication.instance().setStyleSheet(dialog_style)

def escape_markdown_tags(text: str) -> str:
    """
    Экранирует символы '#' в тегах, чтобы они не превращались в заголовки Markdown.
    Игнорирует настоящие заголовки (где есть пробел после #).
    """
    # Используем регулярное выражение для поиска всех слов, начинающихся с #
    # (?<!\S) - Negative lookbehind: убеждаемся, что перед # нет не-пробельного символа
    #           (т.е. # в начале строки или после пробела)
    # #(\w+)  - Находит сам # и захватывает слово после него (буквы, цифры, _)
    
    def replacer(match):
        # match.group(0) - это вся найденная строка, например, "#тег"
        # Просто добавляем обратный слэш в начало
        return f'\\{match.group(0)}'

    # Заменяем все вхождения вида "#слово" на "\#слово"
    # Это не затронет "# заголовок", так как там есть пробел, который не входит в \w+
    escaped_text = re.sub(r'(?<!\S)#(\w+)', replacer, text)
    return escaped_text

# --- Вспомогательные классы UI ---

class ThemedMenuMixin:
    """Миксин для создания стилизованного контекстного меню."""
    def _create_themed_menu(self):
        if not hasattr(self, 'data_manager'):
            print("Warning: ThemedMenuMixin requires a 'data_manager' attribute.")
            return QMenu(self)
            
        menu = QMenu(self)
        settings = self.data_manager.get_settings()
        is_dark, accent, bg, text, _ = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border_color = "#555" if is_dark else "#ced4da"
        
        stylesheet = f"""
            QMenu {{ background-color: {comp_bg}; color: {text}; border: 1px solid {border_color}; border-radius: 6px; padding: 5px; }}
            QMenu::item {{ padding: 6px 15px; border-radius: 4px; }}
            QMenu::item:selected {{ background-color: {accent}; color: white; }}
            QMenu::separator {{ height: 1px; background-color: {border_color}; margin: 5px 10px; }}
        """
        menu.setStyleSheet(stylesheet)
        return menu

class ThemedLineEdit(QLineEdit):
    """Поле ввода, которое создает стилизованное контекстное меню."""
    def __init__(self, main_parent=None, parent=None):
        super().__init__(parent)
        self.main_parent = main_parent

    def contextMenuEvent(self, event):
        standard_menu = self.createStandardContextMenu()
        
        if self.main_parent and hasattr(self.main_parent, '_create_themed_menu'):
            themed_menu = self.main_parent._create_themed_menu()
            themed_menu.addActions(standard_menu.actions())
            themed_menu.exec(event.globalPos())
        else:
            standard_menu.exec(event.globalPos())
            
class ThemedInputDialog(QDialog):
    """Диалоговое окно для ввода текста, стилизованное под тему приложения."""
    def __init__(self, parent, title, label, text="", settings=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(350)
        
        self.layout = QVBoxLayout(self)
        self.info_label = QLabel(label)
        self.input_field = QLineEdit(text)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        
        self.layout.addWidget(self.info_label)
        self.layout.addWidget(self.input_field)
        self.layout.addWidget(self.buttons)
        
        if settings:
            self.apply_theme(settings)

    def apply_theme(self, settings):
        is_dark, accent, bg, text, _ = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border = "#555" if is_dark else "#ced4da"
        
        stylesheet = f"""
            QDialog {{ background-color: {bg}; }}
            QLabel {{ color: {text}; background-color: transparent; padding-bottom: 5px; }}
            QLineEdit {{
                background-color: {comp_bg}; border: 1px solid {border};
                border-radius: 4px; color: {text}; padding: 5px;
            }}
            QPushButton {{
                background-color: {comp_bg}; color: {text}; border: 1px solid {border};
                padding: 6px 12px; border-radius: 4px; min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {QColor(comp_bg).lighter(110).name()};
                border: 1px solid {accent};
            }}
        """
        self.setStyleSheet(stylesheet)

    def get_text(self):
        return self.input_field.text()

# --- НОВЫЙ ВСПОМОГАТЕЛЬНЫЙ КЛАСС ---
class HeightAnimator(QObject):
    """Управляет анимацией высоты виджета."""
    def __init__(self, widget, parent=None):
        super().__init__(parent)
        self.widget = widget
        self.animation = QPropertyAnimation(self.widget, b"maximumHeight")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def expand(self, max_height=1000000):
        start_height = self.widget.height()
        self.animation.setStartValue(start_height)
        self.animation.setEndValue(max_height)
        self.widget.show()
        self.animation.start()

    def collapse(self):
        start_height = self.widget.height()
        self.animation.setStartValue(start_height)
        self.animation.setEndValue(0)
        self.animation.finished.connect(self.widget.hide)
        self.animation.start()

# --- Локализация ---
class LocalizationManager(QObject):
    language_changed = pyqtSignal()

    def __init__(self, default_lang='ru_RU'):
        super().__init__()
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        self.locales_dir = os.path.join(base_path, "locales")
        self.translations = {}
        self._ensure_locales_exist()
        self.available_languages = self._scan_languages()
        self.current_lang = default_lang
        self.set_language(self.current_lang)

    def _ensure_locales_exist(self):
        if not os.path.isdir(self.locales_dir):
            os.makedirs(self.locales_dir)
        
        ru_path = os.path.join(self.locales_dir, 'ru_RU.json')
        if not os.path.exists(ru_path):
            ru_data = {
                "app_title": "Ассистент 3.0",
                "lang_name": "Русский", "add_task_button": "Добавить",
                "new_task_placeholder": "Новая задача...", "hide_completed_checkbox": "Скрыть выполненные",
                "delete_note_tooltip": "Удалить заметку", "delete_task_tooltip": "Удалить задачу",
                "notes_editor_label": "Редактор заметок:", "save_button": "Сохранить", "new_note_button": "Новая", "zen_button": "Zen",
                "search_placeholder": "Поиск по тексту...", "all_tags_combo": "Все теги",
                "new_note_placeholder": "Начните писать...", "unsaved_changes_status": "Несохраненные изменения...",
                "data_saved_status": "Данные сохранены", "word_count_label": "Слов", "pomodoro_label": "Pomodoro:",
                "pomodoro_start_btn": "Старт", "pomodoro_pause_btn": "Пауза", "pomodoro_reset_btn": "Сброс",
                "about_menu": "О программе...", "export_menu": "Экспорт заметок...",
                "restore_menu": "Восстановить из резервной копии...", "exit_menu": "Выход",
                "add_list_menu": "Добавить список...", "rename_list_menu": "Переименовать список...",
                "delete_list_menu": "Удалить список...", "new_list_prompt": "Введите имя нового списка:",
                "rename_list_prompt": "Введите новое имя для списка:",
                "delete_list_confirm": "Вы уверены, что хотите удалить список '{list_name}'со всеми задачами?",
                "settings_title": "Настройки", "settings_tab_general": "Общие", "settings_tab_appearance": "Оформление",
                "settings_tab_zen": "Редактор Zen", "settings_lang_label": "Язык:", "settings_theme_label": "Основная тема:",
                "settings_light_theme": "Светлая", "settings_dark_theme": "Тёмная",
                "settings_trigger_pos_label": "Позиция кнопки:", "settings_trigger_left": "Слева",
                "settings_trigger_right": "Справа", "settings_accent_color_label": "Акцентный цвет:",
                "settings_choose_color_btn": "Выбрать цвет...", "settings_light_theme_bg_label": "Фон светлой темы:",
                "settings_light_theme_text_label": "Текст светлой темы:", "settings_dark_theme_bg_label": "Фон тёмной темы:",
                "settings_dark_theme_text_label": "Текст тёмной темы:", "settings_light_theme_list_text_label": "Текст списков (светлая):",
                "settings_dark_theme_list_text_label": "Текст списков (тёмная):", "settings_zen_bg_label": "Фон Zen (картинка):",
                "settings_browse_btn": "Обзор...", "settings_clear_btn": "Очистить",
                "settings_font_label": "Шрифт", "settings_size_label": "Размер:", "settings_font_color_label": "Цвет шрифта:",
                "settings_alignment_label": "Выравнивание:", "settings_align_left": "По левому краю",
                "settings_align_justify": "По ширине", "settings_padding_horiz": "Гор. отступ (%):",
                "settings_padding_vert": "Верт. отступ (%):",
                "task_menu_edit": "Редактировать...", "task_menu_toggle_completed": "Отметить/Снять отметку",
                "note_pin_menu": "Закрепить", "note_unpin_menu": "Открепить",
                "list_management_tooltip": "Клик правой кнопкой для управления списками",
                "open_window_menu": "Открыть оконный режим…", "open_window_tooltip": "Открыть в оконном режиме",
                "to_panel_button": "Панель", "to_panel_tooltip": "Открыть боковую панель", "tags_label": "Теги:",
                "to_task_btn": "➕ в задачи", "to_task_tooltip": "Добавить выделенный текст в задачи",
                "import_settings": "Импорт настроек…", "export_settings": "Экспорт настроек…",
                "task_templates_title": "Шаблоны задач", "task_templates_hint": "Один шаблон — одна строка:",
                "tree_new_folder": "Новая папка...", "tree_rename_folder": "Переименовать папку...",
                "tree_delete_folder": "Удалить папку", "tree_delete_note": "Удалить заметку", "tree_new_note_here": "Новая заметка здесь",
                "tree_confirm_delete_folder": "Удалить папку '{name}' со всем содержимым?",
                "audio_toggle_tooltip": "Музыка", "audio_prev": "Предыдущий",
                "audio_next": "Следующий", "audio_play": "Воспроизвести", "audio_pause": "Пауза", "audio_stop": "Стоп",
                "audio_volume": "Громкость",
                "new_note_title": "Новая заметка", "folder_description": "Описание папки", "note_editing": "Редактирование заметки",
                "settings_zen_light_theme_bg_label": "Фон Zen (светлая тема):", "settings_zen_dark_theme_bg_label": "Фон Zen (тёмная тема):",
                "settings_min_width_left": "Мин. ширина левой колонки:", "settings_min_width_right": "Мин. ширина правой колонки:",
                "task_filter_all": "Все", "task_filter_active": "Активные", "task_filter_completed": "Выполненные",
                "settings_padding_top": "Отступ сверху (px):", "settings_padding_bottom": "Отступ снизу (px):",
                "settings_padding_left": "Отступ слева (px):", "settings_padding_right": "Отступ справа (px):",
                "backup_manager_title": "Менеджер резервных копий", "backup_available_copies": "Доступные копии:",
                "backup_restore_btn": "Восстановить", "backup_delete_btn": "Удалить", "backup_no_copies": "Резервные копии не найдены.",
                "backup_confirm_restore": "Вы уверены, что хотите восстановить данные из копии от {date}?",
                "backup_confirm_delete": "Вы уверены, что хотите удалить эту резервную копию?",
                "settings_create_backup_now": "Создать бэкап сейчас", "zen_button_tooltip": "Перейти в режим Zen (полноэкранный редактор)",
                "window_button_tooltip": "Перейти в оконный режим", "font_search_placeholder": "Поиск шрифта...",
                "settings_backup_interval": "Интервал автосохранения (мин):", "settings_backup_max_count": "Макс. кол-во копий:",
                "backup_creation_silent_success": "Резервная копия создана (автоматически)",
                "day_1": "понедельник", "day_2": "вторник", "day_3": "среда", "day_4": "четверг",
                "day_5": "пятница", "day_6": "суббота", "day_7": "воскресенье",
                "settings_tab_security": "Безопасность", "login_title": "Вход в Ассистент",
                "login_password_label": "Введите пароль:", "login_button": "Войти", "login_forgot_password": "Забыли пароль?",
                "setup_password_title": "Установка пароля", "setup_password_intro": "Это первый запуск с функцией безопасности. Установите пароль для защиты ваших данных.",
                "setup_password_new": "Новый пароль:", "setup_password_confirm": "Подтвердите пароль:",
                "setup_question1": "Контрольный вопрос 1:", "setup_answer1": "Ответ 1:",
                "setup_question2": "Контрольный вопрос 2:", "setup_answer2": "Ответ 2:",
                "setup_save_button": "Сохранить и войти", "setup_no_password_button": "Использовать без пароля",
                "password_recovery_title": "Восстановление доступа", "password_recovery_intro": "Ответьте на контрольные вопросы, чтобы сбросить пароль.",
                "password_recovery_button": "Сбросить пароль", "password_reset_title": "Новый пароль",
                "password_reset_success": "Пароль успешно сброшен! Теперь вы можете установить новый.",
                "reset_all_data_button": "Сбросить все данные...", "reset_data_warning_title": "ВНИМАНИЕ!",
                "reset_data_warning_text": "Вы уверены, что хотите ПОЛНОСТЬЮ удалить все заметки, задачи и настройки?\n\nЭто действие НЕОБРАТИМО!",
                "error_passwords_mismatch": "Пароли не совпадают.", "error_password_incorrect": "Неверный пароль.",
                "error_answers_incorrect": "Ответы неверны.", "error_fields_empty": "Все поля (кроме вопросов 2/ответов 2) должны быть заполнены.",
                "change_password_button": "Изменить пароль и вопросы...",
                "settings_min_width_center": "Мин. ширина центра:", "preview_tooltip": "Режим предпросмотра",
                "main_popup_tab_work": "Работа", "main_popup_tab_player": "Плеер", "pdf_choose_button": "Выбрать...",
                "zen_bg_type_box_title": "Тип фона:", "zen_bg_type_color": "Цвет", "zen_bg_type_procedural": "Горы",
                "zen_bg_type_image": "Изображение", "settings_pdf_tab": "Экспорт PDF", "pdf_font_label": "Шрифт:",
                "pdf_size_label": "Размер:", "pdf_text_color_label": "Цвет текста:", "pdf_margin_top_label": "Верх. отступ (мм):",
                "pdf_margin_bottom_label": "Нижн. отступ (мм):", "pdf_margin_left_label": "Лев. отступ (мм):",
                "pdf_margin_right_label": "Прав. отступ (мм):", "startup_box_title": "Запускать при старте:",
                "startup_panel_radio": "Боковую панель", "startup_window_radio": "Оконный режим",
                "import_folder_title": "Импортировать из папки...", "import_files_title": "Импортировать файлы сюда...",
                "export_folder_title": "Экспортировать папку...", "export_note_title": "Экспортировать заметку...",
                "move_item_up_title": "Поднять на уровень выше", "move_item_to_root_title": "В корень",
                "remove_password_button": "Удалить пароль", "error_change_q1": "Если вы меняете вопрос 1, нужно ввести новый ответ 1.",
                "password_remove_confirm_title": "Удаление пароля", "password_remove_confirm_text": "Вы уверены, что хотите удалить пароль? Доступ к приложению больше не будет защищен.",
                "password_removed_success": "Пароль удален.", "export_notes_dialog_title": "Экспорт заметок",
                "export_all_notes_default_filename": "Все_заметки", "export_note_default_filename": "Заметка",
                "export_folder_default_filename": "Папка", "import_target_dialog_title": "Выберите место для импорта",
                "import_target_label": "Куда импортировать заметки?", "import_target_root": "В корень (верхний уровень)",
                "import_new_folder_button": "Новая папка", "import_new_folder_prompt_title": "Новая папка",
                "import_new_folder_prompt_label": "Введите имя новой папки:", "import_files_dialog_title": "Выберите файлы для импорта",
                "import_success_message": "Импорт завершен.\nДобавлено новых заметок: {count}",
                "import_error_message": "Произошла ошибка при импорте:\n{error}", "import_files_error_message": "Произошла ошибка при импорте файлов:\n{error}",
                "export_no_notes": "Нет заметок для экспорта.", "export_success_message": "Все заметки успешно экспортированы в папку:\n{dir}",
                "export_error_message": "Произошла ошибка при экспорте:\n{error}",
                "unnamed_note_title": "Без названия", "unnamed_folder_title": "Новая папка",
                "unnamed_note_updated_title": "Обновленная заметка", "unnamed_note_renamed_title": "Переименованная заметка",
                "delete_item_confirm_title": "Подтверждение", "delete_item_confirm_text": "Удалить '{name}'?",
                "delete_folder_confirm_extra": "\nВЕСЬ контент внутри папки будет удален!",
                "rename_item_dialog_title": "Переименовать", "rename_item_dialog_label": "Новое имя:",
                "backup_created_success_popup": "Резервная копия успешно создана!", "backup_title": "Бэкап",
                "success_title": "Успех", "error_title": "Ошибка",
                "backup_restore_error": "Не удалось восстановить: {error}", "backup_restored_success": "Данные восстановлены. Приложение будет перезапущено.",
                "export_file_success": "Заметки экспортированы в {path}", "export_file_error": "Не удалось экспортировать: {error}",
                "settings_export_success": "Настройки экспортированы в {path}", "settings_export_error": "Не удалось экспортировать: {error}",
                "settings_import_success": "Настройки импортированы", "settings_import_error": "Не удалось импортировать: {error}",
                "critical_error_title": "Критическая ошибка", "critical_error_text": "Произошла непредвиденная ошибка:\n\n{msg}\n\nПриложение может работать нестабильно.",
                "leave_password_blank":"Оставьте поля пароля пустыми, чтобы изменить только вопросы.",
                "new_password":"Новый пароль (необязательно)",
                "new_answer":"Новый ответ (если меняете вопрос 1)",
                "new_answer2":"Новый ответ (необязательно)",
                "confirm_new_password":"Пожалуйста, подтвердите новый пароль.",
                "delete_faied":"Не удалось удалить файл",
                "export":"Экспорт",
                "delete_data_success":"Все данные были удалены. Приложение перезапустится.",
                "select_export_format":"Выберите формат для экспорта:",
                "edit_task":"Редактировать задачу", "new_text":"Новый текст:",
                "select_folder_to_export":"Выберите папку для экспорта",
                "select_folder_to_import":"Выберите папку для импорта",
                "no_lists":"Нет списков",
                "folder_name":"Имя папки:",
                "lock_app":"Заблокировать",
                "in_one_file":"В один файл...",
                "as_a_folder":"В виде папки...",
                "export_menu_title": "Экспорт...",
                "export_all_to_file": "Экспортировать всё в один файл...",
                "export_all_to_folders": "Экспортировать всё в папки...",
                "app_title_v3": "Ассистент 3.0",
                "zen_opacity_label": "Прозрачность редактора (%):",
                "popup_font_size_label": "Размер (панель):",
                "pdf_font_search_placeholder": "Поиск шрифта...",

            }
            with open(ru_path, 'w', encoding='utf-8') as f:
                json.dump(ru_data, f, ensure_ascii=False, indent=2)

        en_path = os.path.join(self.locales_dir, 'en_US.json')
        if not os.path.exists(en_path):
            en_data = {
                "app_title": "Assistant 3.0",
                "lang_name": "English", "add_task_button": "Add",
                "new_task_placeholder": "New task...", "hide_completed_checkbox": "Hide completed",
                "delete_note_tooltip": "Delete note", "delete_task_tooltip": "Delete task",
                "notes_editor_label": "Notes Editor:", "save_button": "Save", "new_note_button": "New", "zen_button": "Zen",
                "search_placeholder": "Search...", "all_tags_combo": "All tags", "new_note_placeholder": "Start writing...",
                "unsaved_changes_status": "Unsaved changes...", "data_saved_status": "Data saved",
                "word_count_label": "Words", "pomodoro_label": "Pomodoro:", "pomodoro_start_btn": "Start",
                "pomodoro_pause_btn": "Pause", "pomodoro_reset_btn": "Reset", "about_menu": "About...",
                "export_menu": "Export Notes...", "restore_menu": "Restore from Backup...", "exit_menu": "Exit",
                "add_list_menu": "Add List...", "rename_list_menu": "Rename List...", "delete_list_menu": "Delete List...",
                "new_list_prompt": "Enter new list name:", "rename_list_prompt": "Enter new list name:",
                "delete_list_confirm": "Are you sure you want to delete list '{list_name}'?", "settings_title": "Settings",
                "settings_tab_general": "General", "settings_tab_appearance": "Appearance", "settings_tab_zen": "Zen Editor",
                "settings_lang_label": "Language:", "settings_theme_label": "Main theme:", "settings_light_theme": "Light",
                "settings_dark_theme": "Dark", "settings_trigger_pos_label": "Button position:", "settings_trigger_left": "Left",
                "settings_trigger_right": "Right", "settings_accent_color_label": "Accent color:",
                "settings_choose_color_btn": "Choose color...", "settings_light_theme_bg_label": "Light theme BG:",
                "settings_light_theme_text_label": "Light theme Text:", "settings_dark_theme_bg_label": "Dark theme BG:",
                "settings_dark_theme_text_label": "Dark theme Text:", "settings_light_theme_list_text_label": "List text (light):",
                "settings_dark_theme_list_text_label": "List text (dark):", "settings_zen_bg_label": "Zen Background (image):",
                "settings_browse_btn": "Browse...", "settings_clear_btn": "Clear",
                "settings_font_label": "Font", "settings_size_label": "Size:", "settings_font_color_label": "Font Color:",
                "settings_alignment_label": "Alignment:", "settings_align_left": "Left", "settings_align_justify": "Justify",
                "settings_padding_horiz": "Horiz. Padding (%):", "settings_padding_vert": "Vert. Padding (%):",
                "task_menu_edit": "Edit...", "task_menu_toggle_completed": "Toggle completed", "note_pin_menu": "Pin", "note_unpin_menu": "Unpin",
                "list_management_tooltip": "Right-click to manage lists", "open_window_menu": "Open window mode…",
                "open_window_tooltip": "Open in window mode", "to_panel_button": "Panel",
                "to_panel_tooltip": "Open side panel", "tags_label": "Tags:", "to_task_btn": "➕ to tasks",
                "to_task_tooltip": "Add selected text to tasks", "import_settings": "Import settings…",
                "export_settings": "Export settings…", "task_templates_title": "Task templates",
                "task_templates_hint": "One template per line:",
                "tree_new_folder": "New folder...", "tree_rename_folder": "Rename folder...", "tree_delete_folder": "Delete folder",
                "tree_delete_note": "Delete note", "tree_new_note_here": "New note here",
                "tree_confirm_delete_folder": "Delete folder '{name}' with all contents?",
                "audio_toggle_tooltip": "Music", "audio_prev": "Previous",
                "audio_next": "Next", "audio_play": "Play", "audio_pause": "Pause", "audio_stop": "Stop",
                "audio_volume": "Volume", "new_note_title": "New Note",
                "folder_description": "Folder description", "note_editing": "Editing note",
                "settings_zen_light_theme_bg_label": "Zen BG (light theme):", "settings_zen_dark_theme_bg_label": "Zen BG (dark theme):",
                "settings_min_width_left": "Min. left column width:", "settings_min_width_right": "Min. right column width:",
                "task_filter_all": "All", "task_filter_active": "Active", "task_filter_completed": "Completed",
                "settings_padding_top": "Padding Top (px):", "settings_padding_bottom": "Padding Bottom (px):",
                "settings_padding_left": "Padding Left (px):", "settings_padding_right": "Padding Right (px):",
                "backup_manager_title": "Backup Manager", "backup_available_copies": "Available copies:",
                "backup_restore_btn": "Restore", "backup_delete_btn": "Delete", "backup_no_copies": "No backups found.",
                "backup_confirm_restore": "Are you sure you want to restore data from the copy dated {date}?",
                "backup_confirm_delete": "Are you sure you want to delete this backup?", "settings_create_backup_now": "Create backup now",
                "zen_button_tooltip": "Enter Zen Mode (fullscreen editor)", "window_button_tooltip": "Switch to Window Mode",
                "font_search_placeholder": "Search font...", "settings_backup_interval": "Backup interval (min):",
                "settings_backup_max_count": "Max backups to keep:", "backup_creation_silent_success": "Backup created (automatic)",
                "day_1": "monday", "day_2": "tuesday", "day_3": "wednesday", "day_4": "thursday",
                "day_5": "friday", "day_6": "saturday", "day_7": "sunday",
                "settings_tab_security": "Security", "login_title": "Assistant Login",
                "login_password_label": "Enter password:", "login_button": "Login", "login_forgot_password": "Forgot password?",
                "setup_password_title": "Password Setup", "setup_password_intro": "This is the first run with the security feature. Set a password to protect your data.",
                "setup_password_new": "New password:", "setup_password_confirm": "Confirm password:",
                "setup_question1": "Security Question 1:", "setup_answer1": "Answer 1:",
                "setup_question2": "Security Question 2:", "setup_answer2": "Answer 2:",
                "setup_save_button": "Save and Login", "setup_no_password_button": "Use without a password",
                "password_recovery_title": "Access Recovery", "password_recovery_intro": "Answer your security questions to reset your password.",
                "password_recovery_button": "Reset Password", "password_reset_title": "New Password",
                "password_reset_success": "Password has been reset! You can now set a new one.",
                "reset_all_data_button": "Reset All Data...", "reset_data_warning_title": "WARNING!",
                "reset_data_warning_text": "Are you sure you want to PERMANENTLY delete all notes, tasks, and settings?\n\nThis action CANNOT be undone!",
                "error_passwords_mismatch": "Passwords do not match.", "error_password_incorrect": "Incorrect password.",
                "error_answers_incorrect": "Answers are incorrect.", "error_fields_empty": "All fields (except Question 2/Answer 2) must be filled.",
                "change_password_button": "Change Password & Questions...",
                "settings_min_width_center": "Min. center width:", "preview_tooltip": "Preview Mode",
                "main_popup_tab_work": "Work", "main_popup_tab_player": "Player", "pdf_choose_button": "Choose...",
                "zen_bg_type_box_title": "Background Type:", "zen_bg_type_color": "Color",
                "zen_bg_type_procedural": "Mountains", "zen_bg_type_image": "Image",
                "settings_pdf_tab": "PDF Export", "pdf_font_label": "Font:", "pdf_size_label": "Size:",
                "pdf_text_color_label": "Text Color:", "pdf_margin_top_label": "Top margin (mm):",
                "pdf_margin_bottom_label": "Bottom margin (mm):", "pdf_margin_left_label": "Left margin (mm):",
                "pdf_margin_right_label": "Right margin (mm):", "startup_box_title": "On startup open:",
                "startup_panel_radio": "Side Panel", "startup_window_radio": "Window Mode",
                "import_folder_title": "Import from folder...", "import_files_title": "Import files here...",
                "export_folder_title": "Export folder...", "export_note_title": "Export note...",
                "move_item_up_title": "Move one level up", "move_item_to_root_title": "Move to root",
                "remove_password_button": "Remove Password", "error_change_q1": "If you change Question 1, a new Answer 1 is required.",
                "password_remove_confirm_title": "Remove Password", "password_remove_confirm_text": "Are you sure you want to remove the password? Application access will no longer be protected.",
                "password_removed_success": "Password removed.", "export_notes_dialog_title": "Export Notes",
                "export_all_notes_default_filename": "All_Notes", "export_note_default_filename": "Note",
                "export_folder_default_filename": "Folder", "import_target_dialog_title": "Select Import Destination",
                "import_target_label": "Where to import the notes?", "import_target_root": "To Root (Top Level)",
                "import_new_folder_button": "New Folder", "import_new_folder_prompt_title": "New Folder",
                "import_new_folder_prompt_label": "Enter new folder name:", "import_files_dialog_title": "Select Files to Import",
                "import_success_message": "Import complete.\nNew notes added: {count}",
                "import_error_message": "An error occurred during import:\n{error}", "import_files_error_message": "An error occurred during file import:\n{error}",
                "export_no_notes": "No notes to export.", "export_success_message": "All notes successfully exported to:\n{dir}",
                "export_error_message": "An error occurred during export:\n{error}",
                "unnamed_note_title": "Untitled", "unnamed_folder_title": "New Folder",
                "unnamed_note_updated_title": "Updated Note", "unnamed_note_renamed_title": "Renamed Note",
                "delete_item_confirm_title": "Confirm", "delete_item_confirm_text": "Delete '{name}'?",
                "delete_folder_confirm_extra": "\nALL content inside the folder will be deleted!",
                "rename_item_dialog_title": "Rename", "rename_item_dialog_label": "New name:",
                "backup_created_success_popup": "Backup created successfully!", "backup_title": "Backup",
                "success_title": "Success", "error_title": "Error",
                "backup_restore_error": "Failed to restore: {error}", "backup_restored_success": "Data restored. The application will now restart.",
                "export_file_success": "Notes exported to {path}", "export_file_error": "Failed to export: {error}",
                "settings_export_success": "Settings exported to {path}", "settings_export_error": "Failed to export: {error}",
                "settings_import_success": "Settings imported", "settings_import_error": "Failed to import: {error}",
                "critical_error_title": "Critical Error", "critical_error_text": "An unexpected error occurred:\n\n{msg}\n\nThe application may be unstable.",
                "leave_password_blank":"Leave password empty to change only questions.",
                "new_password":"New password (optional)",
                "new_answer":"New answer(if change Question 1)",
                "new_answer2":"New answer (optional)",
                "confirm_new_password":"Please confirm new password.",
                "delete_faied":"Could not delete file",
                "export":"Export",
                "delete_data_success":"All data has been deleted. The application will restart",
                "select_export_format":"Select the format to export:",
                "edit_task":"Edit task", "new_text":"New Text:",
                "select_folder_to_export":"Select folder to export",
                "select_folder_to_import":"Select folder to import",
                "no_lists":"No lists",
                "folder_name":"Folder name:",
                "lock_app":"Lock the app",
                "in_one_file":"In one file...",
                "as_a_folder":"As a folder...",
                "export_menu_title": "Export...",
                "export_all_to_file": "Export all to a single file...",
                "export_all_to_folders": "Export all to folders...",
                "app_title_v3": "Assistant 3.0",
                "zen_opacity_label": "Editor Opacity (%):",
                "popup_font_size_label": "Size (panel):",
                "pdf_font_search_placeholder": "Search font...",
                
            }
            with open(en_path, 'w', encoding='utf-8') as f:
                json.dump(en_data, f, ensure_ascii=False, indent=2)

    def _scan_languages(self):
        langs = {}
        if not os.path.isdir(self.locales_dir): return {}
        for filename in os.listdir(self.locales_dir):
            if filename.endswith(".json"):
                lang_code = os.path.splitext(filename)[0]
                try:
                    with open(os.path.join(self.locales_dir, filename), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        langs[lang_code] = data.get("lang_name", lang_code)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Could not load language file {filename}: {e}")
        return langs

    def set_language(self, lang_code):
        path = os.path.join(self.locales_dir, f"{lang_code}.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
                if self.current_lang != lang_code:
                    self.current_lang = lang_code
                    self.language_changed.emit()
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading language {lang_code}: {e}")
                if lang_code != 'en_US': self.set_language('en_US')
        else:
            print(f"Language file for {lang_code} not found.")

    def get(self, key, default_text=""):
        return self.translations.get(key, default_text or key)

# --- Редактор с хоткеем Shift+Enter ---
class NoteEditor(QTextEdit):
    save_and_new_requested = pyqtSignal()
    
    def __init__(self, parent_panel=None, parent=None):
        super().__init__(parent)
        self.parent_panel = parent_panel

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.save_and_new_requested.emit()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        standard_menu = self.createStandardContextMenu()
        
        if self.parent_panel and hasattr(self.parent_panel.main_parent, '_create_themed_menu'):
            themed_menu = self.parent_panel.main_parent._create_themed_menu()
            themed_menu.addActions(standard_menu.actions())
            themed_menu.exec(event.globalPos())
        else:
            standard_menu.exec(event.globalPos())

# --- О программе ---
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.loc = parent.loc if hasattr(parent, 'loc') else LocalizationManager()
        self.setFixedSize(480, 550)
        
        self.main_layout = QVBoxLayout(self)
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.info_label.setOpenExternalLinks(True)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.info_label)
        self.main_layout.addWidget(scroll_area)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.buttons.accepted.connect(self.accept)
        self.main_layout.addWidget(self.buttons)

        settings = parent.get_settings() if hasattr(parent, 'get_settings') else {}
        is_dark, accent, bg, text, _ = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border = "#555" if is_dark else "#ced4da"
        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; }}
            QLabel, QScrollArea {{ 
                color: {text}; 
                background-color: transparent; 
            }}
            QPushButton {{
                background-color: {comp_bg}; color: {text}; border: 1px solid {border};
                padding: 6px 12px; border-radius: 4px; min-width: 80px;
            }}
            QPushButton:hover {{ border-color: {accent}; }}
        """)
        
        self.retranslate_ui()

    def retranslate_ui(self):
        self.setWindowTitle(self.loc.get("about_menu", "About..."))
        self.info_label.setText(
            f"<h3>{self.loc.get('app_title_v3')}</h3>"
            "<p>Эта программа была создана в рамках совместной работы пользователя и AI-ассистентов.</p>"
            "<p><b>Разработчик:</b> Rintaru123</p>"
            "<p><b>AI-ассистенты:</b> Claude 3, ChatGPT, Google AI</p>"
            "<hr>"
            "<h4>Лицензии используемых компонентов:</h4>"
            "<p>Программа написана с использованием фреймворка <b>PyQt6</b> (<b>GPL v3</b>)</p>"
            "<p>Лицензия кода <b>MIT</b>.</p>"
            "<p>Иконки предоставлены Qt Framework и <a target='_blank' href='https://icons8.com'>Icons8</a>.</p>"
            "<hr>"
            "<h4>Лицензии на аудиоматериалы:</h4>"
            
            "<p>Purple Dream by Ghostrifter <a target='_blank' href='https://bit.ly/ghostrifter-yt'>bit.ly/ghostrifter-yt</a><br>"
            "Creative Commons — Attribution-NoDerivs 3.0 Unported — CC BY-ND 3.0<br>"
            "Music promoted by <a target='_blank' href='https://www.chosic.com/free-music/all/'>https://www.chosic.com/free-music/all/ </a></p>"
            
            "<p>Transcendence by Alexander Nakarada | <a target='_blank' href='https://creatorchords.com'>https://creatorchords.com</a><br>"
            "Music promoted by <a target='_blank' href='https://www.chosic.com/free-music/all/'>https://www.chosic.com/free-music/all/</a><br>"
            "Creative Commons CC BY 4.0</p>"

            "<p>Meanwhile by Scott Buckley | <a target='_blank' href='http://www.scottbuckley.com.au'>www.scottbuckley.com.au</a><br>"
            "Music promoted by <a target='_blank' href='https://www.chosic.com/free-music/all/'>https://www.chosic.com/free-music/all/</a><br>"
            "Creative Commons CC BY 4.0</p>"
            
            "<p>Shadows And Dust by Scott Buckley | <a target='_blank' href='http://www.scottbuckley.com.au'>www.scottbuckley.com.au</a><br>"
            "Music promoted by <a target='_blank' href='https://www.chosic.com/free-music/all/'>https://www.chosic.com/free-music/all/</a><br>"
            "Creative Commons CC BY 4.0</p>"
            
            "<p>Silent Wood by Purrple Cat | <a target='_blank' href='https://purrplecat.com/'>https://purrplecat.com/</a><br>"
            "Music promoted by <a target='_blank' href='https://www.chosic.com/free-music/all/'>https://www.chosic.com/free-music/all/</a><br>"
            "Creative Commons CC BY-SA 3.0</p>"
            "<p><a target='_blank' href='https://icons8.com/icon/gkW5yexEuzan/left-handed'>Левша</a> иконка от <a target='_blank' href='https://icons8.com'>Icons8</a></p>"
        )

class LoginWindow(QDialog):
    login_successful = pyqtSignal()

    def __init__(self, data_manager, loc_manager):
        super().__init__()
        self.data_manager = data_manager
        self.db = data_manager.db
        self.loc = loc_manager
        self.setWindowTitle(self.loc.get("login_title"))
        self.setModal(True)
        
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.setFixedSize(380, 100)
        
        layout = QVBoxLayout(self)
        
        self.info_label = QLabel(self.loc.get("login_password_label"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self._check_password)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #dc3545;")
        self.error_label.hide()

        button_layout = QHBoxLayout()
        self.login_button = QPushButton(self.loc.get("login_button"))
        self.login_button.clicked.connect(self._check_password)
        
        self.forgot_button = QPushButton(self.loc.get("login_forgot_password"))
        self.forgot_button.setFlat(True)
        self.forgot_button.setCursor(Qt.CursorShape.PointingHandCursor) # <-- Добавляем курсор
        self.forgot_button.clicked.connect(self._show_recovery_dialog)
        
        button_layout.addWidget(self.forgot_button)
        button_layout.addStretch()
        button_layout.addWidget(self.login_button)

        layout.addWidget(self.info_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.error_label)
        layout.addLayout(button_layout)

        self.apply_theme()

    def apply_theme(self):
        settings = self.data_manager.get_settings()
        is_dark, accent, bg, text, _ = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border = "#555" if is_dark else "#ced4da"
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; }}
            QLabel {{ color: {text}; }}
            QLineEdit {{
                background-color: {comp_bg}; border: 1px solid {border};
                border-radius: 4px; color: {text}; padding: 6px;
            }}
            QPushButton {{
                background-color: {accent}; color: white; border: none;
                padding: 6px 12px; border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {QColor(accent).lighter(110).name()}; }}
            QPushButton[flat="true"] {{
                background-color: transparent; color: {accent}; text-decoration: underline;
            }}
        """)

    def _check_password(self):
        password = self.password_input.text()
        if self.db.check_password(password):
            self.login_successful.emit()
            self.accept()
        else:
            self.error_label.setText(self.loc.get("error_password_incorrect"))
            self.error_label.show()
            self.password_input.selectAll()

    def _show_recovery_dialog(self):
        """Открывает окно восстановления пароля."""
        self.hide() # Прячем окно входа
        
        recovery_dialog = PasswordSetupDialog(self.data_manager, self.loc, mode='recover')
        recovery_dialog.setup_successful.connect(self.login_successful)
        recovery_dialog.setup_successful.connect(self.accept)
        
        if not recovery_dialog.exec():
            self.show() 

class PasswordSetupDialog(QDialog):
    setup_successful = pyqtSignal()
    use_without_password = pyqtSignal()

    def __init__(self, data_manager, loc_manager, mode='setup'):
        super().__init__()
        self.data_manager = data_manager
        self.db = data_manager.db
        self.loc = loc_manager
        self.mode = mode # 'setup', 'recover', 'change'

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setMinimumWidth(450)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        self.intro_label = QLabel()
        self.intro_label.setWordWrap(True)
        main_layout.addWidget(self.intro_label)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #dc3545;")
        self.error_label.hide()
        main_layout.addWidget(self.error_label)
        
        grid = QGridLayout()
        grid.setSpacing(8)

        # Поля для пароля
        self.new_pass_label = QLabel(self.loc.get("setup_password_new"))
        self.new_pass_input = QLineEdit()
        self.new_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pass_label = QLabel(self.loc.get("setup_password_confirm"))
        self.confirm_pass_input = QLineEdit()
        self.confirm_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        # Поля для контрольных вопросов
        self.q1_label = QLabel(self.loc.get("setup_question1"))
        self.q1_input = QLineEdit()
        self.a1_label = QLabel(self.loc.get("setup_answer1"))
        self.a1_input = QLineEdit()
        self.q2_label = QLabel(self.loc.get("setup_question2"))
        self.q2_input = QLineEdit()
        self.a2_label = QLabel(self.loc.get("setup_answer2"))
        self.a2_input = QLineEdit()

        grid.addWidget(self.new_pass_label, 0, 0); grid.addWidget(self.new_pass_input, 0, 1)
        grid.addWidget(self.confirm_pass_label, 1, 0); grid.addWidget(self.confirm_pass_input, 1, 1)
        grid.addWidget(self.q1_label, 2, 0); grid.addWidget(self.q1_input, 2, 1)
        grid.addWidget(self.a1_label, 3, 0); grid.addWidget(self.a1_input, 3, 1)
        grid.addWidget(self.q2_label, 4, 0); grid.addWidget(self.q2_input, 4, 1)
        grid.addWidget(self.a2_label, 5, 0); grid.addWidget(self.a2_input, 5, 1)
        main_layout.addLayout(grid)

        # Кнопки
        button_layout = QHBoxLayout()
        self.reset_all_button = QPushButton(self.loc.get("reset_all_data_button"))
        self.reset_all_button.setObjectName("resetButton")
        self.no_password_button = QPushButton() # Текст установится в configure_for_mode
        self.save_button = QPushButton()
        
        button_layout.addWidget(self.reset_all_button)
        button_layout.addStretch()
        button_layout.addWidget(self.no_password_button)
        button_layout.addWidget(self.save_button)
        main_layout.addLayout(button_layout)

        self.save_button.clicked.connect(self._on_save)

        self.no_password_button.clicked.connect(self._handle_no_password_button)
        self.reset_all_button.clicked.connect(self._reset_all_data)
        
        self.configure_for_mode()
        self.apply_theme()

    def configure_for_mode(self):
        """Настраивает вид и текст окна в зависимости от режима."""
        for widget in [self.new_pass_label, self.new_pass_input, self.confirm_pass_label, self.confirm_pass_input]:
            widget.show()
        
        self.q1_input.setReadOnly(False)
        self.q2_input.setReadOnly(False)

        if self.mode == 'setup':
            self.setWindowTitle(self.loc.get("setup_password_title"))
            self.intro_label.setText(self.loc.get("setup_password_intro"))
            self.save_button.setText(self.loc.get("setup_save_button"))
            self.no_password_button.setText(self.loc.get("setup_no_password_button"))
            self.no_password_button.show()
            self.reset_all_button.hide()
            for field in [self.new_pass_input, self.confirm_pass_input, self.q1_input, self.a1_input, self.q2_input, self.a2_input]:
                field.clear()
                field.setPlaceholderText("")

        elif self.mode == 'recover':
            self.setWindowTitle(self.loc.get("password_recovery_title"))
            self.intro_label.setText(self.loc.get("password_recovery_intro"))
            self.save_button.setText(self.loc.get("password_recovery_button"))
            
            self.new_pass_label.hide(); self.new_pass_input.hide()
            self.confirm_pass_label.hide(); self.confirm_pass_input.hide()
            self.no_password_button.hide()
            self.reset_all_button.show()
            
            q1, q2 = self.db.get_security_questions()
            self.q1_input.setText(q1 or ""); self.q1_input.setReadOnly(True)
            self.q2_input.setText(q2 or ""); self.q2_input.setReadOnly(True)
            self.a1_input.clear(); self.a2_input.clear()



        elif self.mode == 'change':
            self.setWindowTitle(self.loc.get("setup_password_title"))
            self.intro_label.setText(self.loc.get("leave_password_blank"))
            self.save_button.setText(self.loc.get("save_button"))
            
            self.no_password_button.setText(self.loc.get("remove_password_button"))
            self.no_password_button.show()

            self.reset_all_button.show()
            
            q1, q2 = self.db.get_security_questions()
            self.q1_input.setText(q1 or "")
            self.q2_input.setText(q2 or "")
            
            self.new_pass_input.setPlaceholderText(self.loc.get("new_password"))
            self.a1_input.setPlaceholderText(self.loc.get("new_answer"))
            self.a2_input.setPlaceholderText(self.loc.get("new_answer2"))
    
    def apply_theme(self):
        settings = self.data_manager.get_settings()
        is_dark, accent, bg, text, _ = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border = "#555" if is_dark else "#ced4da"
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; }}
            QLabel {{ color: {text}; }}
            QLineEdit {{
                background-color: {comp_bg}; border: 1px solid {border};
                border-radius: 4px; color: {text}; padding: 6px;
            }}
            QPushButton {{
                background-color: {accent}; color: white; border: none;
                padding: 8px 14px; border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {QColor(accent).lighter(110).name()}; }}
            QPushButton#resetButton {{
                background-color: #dc3545;
            }}
            QPushButton#resetButton:hover {{
                background-color: #c82333;
            }}
        """)

    def _on_save(self):
        if self.mode == 'recover':
            self._check_answers_and_reset()
        else: # 'setup' or 'change'
            self._set_new_password()

    def _set_new_password(self):
        new_pass = self.new_pass_input.text()
        confirm_pass = self.confirm_pass_input.text()
        q1 = self.q1_input.text().strip()
        a1 = self.a1_input.text()
        q2 = self.q2_input.text().strip()
        a2 = self.a2_input.text()

        # Валидация для 'setup'
        if self.mode == 'setup':
            if not new_pass or not confirm_pass or not q1 or not a1:
                self.error_label.setText(self.loc.get("error_fields_empty"))
                self.error_label.show()
                return
        
        # Общая валидация
        if new_pass != confirm_pass:
            self.error_label.setText(self.loc.get("error_passwords_mismatch"))
            self.error_label.show()
            return

        if self.mode == 'change':

            if new_pass and not confirm_pass:
                self.error_label.setText(self.loc.get("confirm_new_password"))
                self.error_label.show()
                return

            if not new_pass and not a1 and not a2 and q1 == self.db.get_security_questions()[0]:
                self.accept()
                return
        
        # Если пароль не меняется, передаем None, чтобы не обновлять его в БД
        final_password = new_pass if new_pass else None
        
        # Если ответ не меняется, передаем None
        final_a1 = a1 if a1 else None
        final_a2 = a2 if a2 else None
        
        self.db.set_password_and_questions(final_password, q1, final_a1, q2, final_a2)
        self.setup_successful.emit()
        self.accept()

    def _check_answers_and_reset(self):
        a1 = self.a1_input.text()
        a2 = self.a2_input.text()
        if self.db.check_security_answers(a1, a2):
            QMessageBox.information(self, self.loc.get("password_reset_title"), self.loc.get("password_reset_success"))

            self.mode = 'change'
            self.configure_for_mode()
            self.error_label.hide()
        else:
            self.error_label.setText(self.loc.get("error_answers_incorrect"))
            self.error_label.show()

    def _reset_all_data(self):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle(self.loc.get("reset_data_warning_title"))
        msg_box.setText(self.loc.get("reset_data_warning_text"))
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        
        # Применяем стили вручную
        settings = self.data_manager.get_settings()
        is_dark, accent, bg, text, _ = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border = "#555" if is_dark else "#ced4da"
        msg_box.setStyleSheet(f"""
            QMessageBox {{ background-color: {bg}; }}
            QMessageBox QLabel {{ color: {text}; }}
            QMessageBox QPushButton {{
                background-color: {comp_bg}; color: {text}; border: 1px solid {border};
                padding: 6px 12px; border-radius: 4px; min-width: 80px;
            }}
        """)
        
        reply = msg_box.exec()
        if reply == QMessageBox.StandardButton.Yes:
            if self.db.reset_all_data():
                QMessageBox.information(self, self.loc.get("success_title"), self.loc.get("delete_data_success"))

                QApplication.instance().exit(123)

    def _handle_no_password_button(self):
        """Обрабатывает клик по второй кнопке, в зависимости от режима."""
        # --- НОВАЯ УПРОЩЕННАЯ ЛОГИКА ---
        if self.db.is_password_set():
            # Если пароль есть (неважно, в каком мы режиме), предлагаем его удалить
            self._remove_password()
        else:
            # Если пароля нет (только в режиме 'setup'), просто продолжаем без него
            self.use_without_password.emit()
            self.accept()


    def _remove_password(self):
        """Удаляет пароль и все вопросы/ответы."""
        reply = QMessageBox.question(self, self.loc.get("password_remove_confirm_title"), self.loc.get("password_remove_confirm_text"))
        if reply == QMessageBox.StandardButton.Yes:
            self.db.set_password_and_questions("", "", "", "", "")
            QMessageBox.information(self, self.loc.get("success_title"), self.loc.get("password_removed_success"))
            
            self.use_without_password.emit() # Это для продолжения без пароля


            self.accept()

    def _set_new_password(self):
        new_pass = self.new_pass_input.text()
        confirm_pass = self.confirm_pass_input.text()
        q1 = self.q1_input.text().strip()
        a1 = self.a1_input.text()
        q2 = self.q2_input.text().strip()
        a2 = self.a2_input.text()

        if new_pass != confirm_pass:
            self.error_label.setText(self.loc.get("error_passwords_mismatch"))
            self.error_label.show()
            return


        if new_pass and (not q1 or not a1):
            self.error_label.setText(self.loc.gedt("error_change_q1"))
            self.error_label.show()
            return
        
 
        if not new_pass:
            q1, a1, q2, a2 = "", "", "", ""


        self.db.set_password_and_questions(new_pass, q1, a1, q2, a2)
        self.setup_successful.emit()
        self.accept()

# --- КЛАСС ДЛЯ ЭКСПОРТА В ПАПКИ ---
class Exporter:
    def __init__(self, db_manager, loc_manager):
        self.db = db_manager
        self.loc = loc_manager

    def _sanitize_filename(self, name):
        """Очищает и обрезает имя файла."""
        # Удаляем запрещенные символы
        name = re.sub(r'[\\/*?:"<>|]', "", name)
        # Заменяем несколько пробелов на один
        name = re.sub(r'\s+', ' ', name).strip()
        
        # --- НОВАЯ ЛОГИКА: ОБРЕЗАЕМ ДЛИННОЕ ИМЯ ---
        # Ограничиваем длину имени файла, оставляя место для ID и расширения
        max_len = 20 
        if len(name) > max_len:
            name = name[:max_len].strip()
        # --- КОНЕЦ ---

        if not name:
            name = self.loc.get("unnamed_note_title")
        return name

    def export_to_directory(self, target_dir, parent_widget, single_folder_data=None):
        """Главный метод, запускающий экспорт."""
        if single_folder_data:
            # Если передана одна папка, работаем только с ней
            note_tree = [single_folder_data]
        else:
            note_tree = self.db.get_full_note_tree()
        
        if not note_tree:
            QMessageBox.information(None, self.loc.get("export"), self.loc.get("export_no_notes"))
            return

        try:
            self._recursive_export(note_tree, target_dir)
            QMessageBox.information(parent_widget, self.loc.get("success_title"), self.loc.get("export_success_message"))
        except Exception as e:
            QMessageBox.critical(parent_widget, "error_title", self.loc.get("export_error_message"))

    def _recursive_export(self, nodes, current_path):
        """Рекурсивно обходит дерево и создает папки/файлы."""
        for node in nodes:
            node_type = node.get('type')
            node_title = node.get('title', self.loc.get("unnamed_note_title"))
            
            if node_type == 'folder':
                folder_name = self._sanitize_filename(node_title)
                new_path = os.path.join(current_path, folder_name)
                
                # Создаем папку, если ее нет
                if not os.path.exists(new_path):
                    os.makedirs(new_path)
                
                # Погружаемся в дочерние элементы
                if 'children' in node:
                    self._recursive_export(node.get('children', []), new_path)

            elif node_type == 'note':
                # Создаем имя файла. Добавляем ID для уникальности.
                node_id = node.get('id')
                file_name = f"{self._sanitize_filename(node_title)}_{node_id}.md"
                file_path = os.path.join(current_path, file_name)
                
                content = node.get('content', '')
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

# --- КЛАСС ДЛЯ ИМПОРТА ИЗ ПАПОК ---
class Importer:
    def __init__(self, db_manager, loc_manager):
        self.db = db_manager
        self.loc = loc_manager
        self.imported_count = 0

    def import_from_directory(self, source_dir, parent_note_id=None):
        """
        Главный метод, запускающий импорт.
        parent_note_id - ID папки в БД, куда будет производиться импорт.
        Если None - импорт в корень.
        """
        try:
            self._recursive_import(source_dir, parent_note_id)
            QMessageBox.information(None, self.loc.get("success_title"), self.loc.get("import_success_message").format(count=self.imported_count))
            return True
           
        except Exception as e:
            QMessageBox.critical(None, "error_title", self.loc.get("import_error_message"))
            return False

    def _recursive_import(self, current_path, parent_id_in_db):
        """Рекурсивно обходит папки и импортирует файлы и подпапки."""
        for entry in os.scandir(current_path):
            if entry.is_dir():
                # Если это папка, создаем ее в БД
                folder_name = entry.name
                new_folder_id = self.db.create_folder(parent_id_in_db, folder_name)
                # И рекурсивно импортируем ее содержимое
                self._recursive_import(entry.path, new_folder_id)
            
            elif entry.is_file():
                # Если это файл, проверяем расширение
                if entry.name.lower().endswith(('.md', '.txt')):
                    try:
                        with open(entry.path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Первая строка - заголовок, остальное - контент
                        title = content.split('\n', 1)[0].strip()
                        if not title:
                            # Если первая строка пустая, берем имя файла без расширения
                            title = os.path.splitext(entry.name)[0]
                        
                        self.db.create_note(parent_id_in_db, title, content)
                        self.imported_count += 1
                    except Exception as e:
                        print(f"Не удалось прочитать файл {entry.path}: {e}")
    
    def import_files(self, file_paths, parent_id_in_db):
        """Импортирует список отдельных файлов."""
        try:
            for file_path in file_paths:
                if file_path.lower().endswith(('.md', '.txt')):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    title = os.path.splitext(os.path.basename(file_path))[0]
                    self.db.create_note(parent_id_in_db, title, content)
                    self.imported_count += 1
            QMessageBox.information(None, self.loc.get("success_title"), self.loc.get("import_success_message").format(count=self.imported_count))
            return True
        except Exception as e:
            QMessageBox.critical(None, "error_title", self.loc.get("import_files_error_message"))
            return False

class ExportDialog(QDialog):
    """Диалог для выбора формата экспорта."""
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.loc = parent.loc if hasattr(parent, 'loc') else LocalizationManager()
        self.setWindowTitle(self.loc.get("export_menu", self.loc.get("export_menu")))
        
        self.layout = QVBoxLayout(self)
        self.info_label = QLabel(self.loc.get("select_export_format"))
        
        self.md_radio = QRadioButton("Markdown (.md)")
        self.pdf_radio = QRadioButton("PDF (.pdf)")
        self.md_radio.setChecked(True)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        
        self.layout.addWidget(self.info_label)
        self.layout.addWidget(self.md_radio)
        self.layout.addWidget(self.pdf_radio)
        self.layout.addWidget(self.buttons)

        # Применяем тему
        is_dark, accent, bg, text, _ = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border = "#555" if is_dark else "#ced4da"
        stylesheet = f"""
            QDialog {{ background-color: {bg}; }}
            QLabel, QRadioButton {{ color: {text}; }}
            QRadioButton::indicator {{
                width: 14px; height: 14px; border: 2px solid {border};
                border-radius: 8px; /* Делает индикатор круглым */
            }}
            QRadioButton::indicator:checked {{
                background-color: {accent}; border: 2px solid {accent};
            }}
            QPushButton {{
                background-color: {comp_bg}; color: {text}; border: 1px solid {border};
                padding: 6px 12px; border-radius: 4px; min-width: 80px;
            }}
            QPushButton:hover {{ border-color: {accent}; }}
        """
        self.setStyleSheet(stylesheet)

    def get_selected_format(self):
        if self.pdf_radio.isChecked():
            return "pdf"
        return "md"

# --- ДИАЛОГ ДЛЯ ВЫБОРА МЕСТА ИМПОРТА ---
class ImportTargetDialog(QDialog):
    def __init__(self, tree_data, db_manager, loc_manager, parent=None, settings=None): # <-- Добавляем loc_manager
        super().__init__(parent)
        self.loc = loc_manager # <-- Сохраняем его
        self.setWindowTitle(self.loc.get("import_target_dialog_title"))
        self.setMinimumWidth(350)
        self.db = db_manager
        
        self.selected_parent_id = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self.loc.get("import_target_label")))
        
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        layout.addWidget(self.tree_widget)
        
        self._load_and_populate_tree(tree_data)

        button_box = QDialogButtonBox()
        self.new_folder_button = button_box.addButton(self.loc.get("import_new_folder_button"), QDialogButtonBox.ButtonRole.ActionRole)
        ok_button = button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        cancel_button = button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        self.new_folder_button.clicked.connect(self._create_new_folder)
        layout.addWidget(button_box)
        
        # --- ВОССТАНАВЛИВАЕМ ПРИМЕНЕНИЕ ТЕМЫ ---
        if settings:
            is_dark, accent, bg, text, _ = theme_colors(settings)
            comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
            border = "#555" if is_dark else "#ced4da"
            
            self.setStyleSheet(f"""
                QDialog {{ background-color: {bg}; }}
                QLabel, QRadioButton {{ color: {text}; }}
                QTreeWidget {{
                    background-color: {comp_bg};
                    border: 1px solid {border};
                    border-radius: 4px;
                    color: {text};
                }}
                QTreeWidget::item:selected {{ background-color: {accent}; color: white; }}
                QPushButton {{
                    background-color: {comp_bg}; color: {text}; border: 1px solid {border};
                    padding: 6px 12px; border-radius: 4px; min-width: 80px;
                }}
                QPushButton:hover {{ border-color: {accent}; }}
            """)

    def _populate_folders(self, parent_item, children_data):
        for node in children_data:
            if node.get('type') == 'folder':
                item = QTreeWidgetItem(parent_item, [node.get('title')])
                item.setData(0, Qt.ItemDataRole.UserRole, node.get('id'))
                if 'children' in node:
                    self._populate_folders(item, node['children'])

    def accept(self):
        selected_item = self.tree_widget.currentItem()
        if selected_item:
            self.selected_parent_id = selected_item.data(0, Qt.ItemDataRole.UserRole)
        super().accept()

    def _load_and_populate_tree(self, tree_data):
        self.tree_widget.clear()
        root_item = QTreeWidgetItem(self.tree_widget, [self.loc.get("import_target_root")])
        root_item.setData(0, Qt.ItemDataRole.UserRole, None)
        self._populate_folders(root_item, tree_data)
        self.tree_widget.expandAll()
        self.tree_widget.setCurrentItem(root_item)

    def _create_new_folder(self):
        """Создает новую папку для импорта."""
        selected_item = self.tree_widget.currentItem()
        parent_id = selected_item.data(0, Qt.ItemDataRole.UserRole) if selected_item else None

        name, ok = QInputDialog.getText(self, self.loc.get("import_new_folder_prompt_title"), self.loc.get("import_new_folder_prompt_label"))
        if ok and name.strip():
            new_folder_id = self.db.create_folder(parent_id, name.strip())
            # Перезагружаем дерево, чтобы увидеть новую папку
            new_tree_data = self.db.get_note_tree()
            self._load_and_populate_tree(new_tree_data)
            # Находим и выделяем только что созданную папку
            self._find_and_select_item(new_folder_id)

    def _find_and_select_item(self, item_id):
        """Находит и выделяет элемент в дереве по ID."""
        def find_recursive(parent):
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child.data(0, Qt.ItemDataRole.UserRole) == item_id:
                    return child
                found = find_recursive(child)
                if found: return found
            return None
        item_to_select = find_recursive(self.tree_widget.invisibleRootItem())
        if item_to_select:
            self.tree_widget.setCurrentItem(item_to_select)

class TasksPanel(QWidget):
    def __init__(self, data_manager, parent=None):
        super().__init__()
        self.data_manager = data_manager
        self.db = data_manager.db # Получаем доступ к БД
        self.loc = data_manager.loc_manager
        self.main_parent = parent
        

        self.task_lists_cache = [] # [{id: 1, name: "Default"}, ...]
        self.current_list_index = -1
        
        layout = QVBoxLayout(self); 
        layout.setContentsMargins(0, 8, 0, 0) 
        layout.setSpacing(10)
        
        add_task_layout = QHBoxLayout()
        self.task_input = ThemedLineEdit(main_parent=self.main_parent) 
        self.add_button = QPushButton()
        self.add_button.clicked.connect(self.add_task_from_input)
        self.task_input.returnPressed.connect(self.add_task_from_input)
        self.templates_btn = QToolButton(); self.templates_btn.setText("⋮")
        self.templates_btn.clicked.connect(self.show_templates_menu)
        add_task_layout.addWidget(self.task_input, 1)
        add_task_layout.addWidget(self.templates_btn)
        add_task_layout.addWidget(self.add_button)
        
        list_mgmt_layout = QHBoxLayout(); list_mgmt_layout.setSpacing(5)
        self.prev_list_btn = QPushButton("<")
        self.prev_list_btn.clicked.connect(lambda: self.switch_list(-1))
        self.list_name_label = QLabel(); self.list_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.list_name_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_name_label.customContextMenuRequested.connect(self.show_list_context_menu)
        self.next_list_btn = QPushButton(">")
        self.next_list_btn.clicked.connect(lambda: self.switch_list(1))
        
        self.task_filter_combo = QComboBox()
        self.task_filter_combo.currentIndexChanged.connect(self.filter_tasks)
        
        target_height = 34
        self.prev_list_btn.setFixedSize(target_height, target_height)
        self.next_list_btn.setFixedSize(target_height, target_height)
        self.task_filter_combo.setFixedHeight(target_height)

        list_mgmt_layout.addWidget(self.prev_list_btn)
        list_mgmt_layout.addWidget(self.list_name_label, 1)
        list_mgmt_layout.addWidget(self.next_list_btn)
        list_mgmt_layout.addStretch()
        list_mgmt_layout.addWidget(self.task_filter_combo)
        
        self.task_list_widget = QListWidget(); self.task_list_widget.setObjectName("TaskList")
        self.task_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.task_list_widget.customContextMenuRequested.connect(self.show_task_context_menu)
        self.task_list_widget.itemDoubleClicked.connect(self.edit_task)
        
        self.task_list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.task_list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.task_list_widget.model().rowsMoved.connect(self._on_tasks_reordered)

        #self.task_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.task_list_widget.itemClicked.connect(self._on_task_item_clicked)
        
        layout.addLayout(add_task_layout)
        layout.addLayout(list_mgmt_layout)
        layout.addWidget(self.task_list_widget)

        self.load_task_lists() # Загружаем списки при инициализации

    def _on_tasks_reordered(self, parent, start, end, destination, row):
        """Вызывается после того, как пользователь перетащил задачу."""
        if self.current_list_index == -1: return

        current_list = self.task_lists_cache[self.current_list_index]
        list_id = current_list['id']
        
        # Собираем новый список ID в правильном порядке
        ordered_ids = []
        for i in range(self.task_list_widget.count()):
            item = self.task_list_widget.item(i)
            task_id = item.data(Qt.ItemDataRole.UserRole).get('id')
            if task_id:
                ordered_ids.append(task_id)
        
        # Отправляем новый порядок в базу данных
        self.db.update_tasks_order(list_id, ordered_ids)

    def _get_templates(self):
        return self.data_manager.get_settings().get("task_templates", [])

    def _set_templates(self, templates):
        settings = self.data_manager.get_settings()
        settings["task_templates"] = templates
        self.data_manager.save_settings()

    def _create_themed_menu(self):
        if self.main_parent and hasattr(self.main_parent, '_create_themed_menu'):
            return self.main_parent._create_themed_menu()
        return QMenu(self)

    def show_templates_menu(self):
        menu = self._create_themed_menu()
        templates = self._get_templates()
        if templates:
            for t in templates:
                action_text = f"{self.loc.get('add_task_button')}: {t}"
                menu.addAction(action_text, lambda tt=t: self._add_template_task(tt))
            menu.addSeparator()
        menu.addAction(self.loc.get('task_templates_title', 'Управление шаблонами…'), self._manage_templates)
        menu.exec(self.templates_btn.mapToGlobal(QPoint(0, self.templates_btn.height())))

    def _add_template_task(self, t):
        self.add_task(t) # Просто передаем текст
        
    def _manage_templates(self):
        dlg = TemplatesDialog(self, self.data_manager.get_settings(), self.loc)
        dlg.set_templates(self._get_templates())
        if dlg.exec():
            new_list = dlg.get_templates()
            self._set_templates(new_list)

    def retranslate_ui(self):
        self.add_button.setText(self.loc.get("add_task_button"))
        self.task_input.setPlaceholderText(self.loc.get("new_task_placeholder"))
        
        current_index = self.task_filter_combo.currentIndex()
        self.task_filter_combo.blockSignals(True)
        self.task_filter_combo.clear()
        self.task_filter_combo.addItem(self.loc.get("task_filter_all", "Все"))
        self.task_filter_combo.addItem(self.loc.get("task_filter_active", "Активные"))
        self.task_filter_combo.addItem(self.loc.get("task_filter_completed", "Выполненные"))
        self.task_filter_combo.setCurrentIndex(current_index if current_index != -1 else 0)
        self.task_filter_combo.blockSignals(False)
        self.filter_tasks()

        self.list_name_label.setToolTip(self.loc.get("list_management_tooltip"))
        self.templates_btn.setToolTip(self.loc.get("task_templates_title"))

    def add_task(self, text):
        """Добавляет новую задачу в БД и перезагружает список."""
        if not text or self.current_list_index == -1:
            return
        
        current_list = self.task_lists_cache[self.current_list_index]
        self.db.add_task(current_list['id'], text)
        
        # После добавления в БД, просто перезагружаем весь список
        self._load_current_list_display()

    def update_task_item_style(self, item):
        task_data = item.data(Qt.ItemDataRole.UserRole) or {}
        is_completed = task_data.get("completed", False)
        font = item.font()
        font.setStrikeOut(is_completed)
        item.setFont(font)
        
        settings = self.data_manager.get_settings()
        _, _, _, _, list_text_color = theme_colors(settings)
        final_color = QColor(list_text_color)
        if is_completed:
            final_color.setAlpha(120)
        item.setForeground(final_color)
        
        self.task_list_widget.blockSignals(True)
        item.setText(task_data.get("text", ""))
        item.setCheckState(Qt.CheckState.Checked if is_completed else Qt.CheckState.Unchecked)
        self.task_list_widget.blockSignals(False)

    def filter_tasks(self, index=0):
        mode = self.task_filter_combo.currentIndex()
        for i in range(self.task_list_widget.count()):
            item = self.task_list_widget.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole):
                # --- ИСПРАВЛЕНИЕ: Гарантированное приведение к bool ---
                # Значение 'completed' может быть True/False или 1/0.
                # bool() правильно обработает оба случая.
                is_completed = bool(item.data(Qt.ItemDataRole.UserRole).get("completed", False))

                
                if mode == 0: # Все
                    item.setHidden(False)
                elif mode == 1: # Активные
                    item.setHidden(is_completed)
                elif mode == 2: # Выполненные
                    item.setHidden(not is_completed)

    def add_task_from_input(self):
        task_text = self.task_input.text().strip()
        if task_text:
            self.add_task(task_text)
            self.task_input.clear()

    def show_task_context_menu(self, pos):
        item = self.task_list_widget.itemAt(pos)
        if not item: return
        menu = self._create_themed_menu()
        menu.addAction(self.loc.get("task_menu_edit"), lambda: self.edit_task(item))
        menu.addAction(self.loc.get("task_menu_toggle_completed"), lambda: self.toggle_task_completion(item))
        menu.addSeparator()
        menu.addAction(self.loc.get("delete_task_tooltip"), lambda: self.delete_task(item))
        menu.exec(self.task_list_widget.mapToGlobal(pos))

    def edit_task(self, item):
        if not item: return
        task_data = item.data(Qt.ItemDataRole.UserRole)
        old_text = task_data.get("text", "") # Используем правильный ключ 'text'
        task_id = task_data.get("id")
        
        dialog = ThemedInputDialog(self, self.loc.get("edit_task"), self.loc.get("new_text"), text=old_text, settings=self.data_manager.get_settings())
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_text = dialog.get_text().strip()
            if new_text and new_text != old_text:
                self.db.update_task(task_id, new_content=new_text)
                
                task_data["text"] = new_text
                item.setData(Qt.ItemDataRole.UserRole, task_data)
                self.update_task_item_style(item)

    def toggle_task_completion(self, item):
        if not item: return
        is_checked = item.checkState() == Qt.CheckState.Checked
        item.setCheckState(Qt.CheckState.Unchecked if is_checked else Qt.CheckState.Checked)

    def delete_task(self, item):
        row = self.task_list_widget.row(item)
        if row >= 0:
            task_id = item.data(Qt.ItemDataRole.UserRole).get('id')
            self.db.delete_task(task_id)
            self.task_list_widget.takeItem(row)

    def load_task_lists(self):

        self.task_lists_cache = self.db.get_all_task_lists()
        

        last_list_id = self.data_manager.settings.get("active_task_list_id")
        found_index = -1
        if last_list_id:
            for i, lst in enumerate(self.task_lists_cache):
                if lst['id'] == last_list_id:
                    found_index = i
                    break

        if found_index != -1:
            self.current_list_index = found_index
        elif self.task_lists_cache:
            self.current_list_index = 0
        else:
            self.current_list_index = -1

        self._load_current_list_display()

    def _load_current_list_display(self):
        self.task_list_widget.clear()
        
        if self.current_list_index == -1 or not self.task_lists_cache:
            self.list_name_label.setText(self.loc.get("no_lists"))
            self.task_input.setEnabled(False)
            self.add_button.setEnabled(False)
            return
            
        self.task_input.setEnabled(True)
        self.add_button.setEnabled(True)
        
        current_list = self.task_lists_cache[self.current_list_index]
        self.list_name_label.setText(f"<b>{current_list['name']}</b>")
        
        self.data_manager.settings["active_task_list_id"] = current_list['id']
        self.data_manager.save_settings()
        
        tasks_from_db = self.db.get_tasks_for_list(current_list['id'])
        for task in tasks_from_db:
            self._create_task_item(task)
        
        self.filter_tasks()
    def switch_list(self, direction):
        if not self.task_lists_cache or len(self.task_lists_cache) < 2: return

        new_index = (self.current_list_index + direction) % len(self.task_lists_cache)
        self.current_list_index = new_index
        self._load_current_list_display()

    def show_list_context_menu(self, pos):
        menu = self._create_themed_menu()
        menu.addAction(self.loc.get("add_list_menu"), self.add_new_list)
        if self.current_list_index != -1:
            menu.addAction(self.loc.get("rename_list_menu"), self.rename_current_list)
        
        if len(self.task_lists_cache) > 1:
            menu.addAction(self.loc.get("delete_list_menu"), self.delete_current_list)
            
        menu.exec(self.list_name_label.mapToGlobal(pos))

    def add_new_list(self):
        name, ok = QInputDialog.getText(self, self.loc.get("add_list_menu"), self.loc.get("new_list_prompt"))
        if ok and name.strip():
            self.db.add_task_list(name.strip())
            self.load_task_lists()
            self.current_list_index = len(self.task_lists_cache)
            self._load_current_list_display()

    def rename_current_list(self):
        if self.current_list_index == -1: return
        
        current_list = self.task_lists_cache[self.current_list_index]
        old_name = current_list['name']
        
        new_name, ok = QInputDialog.getText(self, self.loc.get("rename_list_menu"), self.loc.get("rename_item_dialog_label"), text=old_name)
        if ok and new_name.strip() and new_name.strip() != old_name:
            self.db.rename_task_list(current_list['id'], new_name.strip())
            self.load_task_lists()

    def delete_current_list(self):
        if self.current_list_index == -1 or len(self.task_lists_cache) <= 1: return
        
        current_list = self.task_lists_cache[self.current_list_index]
        reply = QMessageBox.question(self, self.loc.get("delete_list_menu"), self.loc.get("delete_list_confirm"))
        
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_task_list(current_list['id'])

            old_index = self.current_list_index
            self.load_task_lists()
            self.current_list_index = max(0, old_index - 1)
            self._load_current_list_display()


    def _on_task_item_clicked(self, item):
        task_data = item.data(Qt.ItemDataRole.UserRole)
        if not task_data:
            return

        is_completed_now = not task_data.get("completed", False)
        
        task_data["completed"] = is_completed_now
        item.setData(Qt.ItemDataRole.UserRole, task_data)

        task_id = task_data.get('id')
        self.db.update_task(task_id, is_completed=(1 if is_completed_now else 0))

        self.update_task_item_style(item)
        self.filter_tasks()

    def _create_task_item(self, task_data_from_db):
        """Создает QListWidgetItem на основе данных из БД."""
        if not task_data_from_db: return
        
        item_data = {
            'id': task_data_from_db.get('id'),
            'text': task_data_from_db.get('content', ''),
            'completed': bool(task_data_from_db.get('is_completed', 0))
        }
        
        item = QListWidgetItem()
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setData(Qt.ItemDataRole.UserRole, item_data)
        item.setSizeHint(QSize(0, 32))
        self.task_list_widget.addItem(item)
        
        self.update_task_item_style(item)

class NotesPanel(QWidget):
    tags_updated = pyqtSignal(set)
    zen_mode_requested = pyqtSignal(int)
    note_created = pyqtSignal(str)
    note_deleted = pyqtSignal(str)
    note_saved = pyqtSignal(str)
    dirty_state_changed = pyqtSignal(bool)

    def __init__(self, data_manager, parent=None):
        super().__init__()
        self.data_manager = data_manager
        self.db = data_manager.db
        self.loc = data_manager.loc_manager
        self.main_parent = parent
        self.is_dirty = False
        self.active_folder_id = None
        
        self.save_button = QToolButton()
        self.new_button = QToolButton()
        self.zen_button = QToolButton()
        self.window_button = QToolButton()
        self.preview_button = QToolButton()
        self.preview_button.setCheckable(True)
        self.search_input = ThemedLineEdit(main_parent=self.main_parent)
        self.tag_filter_combo = QComboBox()
        self.notes_editor_label = QLabel()
        self.editor_stack = QStackedWidget()
        self.notes_editor = NoteEditor(parent_panel=self)
        self.previewer = QTextBrowser()
        self.previewer.setOpenExternalLinks(True)
        self.editor_stack.addWidget(self.notes_editor)
        self.editor_stack.addWidget(self.previewer)
        
        # Собираем layout. Он будет использоваться в MainPopup

        self._setup_layout_for_popup()

        self.notes_editor.textChanged.connect(self.on_editor_text_changed)
        
        if isinstance(parent, WindowMain):
            self.notes_editor.save_and_new_requested.connect(self.handle_save_and_new_in_window)
        else:
            self.notes_editor.save_and_new_requested.connect(self._handle_save_and_new_popup)

        self.save_button.clicked.connect(self.save_current_note)

        if isinstance(parent, WindowMain):
            self.new_button.clicked.connect(parent.clear_editor)
        else:
            self.new_button.clicked.connect(lambda: self._create_new_item('note', None))
        
        if isinstance(parent, MainPopup):
            self.zen_button.clicked.connect(self.open_zen_mode)
        
        self.window_button.clicked.connect(self.data_manager.switch_to_window_mode)
        self.preview_button.toggled.connect(self.toggle_preview_mode)
        self.search_input.textChanged.connect(self._apply_filter_popup)
        self.tag_filter_combo.currentIndexChanged.connect(self._apply_filter_popup)

    def _set_dirty(self, is_dirty):
        """Централизованный метод для изменения флага is_dirty и отправки сигнала."""
        if self.is_dirty != is_dirty:
            self.is_dirty = is_dirty
            self.dirty_state_changed.emit(is_dirty)

    def on_data_changed(self):
        if self.notes_panel.is_dirty:
            self.status_label.setText(self.loc.get("unsaved_changes_status"))
            self.status_label.setStyleSheet("color:#dc3545;font-size:10px;margin-right:5px;")
        else:
            self.set_status_saved()

    def _open_context_menu(self, pos):
        item = self.tree_widget.itemAt(pos)
        menu = self._create_themed_menu()
        
        parent_for_new_item = item if (item and item.data(0, Qt.ItemDataRole.UserRole).get('type') == 'folder') else (item.parent() if item else None)
        
        menu.addAction(self.loc.get("tree_new_note_here"), lambda: self._create_new_item('note', parent_for_new_item))
        menu.addAction(self.loc.get("tree_new_folder"), lambda: self._create_new_item('folder', parent_for_new_item))

        if parent_for_new_item:
             menu.addAction(self.loc.get("import_files_title"), lambda: self.data_manager.import_files_here(parent_for_new_item))
        else: 
             menu.addAction(self.loc.get("import_files_title"), lambda: self.data_manager.import_files_here(None))

        if item:
            menu.addSeparator()
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            item_type = item_data.get('type')

            if item_type == 'folder':
                menu.addAction(self.loc.get("export_folder_title"), lambda: self.data_manager.export_notes(scope="folder", item=item))
            else: # note
                menu.addAction(self.loc.get("export_note_title"), lambda: self.data_manager.export_notes(scope="note", item=item))
            menu.addSeparator()

            if item_type == 'folder':
                menu.addAction(self.loc.get("tree_delete_folder"), lambda: self._delete_item(item))
            else:
                menu.addAction(self.loc.get("tree_delete_note"), lambda: self._delete_item(item))
                
            if item.parent():
                menu.addSeparator()
                menu.addAction(self.loc.get("move_item_up_title"), lambda: self._move_item_up(item))
                if item.parent().parent():
                     menu.addAction(self.loc.get("move_item_to_root_title"), lambda: self._move_item_to_root(item))
            
        menu.exec(self.tree_widget.viewport().mapToGlobal(pos))


    def _move_item_up(self, item):
        """Перемещает элемент на один уровень вверх в иерархии."""
        if not item or not item.parent():
            return
            
        item_id = item.data(0, Qt.ItemDataRole.UserRole).get('id')
        
        grandparent_item = item.parent().parent()
        new_parent_id = grandparent_item.data(0, Qt.ItemDataRole.UserRole).get('id') if grandparent_item else None
        
        self.db.move_item(item_id, new_parent_id)
        self.load_notes_for_popup()

    def _move_item_to_root(self, item):
        """Перемещает элемент в корень (делает его элементом верхнего уровня)."""
        if not item or not item.parent():
            return
        
        item_id = item.data(0, Qt.ItemDataRole.UserRole).get('id')
        
        self.db.move_item(item_id, None)
        self.load_notes_for_popup()


    def _create_new_item(self, item_type, parent_item_from_menu):
        """Создает новую заметку или папку в MainPopup."""
        self.save_current_note() 
        
        parent_id = None
        if parent_item_from_menu:
            parent_id = parent_item_from_menu.data(0, Qt.ItemDataRole.UserRole).get('id')
        elif self.active_folder_id:
            parent_id = self.active_folder_id
        
        if item_type == 'note':
            self.clear_for_new_note(force=True)
            self.notes_editor.setProperty("pending_parent_id", parent_id)
            self.notes_editor.setFocus()
        else:
            dialog = ThemedInputDialog(self, self.loc.get("import_new_folder_prompt_title"), self.loc.get("folder_name"), settings=self.data_manager.get_settings())
            if dialog.exec() == QDialog.DialogCode.Accepted:
                name = dialog.get_text().strip()
                if name:
                    new_folder_id = self.db.create_folder(parent_id, name)
                    self.load_notes_for_popup()
                    new_item = self._find_item_by_id(new_folder_id)
                    if new_item:
                        self.tree_widget.setCurrentItem(new_item)

    def _delete_item(self, item):
        """Удаляет элемент из дерева MainPopup."""
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        item_id = item_data.get('id')
        item_name = item.text(0) 

        display_name = item_name[:50] + '...' if len(item_name) > 50 else item_name

        # --- НОВЫЙ СПОСОБ СТИЛИЗАЦИИ ---
        settings = self.data_manager.get_settings()
        is_dark, accent, bg, text, _ = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border = "#555" if is_dark else "#ced4da"

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(self.loc.get("delete_item_confirm_title"))
        msg_box.setText(self.loc.get("delete_item_confirm_text").format(name=display_name)) 
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        # Получаем и применяем стиль
        dialog_style = get_global_dialog_stylesheet(self.data_manager.get_settings())
        msg_box.setStyleSheet(dialog_style)
        
        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Yes:

            parent_id = None
            if item.parent():
                parent_id = item.parent().data(0, Qt.ItemDataRole.UserRole).get('id')


            if item_id == self.notes_editor.property("current_note_id"):
                self.clear_for_new_note(force=True)

            self.db.delete_note_or_folder(item_id)
            self.load_notes_for_popup()

            if item_data.get('type') == 'note' and parent_id is not None:
                new_parent_item = self._find_item_by_id(parent_id)
                if new_parent_item:
                    self.tree_widget.setCurrentItem(new_parent_item)
                    self._on_tree_item_clicked(new_parent_item, 0)
            else:
                 self.clear_for_new_note(force=True)

    def load_notes_for_popup(self):
        """Загружает только корневые заметки и папки для MainPopup."""
        active_folder_id = self.active_folder_id 

        self.tree_widget.clear()
        tree_data = self.db.get_note_tree()
        self._populate_tree(self.tree_widget.invisibleRootItem(), tree_data)
        self.tree_widget.expandAll()

        if active_folder_id:
            item_to_reactivate = self._find_item_by_id(active_folder_id)
            if item_to_reactivate:
                self._set_active_folder(item_to_reactivate)

    def _populate_tree(self, parent_item, children_data):
        """Рекурсивно заполняет дерево (копия из NotesTreeSidebar)."""
        settings = self.data_manager.get_settings()
        for node_data in children_data:
            item = QTreeWidgetItem(parent_item, [node_data['title']])
            item.setData(0, Qt.ItemDataRole.UserRole, dict(node_data))
            if node_data['type'] == 'folder':
                item.setIcon(0, ThemedIconProvider.icon("folder", settings))
                if 'children' in node_data and node_data['children']:
                    self._populate_tree(item, node_data['children'])
            else:
                icon_name = "pin" if node_data.get('is_pinned') else "file"
                item.setIcon(0, ThemedIconProvider.icon(icon_name, settings))

    def _on_tree_item_clicked(self, item, column):
        """Обрабатывает клик по элементу в дереве."""
        self.save_current_note()

        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if item_data.get('type') == 'note':
            if self.active_folder_id:
                old_active_item = self._find_item_by_id(self.active_folder_id)
                if old_active_item:
                    font = old_active_item.font(0)
                    font.setBold(False)
                    old_active_item.setFont(0, font)
                self.active_folder_id = None
            self.display_selected_note(item_data.get('id'))
        elif item_data.get('type') == 'folder':
            self._set_active_folder(item)
            self.clear_for_new_note(force=True)
            self.notes_editor.setProperty("pending_parent_id", item_data.get('id'))

            self.is_dirty = False
            if hasattr(self.main_parent, 'on_data_changed'):
                self.main_parent.on_data_changed()

            self.notes_editor.setFocus()

    def display_selected_note(self, note_id):
        self.save_current_note()
        if not note_id: return
        
        note_details = self.db.get_note_details(note_id)
        if note_details:
            content = note_details.get('content', '')
            self.notes_editor.blockSignals(True)
            self.notes_editor.setPlainText(content)
            self.notes_editor.blockSignals(False)
            
            self.notes_editor.setProperty("current_note_id", note_id)
            
            self._set_dirty(False)

            if isinstance(self.main_parent, MainPopup):
                popup_settings = self.data_manager.get_settings().copy()
                popup_settings['zen_font_size'] = popup_settings.get('popup_editor_font_size', 12)
                popup_settings['window_editor_font_size'] = 0
                self.apply_editor_style(popup_settings)

            popup_state = self.data_manager.window_states['popup']
            if note_id == popup_state.get('id'):
                cursor = self.notes_editor.textCursor()
                pos = min(popup_state.get('cursor_pos', 0), len(content))
                cursor.setPosition(pos)
                self.notes_editor.setTextCursor(cursor)
            else:
                self.notes_editor.moveCursor(QTextCursor.MoveOperation.End)

            if hasattr(self.main_parent, 'preview_mode_active') and self.main_parent.preview_mode_active:
                self.preview_button.setChecked(True)
                self.toggle_preview_mode(True)
            else:
                self.preview_button.setChecked(False)
                self.editor_stack.setCurrentIndex(0)
            self.save_current_note()
        

    def save_current_note(self, force_save=False):
        try:
            note_id = self.notes_editor.property("current_note_id")
            content = self.notes_editor.toPlainText()
        except RuntimeError: return

        if not self.is_dirty and not force_save:
            return
            
        is_new_note = not note_id and content.strip()
        
        if self.notes_editor.isReadOnly(): return
            
        title = content.split('\n', 1)[0].strip() or self.loc.get("new_note_title")
        
        if note_id:
            self.db.update_note_content(note_id, title, content)
            item = self._find_item_by_id(note_id)
            if item:
                display_title = re.sub(r'#', '', title).strip()
                display_title = display_title[:30] + '...' if len(display_title) > 30 else display_title
                item.setText(0, display_title)
            
        elif content.strip():
            parent_id = self.notes_editor.property("pending_parent_id") or self.active_folder_id
            new_id = self.db.create_note(parent_id, title, content)
            self.notes_editor.setProperty("current_note_id", new_id)
            
            self.load_notes_for_popup()
            new_item = self._find_item_by_id(new_id)
            if new_item:
                self.tree_widget.setCurrentItem(new_item)
        
        self._set_dirty(False)
        

        if self.is_dirty or force_save:
            # Вызываем с небольшой задержкой, чтобы все успело обновиться
            QTimer.singleShot(10, self.retranslate_ui)


    def open_zen_mode(self):
        """Запускает Zen-режим для текущей или новой заметки."""
        note_id = 0
        
        if isinstance(self.main_parent, WindowMain):
            self.main_parent.save_current_item()
            # Если редактировалась заметка, берем ее ID
            if self.main_parent.current_edit_target and self.main_parent.current_edit_target[0] == 'note':
                note_id = self.main_parent.current_edit_target[1].data(0, Qt.ItemDataRole.UserRole).get('id')
        
        elif isinstance(self.main_parent, MainPopup):
            self.save_current_note()
            note_id = self.notes_editor.property("current_note_id")


        # Если note_id все еще None, он станет 0
        self.zen_mode_requested.emit(note_id or 0)

    def on_editor_text_changed(self):
        if self.notes_editor.isReadOnly():
            return
        self._set_dirty(True)


    def retranslate_ui(self):
        self.notes_editor_label.setText(self.loc.get("notes_editor_label"))
        
        self.save_button.setText(self.loc.get("save_button"))
        self.save_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        
        self.new_button.setText(self.loc.get("new_note_button"))
        self.new_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        
        self.zen_button.setText(self.loc.get("zen_button"))
        
        settings = self.data_manager.get_settings()
        self.zen_button.setToolTip(self.loc.get("zen_button_tooltip"))
        self.window_button.setToolTip(self.loc.get("window_button_tooltip"))
        self.window_button.setIcon(ThemedIconProvider.icon("window", settings))
        
        self._update_preview_button_icon(self.preview_button.isChecked())
        
        self.search_input.setPlaceholderText(self.loc.get("search_placeholder"))
        self.notes_editor.setPlaceholderText(self.loc.get("new_note_placeholder"))

        self.zen_button.setToolTip(self.loc.get("zen_button_tooltip"))
        self.window_button.setToolTip(self.loc.get("window_button_tooltip"))
        self.preview_button.setToolTip(self.loc.get("preview_tooltip"))
        
        current_text = self.tag_filter_combo.currentText()
        all_tags_text = self.loc.get("all_tags_combo")
        
        all_tags = self.db.get_all_tags()

        self.tag_filter_combo.blockSignals(True)
        self.tag_filter_combo.clear()
        self.tag_filter_combo.addItem(all_tags_text)
        if all_tags:
            self.tag_filter_combo.addItems(all_tags)
        
        idx = self.tag_filter_combo.findText(current_text)
        self.tag_filter_combo.setCurrentIndex(idx if idx != -1 else 0)
        self.tag_filter_combo.blockSignals(False)

    def _update_preview_button_icon(self, is_preview_mode):
        settings = self.data_manager.get_settings()
        icon_name = "edit_pencil" if is_preview_mode else "eye"
        self.preview_button.setIcon(ThemedIconProvider.icon(icon_name, settings))

    def toggle_preview_mode(self, checked):
        if hasattr(self.main_parent, 'preview_mode_active'):
            self.main_parent.preview_mode_active = checked
        self._update_preview_button_icon(checked)
        
        if checked:
            settings = self.data_manager.get_settings()
            is_dark, accent, bg, text_color, _ = theme_colors(settings)
            
            bg_color = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
            font_family = settings.get("zen_font_family", "sans-serif")
            font_size = settings.get('popup_editor_font_size', 12)
            
            self.previewer.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: {bg_color};
                    color: {text_color};
                    font-family: "{font_family}";
                    font-size: {font_size}pt;
                    border: none;
                    /* Добавляем простой внутренний отступ, который должен работать */
                    padding: 8px; 
                }}
            """)
            self.previewer.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.previewer.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            
            text = self.notes_editor.toPlainText()
            escaped_text = escape_markdown_tags(text)
            html_body = markdown.markdown(escaped_text, extensions=['fenced_code', 'tables', 'nl2br'])
            style_head = generate_markdown_css(settings)
            
            doc = self.previewer.document()
            text_option = doc.defaultTextOption()
            alignment_str = settings.get("zen_alignment", "left")
            alignment = Qt.AlignmentFlag.AlignJustify if alignment_str == "justify" else Qt.AlignmentFlag.AlignLeft
            text_option.setAlignment(alignment)
            doc.setDefaultTextOption(text_option)
            doc.setDefaultStyleSheet(style_head)
            self.previewer.setHtml(html_body)

            self.editor_stack.setCurrentIndex(1)
        else:
            self.editor_stack.setCurrentIndex(0)
            self.notes_editor.setFocus()

    def _create_themed_menu(self):
        if self.main_parent and hasattr(self.main_parent, '_create_themed_menu'):
            return self.main_parent._create_themed_menu()
        return QMenu(self)
    
    def find_tags(self, text):
        return set(re.findall(r'#(\w+)', text))

    def load_notes(self, notes_data):
        self.note_list_widget.clear()
        self.all_tags.clear()
        if not isinstance(notes_data, list):
            notes_data = []
            
        for note in notes_data:
            note.setdefault("pinned", False)
            self.add_note_item(note)
            self.all_tags.update(self.find_tags(note.get("text", "")))
        
        self.sort_note_items()
        self.update_tag_filter()
        self.tags_updated.emit(self.all_tags)
    
    
    def find_and_select_note_by_timestamp(self, timestamp):
        if not timestamp: return
        for i in range(self.note_list_widget.count()):
            item = self.note_list_widget.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) and item.data(Qt.ItemDataRole.UserRole).get('timestamp') == timestamp:
                self.note_list_widget.setCurrentItem(item)
                self.note_list_widget.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
                break
    
    def clear_for_new_note(self, force=False):
        if not force and self.is_dirty:
            self.save_current_note()
        
        if hasattr(self, 'tree_widget') and self.tree_widget.currentItem() is not None:
            self.tree_widget.clearSelection()

        self.notes_editor.clear()
        self.notes_editor.setProperty("current_note_id", None)
        
        self._set_dirty(False)

        self.notes_editor.setPlaceholderText(self.loc.get("new_note_placeholder"))
    
    def handle_save_and_new(self):
        self.save_current_note()
        self.clear_for_new_note(force=True)
    
    
    def save_if_dirty(self):
        if self.is_dirty:
            self.save_current_note()
    
    def apply_editor_style(self, settings):
        font_family = settings.get("zen_font_family", "Georgia")
        
        if isinstance(self.main_parent, WindowMain):
            font_size = settings.get("window_editor_font_size", 0)
            if font_size == 0:
                font_size = settings.get("zen_font_size", 12)
        elif isinstance(self.main_parent, MainPopup):
            font_size = settings.get("popup_editor_font_size", 12)
        else: # ZenMode
            font_size = settings.get("zen_font_size", 16)
        
        is_dark = settings.get("theme") == "dark"
        default_color = settings.get("dark_theme_text") if is_dark else settings.get("light_theme_text")
        editor_color = settings.get("zen_font_color") or default_color
        
        alignment = Qt.AlignmentFlag.AlignJustify if settings.get("zen_alignment") == "justify" else Qt.AlignmentFlag.AlignLeft
        
        padding_top = settings.get("editor_padding_top", 8)
        padding_bottom = settings.get("editor_padding_bottom", 8)
        padding_left = settings.get("editor_padding_left", 10)
        padding_right = settings.get("editor_padding_right", 10)

        comp_bg = QColor(settings.get("dark_theme_bg" if is_dark else "light_theme_bg")).lighter(115).name() if is_dark else QColor(settings.get("light_theme_bg")).darker(105).name()
        border_color = "#555" if is_dark else "#ced4da"

        self.notes_editor.setStyleSheet(f"""
            QTextEdit {{ 
                color: {editor_color};
                background-color: {comp_bg};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 0px; /* Сбрасываем CSS padding */
            }}
        """)
        
        self.notes_editor.setViewportMargins(padding_left, padding_top, padding_right, padding_bottom)

        f = self.notes_editor.font()
        f.setFamily(font_family)
        f.setPointSize(font_size)
        self.notes_editor.setFont(f)
        
        cursor = self.notes_editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        block_format = cursor.blockFormat()
        block_format.setAlignment(alignment)
        cursor.mergeBlockFormat(block_format)
        cursor.clearSelection()
        self.notes_editor.setTextCursor(cursor)

    def _set_active_folder(self, folder_item):
        """Устанавливает и подсвечивает активную папку по ее ID."""
        if self.active_folder_id:

            old_item = self._find_item_by_id(self.active_folder_id)

            if old_item:
                font = old_item.font(0)
                font.setBold(False)
                old_item.setFont(0, font)

        if folder_item:
            self.active_folder_id = folder_item.data(0, Qt.ItemDataRole.UserRole).get('id')
            font = folder_item.font(0)
            font.setBold(True)
            folder_item.setFont(0, font)
        else:
            self.active_folder_id = None

    def _on_tree_item_clicked(self, item, column):
        """Обрабатывает клик по элементу в дереве."""
        self.save_current_note()

        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if item_data.get('type') == 'note':
            if self.active_folder_id:
                old_active_item = self._find_item_by_id(self.active_folder_id)
                if old_active_item:
                    font = old_active_item.font(0)
                    font.setBold(False)
                    old_active_item.setFont(0, font)
                self.active_folder_id = None
            self.display_selected_note(item_data.get('id'))
        elif item_data.get('type') == 'folder':
            self._set_active_folder(item)

            self.clear_for_new_note(force=True)
            self.notes_editor.setProperty("pending_parent_id", item_data.get('id'))
            self.notes_editor.setFocus()

    def _find_item_by_id(self, item_id):
        """Рекурсивно ищет элемент в дереве по его ID."""
        if not item_id: return None
        
        def find_recursive(parent):
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child.data(0, Qt.ItemDataRole.UserRole).get('id') == item_id:
                    return child
                found = find_recursive(child)
                if found:
                    return found
            return None
            
        return find_recursive(self.tree_widget.invisibleRootItem())
        
    def _rename_item(self, item):
        """Переименовывает и папку, и заметку."""
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        item_id = item_data.get('id')
        

        fresh_item_data = self.db.get_note_details(item_id) or item_data
        old_name = fresh_item_data.get('title', "")

        
        new_name, ok = QInputDialog.getText(self, "Переименовать", "Новое имя:", text=old_name)
        if not ok or not new_name.strip() or new_name.strip() == old_name:
            return

        self.db.rename_item(item_id, new_name.strip())
        
        if (self.main_window.current_edit_target and
            self.main_window.current_edit_target[0] == 'note' and
            item_id == self.main_window.current_edit_target[1].data(0, Qt.ItemDataRole.UserRole).get('id')):
                
            content = self.main_window.notes_panel.notes_editor.toPlainText()
            parts = content.split('\n', 1)
            new_content = new_name.strip() + ('\n' + parts[1] if len(parts) > 1 else '')
            self.main_window.notes_panel.notes_editor.setPlainText(new_content)
            self.db.update_note_content(item_id, new_name.strip(), new_content)

        self.load_tree_from_db()
        self.select_item_by_id(item_id)

    def handle_save_and_new_in_window(self):
        """Обработчик для Shift+Enter в WindowMain: сохранить и создать новую."""
        if not isinstance(self.main_parent, WindowMain):
            return
            
        saved_note_id, parent_id = self.main_parent.save_current_item(force_save=True)
        
        self.main_parent.clear_editor()
        
        folder_to_activate = parent_id or self.main_parent.tree_sidebar.active_folder_id
        if folder_to_activate:
            item = self.main_parent.tree_sidebar.select_item_by_id(folder_to_activate)
            if item:
                self.main_parent.tree_sidebar._set_active_folder(item)

    def _on_item_dropped(self, moved_item, old_parent, new_parent):
        """Вызывается после того, как пользователь перетащил элемент в MainPopup."""
        if not moved_item:
            return

        moved_item_data = moved_item.data(0, Qt.ItemDataRole.UserRole)
        moved_id = moved_item_data.get('id')

        new_parent_id = None
        if new_parent and new_parent != self.tree_widget.invisibleRootItem():
            new_parent_id = new_parent.data(0, Qt.ItemDataRole.UserRole).get('id')

        self.db.update_item_parent_and_order(moved_id, new_parent_id, [])

    def _apply_filter_popup(self):
        """Применяет рекурсивный фильтр к дереву заметок в MainPopup."""
        search_text = self.search_input.text().strip().lower()
        
        selected_tag = self.tag_filter_combo.currentText()
        all_tags_text = self.loc.get("all_tags_combo")
        if selected_tag == all_tags_text:
            selected_tag = ""
            
        if not search_text and not selected_tag:
            visible_note_ids = {note['id'] for note in self.db.get_all_notes_flat()}
        else:
            visible_note_ids = set(self.db.search_notes(search_text, selected_tag))
        
        def is_item_visible(item):
            """Проверяет, должен ли элемент или его дочерние элементы быть видимыми."""
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            item_id = item_data.get('id')
            item_type = item_data.get('type')

            if item_type == 'note':
                # Заметка видима, если ее ID есть в списке
                return item_id in visible_note_ids
            
            elif item_type == 'folder':
                # Папка видима, если хотя бы один из ее дочерних элементов (на любом уровне) видим
                
                # Сначала проверяем, соответствует ли сама папка текстовому поиску
                if search_text and search_text in item_data.get('title', '').lower():
                    return True # Если да, показываем ее и все внутри

                # Если нет, рекурсивно проверяем дочерние элементы
                for i in range(item.childCount()):
                    if is_item_visible(item.child(i)):
                        return True # Нашли видимый дочерний элемент, значит, папку нужно показать
                
                return False # Ни один дочерний элемент не видим

        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            item.setHidden(not is_item_visible(item))

    def _populate_tree(self, parent_item, children_data):
        """Рекурсивно заполняет дерево (копия из NotesTreeSidebar)."""
        settings = self.data_manager.get_settings()
        for node_data in children_data:
            title = node_data.get('title', self.loc.get("unnamed_note_title"))
            display_title = title[:30] + '...' if len(title) > 30 else title

            item = QTreeWidgetItem(parent_item, [display_title])

            item.setData(0, Qt.ItemDataRole.UserRole, dict(node_data))
            if node_data['type'] == 'folder':
                item.setIcon(0, ThemedIconProvider.icon("folder", settings))
                if 'children' in node_data and node_data['children']:
                    self._populate_tree(item, node_data['children'])
            else:
                icon_name = "pin" if node_data.get('is_pinned') else "file"
                item.setIcon(0, ThemedIconProvider.icon(icon_name, settings))
    
    def _save_splitter_sizes(self, pos, index):
        """Сохраняет размеры сплиттера в MainPopup."""
        if isinstance(self.main_parent, MainPopup):
            sizes = self.splitter.sizes()
            if all(s > 0 for s in sizes): # Сохраняем, только если панели не свернуты в ноль
                settings = self.data_manager.get_settings()
                settings["popup_notes_splitter_sizes"] = sizes
                self.data_manager.save_settings()

    def _handle_save_and_new_popup(self):
        """Обрабатывает Shift+Enter в MainPopup."""

        self.save_current_note()
        
        parent_id = self.active_folder_id
        if not parent_id:
            try:
                # Если папка не активна, берем родителя только что сохраненной заметки
                saved_id = self.notes_editor.property("current_note_id")
                if saved_id:
                    parent_id = self.db.get_parent_id(saved_id)
            except RuntimeError:
                pass # На случай, если редактор был удален
        
        self.clear_for_new_note(force=True)
        self.notes_editor.setProperty("pending_parent_id", parent_id)
        self.notes_editor.setFocus()

    def _setup_layout_for_popup(self):
        """Собирает внутренний layout для использования в MainPopup."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.setSpacing(5)

        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0,0,0,0)
        editor_layout.setSpacing(5)
        editor_layout.addWidget(self.editor_stack, 1)

        button_layout = QHBoxLayout()
        for btn in [self.new_button, self.zen_button, self.window_button, self.preview_button]:
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button_layout.addWidget(self.new_button)
        button_layout.addWidget(self.zen_button)
        button_layout.addWidget(self.window_button)
        button_layout.addWidget(self.preview_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        editor_layout.addLayout(button_layout)
        
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0,0,0,0)
        tree_layout.setSpacing(5)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.search_input, 1)
        filter_layout.addWidget(self.tag_filter_combo)
        self.tree_widget = NotesTreeWidget(self)
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.itemClicked.connect(self._on_tree_item_clicked)
        self.tree_widget.setIndentation(15)
        self.tree_widget.setStyleSheet("QTreeWidget::item { height: 20px; }")
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self._open_context_menu)
        self.tree_widget.dropped.connect(self._on_item_dropped)
        tree_layout.addLayout(filter_layout)
        tree_layout.addWidget(self.tree_widget, 1)
        
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.addWidget(editor_container)
        self.splitter.addWidget(tree_container)
        splitter_sizes = self.data_manager.get_settings().get("popup_notes_splitter_sizes", [200, 200])
        self.splitter.setSizes(splitter_sizes)
        self.splitter.splitterMoved.connect(self._save_splitter_sizes)
        layout.addWidget(self.splitter)

    def display_folder_info(self, folder_data):
        """Показывает информацию о папке."""
        self.notes_editor.setProperty("current_note_id", None)
        self.is_dirty = False
        
        description = f"<i>Это папка. Выберите заметку для редактирования или создайте новую в этой папке.</i>"
        self.notes_editor.blockSignals(True)
        self.notes_editor.setHtml(description)
        self.notes_editor.blockSignals(False)
        self.notes_editor.setReadOnly(True)
        
        if hasattr(self.main_parent, 'on_data_changed'):
            self.main_parent.on_data_changed()

class TemplatesDialog(QDialog):
    def __init__(self, parent, settings, loc_manager):
        super().__init__(parent)
        self.settings = settings
        self.loc = loc_manager
        self.setWindowTitle(self.loc.get("task_templates_title"))
        self.resize(520, 460)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        
        self.info_label = QLabel(self.loc.get("task_templates_hint"))
        layout.addWidget(self.info_label)
        
        self.edit = QPlainTextEdit()
        self.edit.setTabChangesFocus(True)
        layout.addWidget(self.edit, 1)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(btns)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        
        self.apply_theme(self.settings)

    def set_templates(self, items):
        self.edit.setPlainText("\n".join(items))

    def get_templates(self):
        return [line.strip() for line in self.edit.toPlainText().splitlines() if line.strip()]

    def apply_theme(self, settings):
        is_dark, _, bg, text, _ = theme_colors(settings)
        component_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border_color = "#555" if is_dark else "#ced4da"
        hover = QColor(component_bg).lighter(110).name()
        self.setStyleSheet(f"""
            QDialog{{background-color:{bg};color:{text};}}
            QLabel{{background:transparent;color:{text};}}
            QPlainTextEdit{{background-color:{component_bg};color:{text};border:1px solid {border_color};border-radius:6px;padding:6px;}}
            QPushButton{{background-color:{component_bg};color:{text};border:1px solid {border_color};border-radius:6px;padding:6px 12px;}}
            QPushButton:hover{{background-color:{hover};}}
            QDialogButtonBox{{background:transparent;}}
        """)

class SettingsPanel(QWidget):
    settings_changed = pyqtSignal(dict)

    def __init__(self, current_settings, loc_manager, data_manager, parent=None, context="main_popup"):
        super().__init__(parent)
        self.settings = current_settings.copy()
        self.loc = loc_manager
        self.data_manager = data_manager
        self.context = context

        self.apply_timer = QTimer(self)
        self.apply_timer.setSingleShot(True)
        self.apply_timer.setInterval(250) # Задержка в мс
        self.apply_timer.timeout.connect(self.apply_changes)
        
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addStretch()
        
        self.container_frame = QFrame()
        self.container_frame.setObjectName("SettingsPanelFrame")
        outer_layout.addWidget(self.container_frame)
        outer_layout.addStretch()

        main_layout = QVBoxLayout(self.container_frame)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        title_layout = QHBoxLayout()
        self.title_label = QLabel()
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setObjectName("settingsCloseBtn")
        close_btn.clicked.connect(self.hide)
        title_layout.addWidget(close_btn)
        main_layout.addLayout(title_layout)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        self.color_widgets = {}
        
        self.general_tab = self.create_general_tab()
        self.appearance_tab = self.create_appearance_tab()
        self.zen_tab = self.create_zen_editor_tab()
        self.font_tab = self.create_font_tab()

        self.pdf_tab = self.create_pdf_tab()

        self.security_tab = self.create_security_tab()

        self.tab_widget.addTab(self.general_tab, "")
        self.tab_widget.addTab(self.appearance_tab, "")
        self.tab_widget.addTab(self.zen_tab, "")
        self.tab_widget.addTab(self.font_tab, "")
        self.tab_widget.addTab(self.security_tab, "")
        self.tab_widget.addTab(self.pdf_tab, "") 

        

        self.configure_tabs_visibility()
        self.load_settings_to_ui()
        self.connect_signals()
        self.retranslate_ui()
        self.apply_styles()

    def configure_tabs_visibility(self):
        is_zen_visible = (self.context == "zen_mode")
        self.tab_widget.setTabVisible(2, is_zen_visible)
        if hasattr(self, 'splitter_settings_container'):
             self.splitter_settings_container.setVisible(self.context == "window_main")

    def set_splitter_settings_visible(self, visible):
        if hasattr(self, 'splitter_settings_container'):
            self.splitter_settings_container.setVisible(visible)

    def create_general_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.lang_label = QLabel()
        self.lang_list_widget = QListWidget()
        self.lang_list_widget.setFixedHeight(120)
        layout.addWidget(self.lang_label)
        layout.addWidget(self.lang_list_widget)
        
        theme_box = QHBoxLayout()
        self.theme_label = QLabel()
        self.main_dark_radio = QRadioButton()
        self.main_light_radio = QRadioButton()
        self.theme_group = QButtonGroup(self)
        self.theme_group.addButton(self.main_dark_radio)
        self.theme_group.addButton(self.main_light_radio)
        theme_box.addWidget(self.theme_label)
        theme_box.addWidget(self.main_light_radio)
        theme_box.addWidget(self.main_dark_radio)
        theme_box.addStretch()
        layout.addLayout(theme_box)
        
        pos_box = QHBoxLayout()
        self.pos_label = QLabel()
        self.trigger_left_radio = QRadioButton()
        self.trigger_right_radio = QRadioButton()
        self.pos_group = QButtonGroup(self)
        self.pos_group.addButton(self.trigger_left_radio)
        self.pos_group.addButton(self.trigger_right_radio)
        pos_box.addWidget(self.pos_label)
        pos_box.addWidget(self.trigger_left_radio)
        pos_box.addWidget(self.trigger_right_radio)
        pos_box.addStretch()
        layout.addLayout(pos_box)

        self.startup_box = QGroupBox("Запускать при старте:")
        startup_layout = QHBoxLayout()
        
        self.startup_panel_radio = QRadioButton("Панель")
        self.startup_window_radio = QRadioButton("Окно")
        
        self.startup_group = QButtonGroup(self)
        self.startup_group.addButton(self.startup_panel_radio)
        self.startup_group.addButton(self.startup_window_radio)

        startup_layout.addWidget(self.startup_panel_radio)
        startup_layout.addWidget(self.startup_window_radio)
        startup_layout.addStretch()
        self.startup_box.setLayout(startup_layout)
        layout.addWidget(self.startup_box)

        separator = QFrame(); separator.setFrameShape(QFrame.Shape.HLine); separator.setFrameShadow(QFrame.Shadow.Sunken); layout.addWidget(separator)


        # Новые настройки бэкапов
        backup_grid = QGridLayout()
        self.backup_interval_label = QLabel()
        self.backup_interval_spin = QSpinBox()
        self.backup_interval_spin.setRange(1, 1440); self.backup_interval_spin.setSuffix(" min")
        self.backup_max_count_label = QLabel()
        self.backup_max_count_spin = QSpinBox()
        self.backup_max_count_spin.setRange(1, 100)
        backup_grid.addWidget(self.backup_interval_label, 0, 0)
        backup_grid.addWidget(self.backup_interval_spin, 0, 1)
        backup_grid.addWidget(self.backup_max_count_label, 1, 0)
        backup_grid.addWidget(self.backup_max_count_spin, 1, 1)
        backup_grid.setColumnStretch(2, 1)
        layout.addLayout(backup_grid)
        
        self.create_backup_btn = QPushButton()
        layout.addWidget(self.create_backup_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch()
        return tab
    
    def create_appearance_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        def create_color_picker(setting_key):
            h_layout = QHBoxLayout()
            label = QLabel()
            swatch = QLabel(); swatch.setFixedSize(20, 20); swatch.setStyleSheet("border: 1px solid #888;")
            btn = QPushButton()
            h_layout.addWidget(label, 1)
            h_layout.addWidget(swatch)
            h_layout.addWidget(btn)
            self.color_widgets[setting_key] = (label, swatch, btn)
            return h_layout

        for key in ["accent_color", "light_theme_bg", "light_theme_text", "light_theme_list_text", "dark_theme_bg", "dark_theme_text", "dark_theme_list_text"]:
            layout.addLayout(create_color_picker(key))
        
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        self.splitter_settings_container = QWidget()
        splitter_layout = QVBoxLayout(self.splitter_settings_container)
        splitter_layout.setContentsMargins(0,0,0,0)

        self.min_width_left_label = QLabel()
        self.min_width_left_spin = QSpinBox()
        self.min_width_left_spin.setRange(150, 500)
        self.min_width_left_spin.setSuffix(" px")
        width_layout_left = QHBoxLayout()
        width_layout_left.addWidget(self.min_width_left_label)
        width_layout_left.addWidget(self.min_width_left_spin)
        splitter_layout.addLayout(width_layout_left)

        self.min_width_right_label = QLabel()
        self.min_width_right_spin = QSpinBox()
        self.min_width_right_spin.setRange(250, 600)
        self.min_width_right_spin.setSuffix(" px")
        width_layout_right = QHBoxLayout()
        width_layout_right.addWidget(self.min_width_right_label)
        width_layout_right.addWidget(self.min_width_right_spin)
        splitter_layout.addLayout(width_layout_right)

        self.min_width_center_label = QLabel()
        self.min_width_center_spin = QSpinBox()
        self.min_width_center_spin.setRange(200, 800)
        self.min_width_center_spin.setSuffix(" px")
        width_layout_center = QHBoxLayout()
        width_layout_center.addWidget(self.min_width_center_label)
        width_layout_center.addWidget(self.min_width_center_spin)
        splitter_layout.addLayout(width_layout_center)

        
        layout.addWidget(self.splitter_settings_container)
        
        layout.addStretch()
        return tab

    def create_zen_editor_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.zen_bg_type_box = QGroupBox()
        bg_type_layout = QHBoxLayout()
        self.zen_bg_color_radio = QRadioButton("Цвет")
        self.zen_bg_procedural_radio = QRadioButton("Горы")
        self.zen_bg_image_radio = QRadioButton("Изображение")
        
        self.zen_bg_type_group = QButtonGroup(self)
        self.zen_bg_type_group.addButton(self.zen_bg_color_radio)
        self.zen_bg_type_group.addButton(self.zen_bg_procedural_radio)
        self.zen_bg_type_group.addButton(self.zen_bg_image_radio)
        
        bg_type_layout.addWidget(self.zen_bg_color_radio)
        bg_type_layout.addWidget(self.zen_bg_procedural_radio)
        bg_type_layout.addWidget(self.zen_bg_image_radio)
        bg_type_layout.addStretch()
        self.zen_bg_type_box.setLayout(bg_type_layout)
        layout.addWidget(self.zen_bg_type_box)


        self.zen_bg_settings_stack = QStackedWidget()
        layout.addWidget(self.zen_bg_settings_stack)


        color_page = QWidget()
        color_layout = QVBoxLayout(color_page)
        color_layout.setContentsMargins(0,0,0,0)
        color_layout.addLayout(self._create_color_picker_layout("zen_light_theme_bg"))
        color_layout.addLayout(self._create_color_picker_layout("zen_dark_theme_bg"))
        self.zen_bg_settings_stack.addWidget(color_page)

        self.zen_bg_settings_stack.addWidget(QWidget())

        image_page = QWidget()
        image_layout = QVBoxLayout(image_page)
        image_layout.setContentsMargins(0,0,0,0)
        bg_layout = QHBoxLayout()
        self.zen_bg_label = QLabel()
        self.bg_path_edit = QLineEdit()
        self.browse_button = QPushButton()
        self.clear_bg_button = QPushButton()
        btns_h = QHBoxLayout(); btns_h.setSpacing(6); btns_h.addWidget(self.browse_button); btns_h.addWidget(self.clear_bg_button)
        bg_layout.addWidget(self.zen_bg_label); bg_layout.addWidget(self.bg_path_edit, 1); bg_layout.addLayout(btns_h)
        image_layout.addLayout(bg_layout)
        self.zen_bg_settings_stack.addWidget(image_page)
        
        # --- Общие настройки Zen ---
        separator = QFrame(); separator.setFrameShape(QFrame.Shape.HLine); separator.setFrameShadow(QFrame.Shadow.Sunken); layout.addWidget(separator)
        opacity_layout = QHBoxLayout(); self.zen_opacity_label = QLabel(); self.zen_opacity_slider = QSlider(Qt.Orientation.Horizontal); self.zen_opacity_slider.setRange(0, 100); self.zen_opacity_value_label = QLabel("100%"); self.zen_opacity_value_label.setMinimumWidth(40); opacity_layout.addWidget(self.zen_opacity_label); opacity_layout.addWidget(self.zen_opacity_slider); opacity_layout.addWidget(self.zen_opacity_value_label); layout.addLayout(opacity_layout)
        padding_block = QVBoxLayout(); row_h = QHBoxLayout(); self.horiz_pad_label = QLabel(); self.horiz_padding = QSpinBox(); self.horiz_padding.setRange(0, 40); row_h.addWidget(self.horiz_pad_label); row_h.addWidget(self.horiz_padding); row_v = QHBoxLayout(); self.vert_pad_label = QLabel(); self.vert_padding = QSpinBox(); self.vert_padding.setRange(0, 40); row_v.addWidget(self.vert_pad_label); row_v.addWidget(self.vert_padding); padding_block.addLayout(row_h); padding_block.addLayout(row_v); layout.addLayout(padding_block)
        
        layout.addStretch()
        return tab
       
    def create_font_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        
        self.font_label = QLabel(); self.font_list_widget = QListWidget()
        
        self.font_search_edit = QLineEdit(); self.font_search_edit.textChanged.connect(self._filter_fonts)
        
        layout.addWidget(self.font_label); layout.addWidget(self.font_search_edit); layout.addWidget(self.font_list_widget, 1)

        size_color_layout = QHBoxLayout(); 
        self.size_label = QLabel(); 
        self.font_size_spin = QSpinBox(); 
        self.font_size_spin.setRange(8, 72); 
        size_color_layout.addWidget(self.size_label); 
        size_color_layout.addWidget(self.font_size_spin); 

        self.popup_size_label = QLabel("Размер (панель):")
        self.popup_font_size_spin = QSpinBox()
        self.popup_font_size_spin.setRange(8, 24)
        size_color_layout.addWidget(self.popup_size_label)
        size_color_layout.addWidget(self.popup_font_size_spin)

        size_color_layout.addStretch(); 
        self.font_color_label = QLabel(); 
        self.zen_font_color_swatch = QLabel(); 
        self.zen_font_color_swatch.setFixedSize(20, 20); 
        self.zen_font_color_swatch.setStyleSheet("border: 1px solid #888;"); 
        self.font_color_btn = QPushButton(); 
        self.clear_font_color_btn = QPushButton(); 
        size_color_layout.addWidget(self.font_color_label); 
        size_color_layout.addWidget(self.zen_font_color_swatch); 
        size_color_layout.addWidget(self.font_color_btn); 
        size_color_layout.addWidget(self.clear_font_color_btn); 
        layout.addLayout(size_color_layout)

        self.zen_align_group = QButtonGroup(self); align_layout = QHBoxLayout(); self.align_label = QLabel(); self.align_left_radio = QRadioButton(); self.align_justify_radio = QRadioButton(); self.zen_align_group.addButton(self.align_left_radio); self.zen_align_group.addButton(self.align_justify_radio); align_layout.addWidget(self.align_label); align_layout.addWidget(self.align_left_radio); align_layout.addWidget(self.align_justify_radio); align_layout.addStretch(); layout.addLayout(align_layout)
        
        
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        padding_grid = QGridLayout()
        padding_grid.setSpacing(10)
        
        self.padding_top_label = QLabel()
        self.padding_top_spin = QSpinBox()
        self.padding_top_spin.setRange(0, 100)
        padding_grid.addWidget(self.padding_top_label, 0, 0)
        padding_grid.addWidget(self.padding_top_spin, 0, 1)

        self.padding_bottom_label = QLabel()
        self.padding_bottom_spin = QSpinBox()
        self.padding_bottom_spin.setRange(0, 100)
        padding_grid.addWidget(self.padding_bottom_label, 0, 2)
        padding_grid.addWidget(self.padding_bottom_spin, 0, 3)

        self.padding_left_label = QLabel()
        self.padding_left_spin = QSpinBox()
        self.padding_left_spin.setRange(0, 100)
        padding_grid.addWidget(self.padding_left_label, 1, 0)
        padding_grid.addWidget(self.padding_left_spin, 1, 1)

        self.padding_right_label = QLabel()
        self.padding_right_spin = QSpinBox()
        self.padding_right_spin.setRange(0, 100)
        padding_grid.addWidget(self.padding_right_label, 1, 2)
        padding_grid.addWidget(self.padding_right_spin, 1, 3)
        
        layout.addLayout(padding_grid)
        
        return tab

    def _filter_fonts(self, text):
        text = text.lower()
        for i in range(self.font_list_widget.count()):
            item = self.font_list_widget.item(i)
            item.setHidden(text not in item.text().lower())

    def load_settings_to_ui(self):
        for widget in self.findChildren(QWidget):
            if isinstance(widget, (QListWidget, QSpinBox, QCheckBox, QLineEdit, QRadioButton)):
                widget.blockSignals(True)
        
        self.lang_list_widget.clear()
        current_lang_code = self.settings.get("language", "ru_RU")
        for code, name in self.loc.available_languages.items():
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, code)
            self.lang_list_widget.addItem(item)
            if code == current_lang_code:
                self.lang_list_widget.setCurrentItem(item)
                self.lang_list_widget.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)

        self.font_list_widget.clear()
        self.all_fonts = sorted(list(set(QFontDatabase.families())))
        self.font_list_widget.addItems(self.all_fonts)
        self.pdf_font_list_widget.addItems(self.all_fonts)
        current_font = self.settings.get("zen_font_family", "Georgia")
        items = self.font_list_widget.findItems(current_font, Qt.MatchFlag.MatchExactly)
        if items:
            self.font_list_widget.setCurrentItem(items[0])
            self.font_list_widget.scrollToItem(items[0], QAbstractItemView.ScrollHint.PositionAtCenter)

        (self.main_light_radio if self.settings.get("theme") == "light" else self.main_dark_radio).setChecked(True)
        (self.trigger_left_radio if self.settings.get("trigger_pos") == "left" else self.trigger_right_radio).setChecked(True)
        self.bg_path_edit.setText(self.settings.get("zen_bg_path", ""))
        
        opacity = self.settings.get("zen_editor_opacity", 85)
        self.zen_opacity_slider.setValue(opacity)
        self.zen_opacity_value_label.setText(f"{opacity}%")
        
        self.font_size_spin.setValue(self.settings.get("zen_font_size", 18))
        (self.align_left_radio if self.settings.get("zen_alignment", "left") == "left" else self.align_justify_radio).setChecked(True)
        self.horiz_padding.setValue(self.settings.get("zen_padding_horiz", 15))
        self.vert_padding.setValue(self.settings.get("zen_padding_vert", 10))
        
        self.padding_top_spin.setValue(self.settings.get("editor_padding_top", 8))
        self.padding_bottom_spin.setValue(self.settings.get("editor_padding_bottom", 8))
        self.padding_left_spin.setValue(self.settings.get("editor_padding_left", 10))
        self.padding_right_spin.setValue(self.settings.get("editor_padding_right", 10))

        self.min_width_left_spin.setValue(self.settings.get("window_min_width_left", 260))
        self.min_width_right_spin.setValue(self.settings.get("window_min_width_right", 380))
        
        self.backup_interval_spin.setValue(self.settings.get("backup_interval_min", 60))
        self.backup_max_count_spin.setValue(self.settings.get("backup_max_count", 10))
        

        current_pdf_font = self.settings.get("pdf_font_family", "Times New Roman")
        pdf_items = self.pdf_font_list_widget.findItems(current_pdf_font, Qt.MatchFlag.MatchExactly)
        if pdf_items:
            self.pdf_font_list_widget.setCurrentItem(pdf_items[0])
            self.pdf_font_list_widget.scrollToItem(pdf_items[0], QAbstractItemView.ScrollHint.PositionAtCenter)
 
        self.pdf_font_size_spin.setValue(self.settings.get("pdf_font_size", 11))
        self.pdf_text_color_swatch.setStyleSheet(f"background-color: {self.settings.get('pdf_text_color', '#000000')}; border: 1px solid #888;")
        
        self.pdf_margin_top_spin.setValue(self.settings.get("pdf_margin_top", 20))
        self.pdf_margin_bottom_spin.setValue(self.settings.get("pdf_margin_bottom", 20))
        self.pdf_margin_left_spin.setValue(self.settings.get("pdf_margin_left", 15))
        self.pdf_margin_right_spin.setValue(self.settings.get("pdf_margin_right", 15))

        self.popup_font_size_spin.setValue(self.settings.get("popup_editor_font_size", 12))

        self.update_color_swatches()
        
        for widget in self.findChildren(QWidget):
            if isinstance(widget, (QListWidget, QSpinBox, QCheckBox, QLineEdit, QRadioButton)):
                widget.blockSignals(False)
        startup_mode = self.settings.get("startup_mode", "panel")
        if startup_mode == "window":
            self.startup_window_radio.setChecked(True)
        else:
            self.startup_panel_radio.setChecked(True)

        bg_type = self.settings.get("zen_background_type", "procedural")
        if bg_type == "color":
            self.zen_bg_color_radio.setChecked(True)
        elif bg_type == "image":
            self.zen_bg_image_radio.setChecked(True)
        else:
            self.zen_bg_procedural_radio.setChecked(True)
        self._update_zen_bg_settings_visibility()

    def connect_signals(self):
        def _filter_pdf_fonts(text):
            text = text.lower()
            for i in range(self.pdf_font_list_widget.count()):
                item = self.pdf_font_list_widget.item(i)
                item.setHidden(text not in item.text().lower())


        self.lang_list_widget.currentItemChanged.connect(self.apply_timer.start)
        self.font_list_widget.currentItemChanged.connect(self.apply_timer.start)
        self.theme_group.buttonClicked.connect(self.apply_timer.start)
        self.pos_group.buttonClicked.connect(self.apply_timer.start)
        
        for key, (_, _, btn) in self.color_widgets.items():

            btn.clicked.connect(lambda _, k=key, s=self.color_widgets[key][1]: self.choose_color(k, s))
        
        self.bg_path_edit.editingFinished.connect(self.apply_timer.start)
        self.browse_button.clicked.connect(self.browse_for_image) 
        self.clear_bg_button.clicked.connect(self.clear_background)
        
        self.zen_opacity_slider.valueChanged.connect(self.apply_timer.start)
        self.zen_opacity_slider.valueChanged.connect(lambda v: self.zen_opacity_value_label.setText(f"{v}%")) # Обновляем лейбл сразу
        
        self.font_size_spin.valueChanged.connect(self.apply_timer.start)
        self.font_color_btn.clicked.connect(lambda: self.choose_color("zen_font_color", self.zen_font_color_swatch))
        self.clear_font_color_btn.clicked.connect(self.clear_font_color)
        self.zen_align_group.buttonClicked.connect(self.apply_timer.start)
        self.horiz_padding.valueChanged.connect(self.apply_timer.start)
        self.vert_padding.valueChanged.connect(self.apply_timer.start)

        self.padding_top_spin.valueChanged.connect(self.apply_timer.start)
        self.padding_bottom_spin.valueChanged.connect(self.apply_timer.start)
        self.padding_left_spin.valueChanged.connect(self.apply_timer.start)
        self.padding_right_spin.valueChanged.connect(self.apply_timer.start)
        
        self.min_width_left_spin.valueChanged.connect(self.apply_timer.start)
        self.min_width_right_spin.valueChanged.connect(self.apply_timer.start)
        self.min_width_center_spin.valueChanged.connect(self.apply_timer.start)
        
        self.backup_interval_spin.valueChanged.connect(self.apply_timer.start)
        self.backup_max_count_spin.valueChanged.connect(self.apply_timer.start)

        self.zen_bg_type_group.buttonClicked.connect(self.apply_timer.start)
        self.zen_bg_type_group.buttonClicked.connect(self._update_zen_bg_settings_visibility)

        self.lang_list_widget.currentItemChanged.connect(self._on_language_select)
        self.font_list_widget.currentItemChanged.connect(self.apply_timer.start)
        
        self.pdf_font_list_widget.currentItemChanged.connect(self.apply_timer.start)
        self.pdf_font_search_edit.textChanged.connect(_filter_pdf_fonts)

        if hasattr(self.data_manager, 'create_backup'):
            self.create_backup_btn.clicked.connect(lambda: self.data_manager.create_backup(notify=True))

    def retranslate_ui(self):
        self.title_label.setText(f"<b>{self.loc.get('settings_title')}</b>")
        self.tab_widget.setTabText(0, self.loc.get("settings_tab_general"))
        self.tab_widget.setTabText(1, self.loc.get("settings_tab_appearance"))
        self.tab_widget.setTabText(2, self.loc.get("settings_tab_zen"))
        self.tab_widget.setTabText(3, self.loc.get("settings_font_label"))
        self.tab_widget.setTabText(4, self.loc.get("settings_tab_security"))
        self.tab_widget.setTabText(5, self.loc.get("settings_pdf_tab"))
        
        # Вкладка "Общие"
        self.lang_label.setText(self.loc.get("settings_lang_label"))
        self.theme_label.setText(self.loc.get("settings_theme_label"))
        self.main_light_radio.setText(self.loc.get("settings_light_theme"))
        self.main_dark_radio.setText(self.loc.get("settings_dark_theme"))
        self.pos_label.setText(self.loc.get("settings_trigger_pos_label"))
        self.trigger_left_radio.setText(self.loc.get("settings_trigger_left"))
        self.trigger_right_radio.setText(self.loc.get("settings_trigger_right"))
        self.startup_box.setTitle(self.loc.get("startup_box_title"))
        self.startup_panel_radio.setText(self.loc.get("startup_panel_radio"))
        self.startup_window_radio.setText(self.loc.get("startup_window_radio"))
        self.backup_interval_label.setText(self.loc.get("settings_backup_interval"))
        self.backup_max_count_label.setText(self.loc.get("settings_backup_max_count"))
        self.create_backup_btn.setText(self.loc.get("settings_create_backup_now"))

        # Вкладка "Оформление"
        btn_text = self.loc.get("settings_choose_color_btn")
        for key, (label, _, btn) in self.color_widgets.items():
            # Пропускаем ключи Zen, так как они на другой вкладке
            if 'zen' not in key:
                label.setText(self.loc.get(f"settings_{key}_label", key))
                btn.setText(btn_text)
        self.min_width_left_label.setText(self.loc.get("settings_min_width_left"))
        self.min_width_right_label.setText(self.loc.get("settings_min_width_right"))
        self.min_width_center_label.setText(self.loc.get("settings_min_width_center"))

        self.pdf_text_color_btn.setText(self.loc.get("pdf_choose_button"))
            
        # Вкладка "Zen"

        self.zen_bg_color_radio.setText(self.loc.get("zen_bg_type_color"))
        self.zen_bg_procedural_radio.setText(self.loc.get("zen_bg_type_procedural"))
        self.zen_bg_image_radio.setText(self.loc.get("zen_bg_type_image"))
        self.color_widgets['zen_light_theme_bg'][0].setText(self.loc.get('settings_zen_light_theme_bg_label'))
        self.color_widgets['zen_dark_theme_bg'][0].setText(self.loc.get('settings_zen_dark_theme_bg_label'))
        self.zen_bg_label.setText(self.loc.get("settings_zen_bg_label"))
        self.browse_button.setText(self.loc.get("settings_browse_btn"))
        self.clear_bg_button.setText(self.loc.get("settings_clear_btn"))
        self.zen_opacity_label.setText(self.loc.get("zen_opacity_label"))
        self.horiz_pad_label.setText(self.loc.get("settings_padding_horiz"))
        self.vert_pad_label.setText(self.loc.get("settings_padding_vert"))
        self.zen_bg_type_box.setTitle(self.loc.get("zen_bg_type_box_title"))
        
        # Вкладка "Шрифт"
        self.font_label.setText(self.loc.get("settings_font_label"))
        self.font_search_edit.setPlaceholderText(self.loc.get("font_search_placeholder"))
        self.size_label.setText(self.loc.get("settings_size_label"))
        self.font_color_label.setText(self.loc.get("settings_font_color_label"))
        self.font_color_btn.setText(btn_text)
        self.clear_font_color_btn.setText(self.loc.get("settings_clear_btn"))
        self.align_label.setText(self.loc.get("settings_alignment_label"))
        self.align_left_radio.setText(self.loc.get("settings_align_left"))
        self.align_justify_radio.setText(self.loc.get("settings_align_justify"))
        self.padding_top_label.setText(self.loc.get("settings_padding_top"))
        self.padding_bottom_label.setText(self.loc.get("settings_padding_bottom"))
        self.padding_left_label.setText(self.loc.get("settings_padding_left"))
        self.padding_right_label.setText(self.loc.get("settings_padding_right"))
        self.popup_size_label.setText(self.loc.get("popup_font_size_label"))
        
        # Вкладка "Безопасность"
        if hasattr(self.data_manager, 'db') and self.data_manager.db.is_password_set():
             self.change_password_button.setText(self.loc.get("change_password_button"))
        else:
             self.change_password_button.setText(self.loc.get("setup_password_title"))

        # Вкладка "PDF"
        self.pdf_font_label.setText(self.loc.get("pdf_font_label"))
        self.pdf_size_label.setText(self.loc.get("pdf_size_label"))
        self.pdf_text_color_label.setText(self.loc.get("pdf_text_color_label"))
        self.pdf_margin_top_label.setText(self.loc.get("pdf_margin_top_label"))
        self.pdf_margin_bottom_label.setText(self.loc.get("pdf_margin_bottom_label"))
        self.pdf_margin_left_label.setText(self.loc.get("pdf_margin_left_label"))
        self.pdf_margin_right_label.setText(self.loc.get("pdf_margin_right_label"))
        self.pdf_text_color_btn.setText(btn_text)
        self.pdf_font_search_edit.setPlaceholderText(self.loc.get("pdf_font_search_placeholder"))


    def choose_color(self, setting_key, swatch_widget=None):
        current_color = self.settings.get(setting_key, "#ffffff") or "#ffffff"
        color = QColorDialog.getColor(QColor(current_color), self, "Выберите цвет")
        if color.isValid():
            self.settings[setting_key] = color.name()
            if swatch_widget:
                 swatch_widget.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")
            self.update_color_swatches()
            self.settings_changed.emit(self.settings.copy())
            
    def update_color_swatches(self):
        for key, (_, swatch, _) in self.color_widgets.items():
            swatch.setStyleSheet(f"background-color: {self.settings.get(key)}; border: 1px solid #888;")
        zen_color = self.settings.get("zen_font_color", "") or "#00000000"
        self.zen_font_color_swatch.setStyleSheet(f"background-color: {zen_color}; border: 1px solid #888;")

    def clear_font_color(self):
        self.settings["zen_font_color"] = ""
        self.update_color_swatches()
        self.settings_changed.emit(self.settings.copy())
        
    def browse_for_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if file_path:

            try:
                relative_path = os.path.relpath(file_path, BASE_PATH)
                if not relative_path.startswith('..'):
                    self.bg_path_edit.setText(relative_path)
                else:
                    self.bg_path_edit.setText(file_path) 
            except ValueError:

                self.bg_path_edit.setText(file_path)
            
            self.settings_changed.emit(self.settings.copy())

    def clear_background(self):
        self.bg_path_edit.setText("")
        self.settings["zen_bg_path"] = ""
        self.settings_changed.emit(self.settings.copy())

    def apply_styles(self):
        is_dark, accent, bg_color, text_color, _ = theme_colors(self.settings)
        line_edit_bg = "rgba(0,0,0,0.25)" if is_dark else "rgba(255,255,255,0.7)"
        button_bg = "rgba(80,80,80,1)" if is_dark else "#e1e1e1"
        border_color = "#555" if is_dark else "#b5b5b5"
        
        hover_color = QColor(accent).lighter(120).name() if is_dark else QColor(accent).darker(105).name()
        
        self.container_frame.setStyleSheet(f"""
            QFrame#SettingsPanelFrame {{
                background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 10px; }}
            #SettingsPanelFrame QWidget {{ background-color: transparent; }}""")
            
        self.setStyleSheet(f"""
            QGroupBox {{
                color: {text_color};
                font-weight: bold;
                border: 1px solid {border_color};
                border-radius: 6px;
                margin-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px 0 5px;
                left: 10px;
            }}
            QLabel, QCheckBox, QRadioButton {{ color:{text_color}; background:transparent; }}
            
            QLineEdit, QListWidget, QComboBox, QFontComboBox {{
                background-color: {line_edit_bg}; 
                border: 1px solid {border_color};
                color: {text_color}; 
                padding: 6px; 
                border-radius: 4px;
            }}
            
            /* --- НОВЫЙ АДАПТИВНЫЙ СТИЛЬ ВЫДЕЛЕНИЯ --- */
            QListWidget::item:selected, QFontComboBox QAbstractItemView::item:selected {{
                background-color: {accent};
                color: white;
            }}
            QListWidget::item:hover, QFontComboBox QAbstractItemView::item:hover {{
                background-color: {hover_color};
                color: white;
            }}
            /* Явно задаем фон для выпадающего списка */
            QComboBox QAbstractItemView {{
                background-color: {line_edit_bg};
                border: 1px solid {border_color};
                selection-background-color: {accent};
            }}
            /* --- КОНЕЦ --- */
            QRadioButton::indicator {{
                width: 14px; height: 14px; border: 2px solid {border_color};
                border-radius: 8px; /* КРУГЛЫЙ ИНДИКАТОР */
            }}
            QRadioButton::indicator:hover {{ border-color: {accent}; }}
            QRadioButton::indicator:checked {{
                background-color: {accent}; border: 2px solid {accent};
            }}
            QLineEdit, QListWidget {{
                background-color:{line_edit_bg}; border:1px solid {border_color};
                color:{text_color}; padding:6px; border-radius:4px;
            }}
            QSpinBox {{
                background-color:{line_edit_bg}; color:{text_color};
                border: 1px solid {border_color}; border-radius: 4px;
                padding: 1px; padding-right: 20px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                subcontrol-origin: border; width: 18px; border-radius: 0px;
                border-left-width: 1px; border-left-style: solid; border-left-color: {border_color};
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background-color: {QColor(button_bg).lighter(115).name()}; }}
            QSpinBox::up-button {{ subcontrol-position: top right; margin-top: 1px; }}
            QSpinBox::down-button {{
                subcontrol-position: bottom right; margin-bottom: 1px;
                border-top-width: 1px; border-top-style: solid; border-top-color: {border_color};
            }}
            QSpinBox::up-arrow {{ image: url(:/qt-project.org/styles/commonstyle/images/up-arrow-{"light" if is_dark else "dark"}.png); width: 10px; height: 10px; }}
            QSpinBox::down-arrow {{ image: url(:/qt-project.org/styles/commonstyle/images/down-arrow-{"light" if is_dark else "dark"}.png); width: 10px; height: 10px; }}

            QPushButton {{
                background-color:{button_bg}; color:{text_color}; border:1px solid {border_color};
                padding:6px 12px; border-radius:4px;
            }}
            QPushButton:hover {{ background-color:{QColor(button_bg).lighter(115).name()}; }}
            QTabWidget::pane {{ border:1px solid #444; }}
            QTabBar::tab {{
                background:{"rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.05)"};
                color:{text_color}; padding:8px 12px; border-top-left-radius:4px; border-top-right-radius:4px;
            }}
            QTabBar::tab:selected, QTabBar::tab:hover {{ background:{"rgba(255,255,255,0.18)" if is_dark else "rgba(0,0,0,0.1)"}; }}
            
            QSlider::groove:horizontal {{
                border: 1px solid {border_color};
                background: {line_edit_bg};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {accent};
                border: 1px solid {accent};
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QSlider::sub-page:horizontal {{
                background: {accent};
                border-radius: 3px;
            }}
        """)

    def _on_language_select(self):
        item = self.lang_list_widget.currentItem()
        if not item: return
        lang_code = item.data(Qt.ItemDataRole.UserRole)
        
        # --- ИСПРАВЛЕНИЕ: Мгновенно применяем язык ---
        if self.loc.current_lang != lang_code:
            self.loc.set_language(lang_code)
            self.retranslate_ui()
            
            self.settings["language"] = lang_code
            self.settings_changed.emit(self.settings.copy())


    def apply_changes(self):
        # Собираем все настройки из виджетов в self.settings
        lang_item = self.lang_list_widget.currentItem()
        if lang_item: self.settings["language"] = lang_item.data(Qt.ItemDataRole.UserRole)
        
        font_item = self.font_list_widget.currentItem()
        if font_item: self.settings["zen_font_family"] = font_item.text()
            
        self.settings["theme"] = "dark" if self.main_dark_radio.isChecked() else "light"
        self.settings["trigger_pos"] = "left" if self.trigger_left_radio.isChecked() else "right"
        
        if self.startup_window_radio.isChecked(): self.settings["startup_mode"] = "window"
        else: self.settings["startup_mode"] = "panel"

        self.settings["backup_interval_min"] = self.backup_interval_spin.value()
        self.settings["backup_max_count"] = self.backup_max_count_spin.value()
        
        self.settings["window_min_width_left"] = self.min_width_left_spin.value()
        self.settings["window_min_width_right"] = self.min_width_right_spin.value()
        self.settings["window_min_width_center"] = self.min_width_center_spin.value()

        if self.zen_bg_color_radio.isChecked(): self.settings["zen_background_type"] = "color"
        elif self.zen_bg_image_radio.isChecked(): self.settings["zen_background_type"] = "image"
        else: self.settings["zen_background_type"] = "procedural"
        
        self.settings["zen_bg_path"] = self.bg_path_edit.text()
        self.settings["zen_editor_opacity"] = self.zen_opacity_slider.value()
        self.settings["zen_padding_horiz"] = self.horiz_padding.value()
        self.settings["zen_padding_vert"] = self.vert_padding.value()

        self.settings["zen_font_size"] = self.font_size_spin.value()
        self.settings["popup_editor_font_size"] = self.popup_font_size_spin.value()
        self.settings["zen_alignment"] = "justify" if self.align_justify_radio.isChecked() else "left"
        
        self.settings["editor_padding_top"] = self.padding_top_spin.value()
        self.settings["editor_padding_bottom"] = self.padding_bottom_spin.value()
        self.settings["editor_padding_left"] = self.padding_left_spin.value()
        self.settings["editor_padding_right"] = self.padding_right_spin.value()

        self.settings["pdf_font_size"] = self.pdf_font_size_spin.value()
        self.settings["pdf_text_color"] = self.settings.get("pdf_text_color", "#000000") # Убедимся, что цвет сохраняется
        self.settings["pdf_margin_top"] = self.pdf_margin_top_spin.value()
        self.settings["pdf_margin_bottom"] = self.pdf_margin_bottom_spin.value()
        self.settings["pdf_margin_left"] = self.pdf_margin_left_spin.value()
        self.settings["pdf_margin_right"] = self.pdf_margin_right_spin.value()
        
        pdf_font_item = self.pdf_font_list_widget.currentItem()
        if pdf_font_item:
            self.settings["pdf_font_family"] = pdf_font_item.text()

        self.settings["pdf_font_size"] = self.pdf_font_size_spin.value()


        self.settings_changed.emit(self.settings.copy())

    def update_splitter_values(self, sizes):
        self.min_width_left_spin.blockSignals(True)
        self.min_width_right_spin.blockSignals(True)
        if len(sizes) == 3:
             self.min_width_left_spin.setValue(sizes[0])
             self.min_width_right_spin.setValue(sizes[2])
        self.min_width_left_spin.blockSignals(False)
        self.min_width_right_spin.blockSignals(False)

    def create_pdf_tab(self):
        """Создает вкладку с настройками экспорта в PDF."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        self.pdf_font_label = QLabel("Шрифт:")
        self.pdf_font_search_edit = QLineEdit()
        self.pdf_font_search_edit.setPlaceholderText("Поиск шрифта...")
        self.pdf_font_list_widget = QListWidget()
        
        layout.addWidget(self.pdf_font_label)
        layout.addWidget(self.pdf_font_search_edit)
        layout.addWidget(self.pdf_font_list_widget, 1)

        # --- Настройки размера и цвета (немного меняем компоновку) ---
        size_color_layout = QHBoxLayout()
        self.pdf_size_label = QLabel("Размер:")
        self.pdf_font_size_spin = QSpinBox()
        self.pdf_font_size_spin.setRange(8, 72)
        
        self.pdf_text_color_label = QLabel("Цвет текста:")
        self.pdf_text_color_swatch = QLabel()
        self.pdf_text_color_btn = QPushButton("Выбрать...")
        self.pdf_text_color_swatch.setFixedSize(20, 20)
        self.pdf_text_color_swatch.setStyleSheet("border: 1px solid #888;")

        size_color_layout.addWidget(self.pdf_size_label)
        size_color_layout.addWidget(self.pdf_font_size_spin)
        size_color_layout.addStretch()
        size_color_layout.addWidget(self.pdf_text_color_label)
        size_color_layout.addWidget(self.pdf_text_color_swatch)
        size_color_layout.addWidget(self.pdf_text_color_btn)
        layout.addLayout(size_color_layout)

        # --- Настройки отступов ---
        margins_layout = QGridLayout()
        margins_layout.setSpacing(8)
        self.pdf_margin_top_label = QLabel("Верхний отступ (мм):")
        self.pdf_margin_top_spin = QSpinBox(); self.pdf_margin_top_spin.setRange(0, 100)
        self.pdf_margin_bottom_label = QLabel("Нижний отступ (мм):")
        self.pdf_margin_bottom_spin = QSpinBox(); self.pdf_margin_bottom_spin.setRange(0, 100)
        self.pdf_margin_left_label = QLabel("Левый отступ (мм):")
        self.pdf_margin_left_spin = QSpinBox(); self.pdf_margin_left_spin.setRange(0, 100)
        self.pdf_margin_right_label = QLabel("Правый отступ (мм):")
        self.pdf_margin_right_spin = QSpinBox(); self.pdf_margin_right_spin.setRange(0, 100)
        margins_layout.addWidget(self.pdf_margin_top_label, 0, 0); margins_layout.addWidget(self.pdf_margin_top_spin, 0, 1)
        margins_layout.addWidget(self.pdf_margin_bottom_label, 1, 0); margins_layout.addWidget(self.pdf_margin_bottom_spin, 1, 1)
        margins_layout.addWidget(self.pdf_margin_left_label, 0, 2); margins_layout.addWidget(self.pdf_margin_left_spin, 0, 3)
        margins_layout.addWidget(self.pdf_margin_right_label, 1, 2); margins_layout.addWidget(self.pdf_margin_right_spin, 1, 3)
        layout.addLayout(margins_layout)
        
        layout.addStretch()
        return tab

    def _create_color_picker_layout(self, setting_key):
        h_layout = QHBoxLayout()
        label = QLabel()
        swatch = QLabel(); swatch.setFixedSize(20, 20); swatch.setStyleSheet("border: 1px solid #888;")
        btn = QPushButton()
        h_layout.addWidget(label, 1)
        h_layout.addWidget(swatch)
        h_layout.addWidget(btn)
        self.color_widgets[setting_key] = (label, swatch, btn)
        return h_layout

    def create_security_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        self.change_password_button = QPushButton()
        
        self.change_password_button.clicked.connect(self._open_password_change_dialog)
        
        layout.addWidget(self.change_password_button, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        return tab

    def _open_password_change_dialog(self):

        parent_window = self.parent()
        
        if parent_window and hasattr(parent_window, '_toggle_settings_panel_main'):
            parent_window._toggle_settings_panel_main()
        else:
            self.hide() 
        
        mode = 'change' if self.data_manager.db.is_password_set() else 'setup'
        
        dialog = PasswordSetupDialog(self.data_manager, self.loc, mode=mode)
        dialog.exec()
        
        if parent_window and hasattr(parent_window, '_toggle_settings_panel_main'):
            parent_window._toggle_settings_panel_main()

    def _update_zen_bg_settings_visibility(self):
        """Показывает/скрывает нужные настройки фона Zen."""
        if self.zen_bg_color_radio.isChecked():
            self.zen_bg_settings_stack.setCurrentIndex(0)
        elif self.zen_bg_procedural_radio.isChecked():
            self.zen_bg_settings_stack.setCurrentIndex(1)
        elif self.zen_bg_image_radio.isChecked():
            self.zen_bg_settings_stack.setCurrentIndex(2)

    def _update_zen_bg_settings_visibility(self):
        """Показывает/скрывает нужные настройки фона Zen."""
        if self.zen_bg_color_radio.isChecked():
            self.zen_bg_settings_stack.setCurrentIndex(0)
        elif self.zen_bg_procedural_radio.isChecked():
            self.zen_bg_settings_stack.setCurrentIndex(1)
        elif self.zen_bg_image_radio.isChecked():
            self.zen_bg_settings_stack.setCurrentIndex(2)

    def hideEvent(self, event):
        """Вызывается, когда панель настроек скрывается."""
        # --- НОВАЯ УСИЛЕННАЯ ЛОГИКА ---
        # Вне зависимости от таймера, принудительно собираем все текущие
        # значения с виджетов и отправляем сигнал на сохранение.
        self.apply_changes()
        super().hideEvent(event)

class ZenEditor(QTextEdit):
    def __init__(self, parent_window=None, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window

    def contextMenuEvent(self, event):
        standard_menu = self.createStandardContextMenu()
        if self.parent_window and hasattr(self.parent_window, '_create_themed_menu'):
            themed_menu = self.parent_window._create_themed_menu()
            themed_menu.addActions(standard_menu.actions())
            themed_menu.exec(event.globalPos())
        else:
            standard_menu.exec(event.globalPos())

# --- НОВЫЙ КЛАСС ДЛЯ ГЕНЕРАЦИИ ФОНА ZEN-РЕЖИМА ---
class ZenBackgroundWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self._cached_background = QPixmap()
        self._theme_palette = {}

    def set_theme_palette(self, palette):
        """Устанавливает цветовую палитру и инициирует перерисовку."""
        self._theme_palette = palette
        self._cached_background = QPixmap()
        self.update()

    def paintEvent(self, event):
        """Рисует фон, используя кэш."""
        if self._cached_background.isNull() or self._cached_background.size() != self.size():
            self._cached_background = QPixmap(self.size())
            self._render_background(self._cached_background)
        
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._cached_background)

    def _render_background(self, target_pixmap):
        """Основная логика отрисовки на QPixmap."""
        painter = QPainter(target_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = target_pixmap.width()
        height = target_pixmap.height()

        # --- 1. Рисуем небо ---
        sky_start_color = QColor(self._theme_palette.get('sky_start', '#87CEEB'))
        sky_end_color = QColor(self._theme_palette.get('sky_end', '#B0E0E6'))
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, sky_start_color)
        gradient.setColorAt(1, sky_end_color)
        painter.fillRect(target_pixmap.rect(), gradient)

        # --- 2. Рисуем солнце/луну ---
        #sun_color = QColor(self._theme_palette.get('sun', '#FFD700'))
        #sun_glow_color = QColor(self._theme_palette.get('sun_glow', '#FFFACD'))
        #sun_glow_color.setAlpha(100)
        
        #sun_size = min(width, height) / 5
        #sun_x = width * 0.8
        #sun_y = height * 0.2
        
        # Эффект свечения
        #painter.setBrush(sun_glow_color)
        #painter.setPen(Qt.PenStyle.NoPen)
        #painter.drawEllipse(QPointF(sun_x, sun_y), sun_size * 0.7, sun_size * 0.7)
        #painter.drawEllipse(QPointF(sun_x, sun_y), sun_size * 0.8, sun_size * 0.8)
        
        # Само солнце/луна
        #painter.setBrush(sun_color)
        #painter.drawEllipse(QPointF(sun_x, sun_y), sun_size / 2, sun_size / 2)

        # --- 3. Рисуем горы (несколько слоев) ---
        mountain_colors = self._theme_palette.get('mountains', ['#2F4F4F', '#696969', '#A9A9A9'])
        
        # Дальний хребет
        self._draw_mountain_range(painter, height * 0.85, height * 0.3, QColor(mountain_colors[0]), width, height, seed=1)
        # Средний хребет
        self._draw_mountain_range(painter, height * 0.9, height * 0.2, QColor(mountain_colors[1]), width, height, seed=2)
        # Ближний хребет
        self._draw_mountain_range(painter, height * 0.95, height * 0.1, QColor(mountain_colors[2]), width, height, seed=3)
        
        painter.end()

    def _draw_mountain_range(self, painter, base_y, max_height, color, width, height, seed):
        """Рисует один горный хребет."""
        from random import Random
        rand = Random(seed)

        points = [QPointF(0, base_y)]
        
        current_x = 0
        while current_x < width:
            peak_y = base_y - rand.uniform(max_height * 0.5, max_height)
            current_x += rand.uniform(width * 0.2, width * 0.4)
            points.append(QPointF(current_x, peak_y))
        
        points.append(QPointF(width, base_y))
        points.append(QPointF(width, height))
        points.append(QPointF(0, height))
        
        polygon = QPolygonF(points)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(polygon)


class ZenModeWindow(QWidget, ThemedMenuMixin):
    zen_exited = pyqtSignal(int, str)
    zen_saved_and_closed = pyqtSignal(int, str)
    
    def __init__(self, note_id, settings, loc_manager, data_manager):
        super().__init__()
        self.setObjectName("ZenModeWindow")
        self.settings = settings
        self.loc = loc_manager
        self.data_manager = data_manager
        self.db = data_manager.db
        self.note_id = note_id
        
        initial_text = ""
        if self.note_id:
            note_details = self.db.get_note_details(self.note_id)
            if note_details:
                initial_text = note_details.get('content', '')

        self.pomodoro_timer = QTimer(self)
        self.pomodoro_timer.timeout.connect(self.update_pomodoro)
        self.pomodoro_time_left = POMODORO_WORK_TIME
        self.is_work_time = True
        self.pomodoro_running = False
        
        self.pomodoro_player = QMediaPlayer()
        self.pomodoro_audio_output = QAudioOutput()
        self.pomodoro_player.setAudioOutput(self.pomodoro_audio_output)
        
        sound_path = os.path.join(BASE_PATH, "pomodoro_end.wav")
        if os.path.exists(sound_path):
            self.pomodoro_player.setSource(QUrl.fromLocalFile(sound_path))

        self.background_widget = ZenBackgroundWidget(self)

        self.editor_container = QWidget(self)
        self.editor_container.setStyleSheet("background: transparent;")
        editor_layout = QVBoxLayout(self.editor_container)
        editor_layout.setSpacing(0)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        
        self.editor_stack = QStackedWidget()
        self.editor = ZenEditor(parent_window=self)
        self.previewer = QTextBrowser()
        self.previewer.setOpenExternalLinks(True)

        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.previewer.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.previewer.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.editor_stack.addWidget(self.editor)
        self.editor_stack.addWidget(self.previewer)
        self.bottom_panel = self.create_bottom_panel()
        
        editor_layout.addWidget(self.editor_stack, 1)
        editor_layout.addWidget(self.bottom_panel)
        
        self.editor.setPlainText(initial_text)
        source_key = 'window' if self.data_manager.zen_return_to_window_mode else 'popup'
        cursor_pos = self.data_manager.window_states[source_key].get('cursor_pos', 0)
        
        cursor = self.editor.textCursor()
        pos = min(cursor_pos, len(initial_text))
        cursor.setPosition(pos)
        self.editor.setTextCursor(cursor)

        self.editor.textChanged.connect(self.update_word_count)


        self.exit_button = QPushButton(self)
        self.exit_button.setFixedSize(32, 32)
        self.exit_button.clicked.connect(self.close)
        
        self.settings_panel = SettingsPanel(
            self.settings, self.loc, self.data_manager, self, context="zen_mode"
        )
        self.settings_panel.settings_changed.connect(self.data_manager.update_settings)
        self.settings_panel.hide()
        self.settings_panel.installEventFilter(self)
                
        self.audio_container = None
        self.global_audio_widget = None
        self._global_audio_controller = None
        self._overlay = None
        self._audio_overlay = None
        
        self.loc.language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()
        self.editor.setFocus()
        
        self.update_background_and_styles()

    def _update_preview_button_icon(self, is_preview_mode):
        settings = self.data_manager.get_settings()
        icon_name = "edit_pencil" if is_preview_mode else "eye"
        self.preview_button.setIcon(ThemedIconProvider.icon(icon_name, settings, QSize(18, 18)))


    def toggle_preview_mode(self, checked):
        self._update_preview_button_icon(checked)
        if checked:

            text = self.editor.toPlainText()
            escaped_text = escape_markdown_tags(text)
            html_body = markdown.markdown(escaped_text, extensions=['fenced_code', 'tables', 'nl2br'])
            
            settings = self.settings
            style_head = generate_markdown_css(settings)

            doc = self.previewer.document()
            text_option = doc.defaultTextOption()
            alignment_str = settings.get("zen_alignment", "left")
            alignment = Qt.AlignmentFlag.AlignJustify if alignment_str == "justify" else Qt.AlignmentFlag.AlignLeft
            text_option.setAlignment(alignment)
            doc.setDefaultTextOption(text_option)

            self.previewer.setHtml(style_head + html_body)

            self.editor_stack.setCurrentIndex(1)
        else:
            self.editor_stack.setCurrentIndex(0)

    def eventFilter(self, obj, event):
        if obj is self.settings_panel and event.type() == QEvent.Type.Show:
             if self._audio_overlay and self._audio_overlay.isVisible():
                self.audio_container.hide()
                self._audio_overlay.hide()
                
        if obj is self.settings_panel and event.type() == QEvent.Type.Hide:
            if self._overlay and self._overlay.isVisible():
                self._overlay.hide()
        return super().eventFilter(obj, event)

    def toggle_settings_panel(self):
        if self.settings_panel.isVisible():
            self.settings_panel.hide()
            return
            
        if not self._overlay:
            self._overlay = QWidget(self)
            self._overlay.setObjectName("zenOverlay")
            self._overlay.setStyleSheet("background: transparent;")
            self._overlay.mousePressEvent = self._overlay_clicked
            
        self._overlay.setGeometry(self.rect())
        self._overlay.show()
        
        self.settings_panel.setParent(self)
        panel_size = self.settings_panel.sizeHint()
        x = (self.width() - panel_size.width()) // 2
        y = (self.height() - panel_size.height()) // 2
        self.settings_panel.move(x, y)
        self.settings_panel.show()
        self.settings_panel.raise_()
    
    def _overlay_clicked(self, event):
        if not self.settings_panel.geometry().contains(event.pos()):
            self.settings_panel.hide()
            self._overlay.hide()
            
    def retranslate_ui(self):
        self.pomodoro_title_label.setText(f"<b>{self.loc.get('pomodoro_label')}</b>")
        self.pomodoro_start_button.setText(self.loc.get('pomodoro_start_btn') if not self.pomodoro_running else self.loc.get('pomodoro_pause_btn'))
        self.pomodoro_reset_button.setText(self.loc.get('pomodoro_reset_btn'))
        self.update_word_count()

    def create_bottom_panel(self):
        panel = QWidget()
        panel.setObjectName("bottomPanel")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(10)

        pomodoro_container = QFrame()
        pomodoro_container.setObjectName("textContainer")
        pomodoro_layout = QHBoxLayout(pomodoro_container)
        pomodoro_layout.setContentsMargins(10, 0, 10, 0)
        
        self.pomodoro_title_label = QLabel(f"<b>{self.loc.get('pomodoro_label')}</b>")
        self.pomodoro_label = QLabel("25:00")
        self.pomodoro_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pomodoro_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pomodoro_layout.addWidget(self.pomodoro_title_label)
        pomodoro_layout.addWidget(self.pomodoro_label)

        self.pomodoro_start_button = QPushButton(self.loc.get('pomodoro_start_btn'))
        self.pomodoro_reset_button = QPushButton(self.loc.get('pomodoro_reset_btn'))
        self.pomodoro_start_button.clicked.connect(self.start_pause_pomodoro)
        self.pomodoro_reset_button.clicked.connect(self.reset_pomodoro)
        
        self.global_audio_btn = QPushButton()
        self.global_audio_btn.setToolTip(self.loc.get("audio_toggle_tooltip"))
        self.global_audio_btn.clicked.connect(self._toggle_global_audio_widget)

        words_container = QFrame()
        words_container.setObjectName("textContainer")
        words_layout = QHBoxLayout(words_container)
        words_layout.setContentsMargins(10, 2, 10, 2)
        
        self.word_count_label = QLabel(self.loc.get('word_count_label') + ": 0")
        words_layout.addWidget(self.word_count_label)
        
        self.preview_button = QPushButton(self)
        self.preview_button.setCheckable(True)
        self.preview_button.toggled.connect(self.toggle_preview_mode)

        self.settings_button = QPushButton(self)
        self.settings_button.clicked.connect(self.toggle_settings_panel)

        layout.addWidget(pomodoro_container)
        layout.addWidget(self.pomodoro_start_button)
        layout.addWidget(self.pomodoro_reset_button)
        layout.addWidget(self.global_audio_btn)
        layout.addStretch()
        layout.addWidget(words_container)
        layout.addWidget(self.preview_button) 
        layout.addSpacing(10)
        layout.addWidget(self.settings_button)

        QApplication.processEvents() 
        base_height = self.pomodoro_start_button.sizeHint().height()
        target_height = int(base_height * 1.25)

        pomodoro_container.setFixedHeight(target_height)
        self.pomodoro_start_button.setFixedHeight(target_height)
        self.pomodoro_reset_button.setFixedHeight(target_height)
        self.global_audio_btn.setFixedHeight(target_height)
        words_container.setFixedHeight(target_height)
        self.preview_button.setFixedSize(target_height, target_height)
        self.settings_button.setFixedSize(target_height, target_height)

        return panel
        
    def start_pause_pomodoro(self):
        self.pomodoro_running = not self.pomodoro_running
        self.retranslate_ui()
        if self.pomodoro_running:
            self.pomodoro_timer.start(1000)
        else:
            self.pomodoro_timer.stop()

    def reset_pomodoro(self):
        self.pomodoro_timer.stop()
        self.pomodoro_running = False
        self.is_work_time = True
        self.pomodoro_time_left = POMODORO_WORK_TIME
        self.retranslate_ui()
        self.update_pomodoro_label()

    def update_pomodoro(self):
        if not self.pomodoro_running:
            return
        self.pomodoro_time_left -= 1
        self.update_pomodoro_label()
        if self.pomodoro_time_left <= 0:
            if self.pomodoro_player.source().isValid():
                self.pomodoro_player.play()
            self.is_work_time = not self.is_work_time
            self.pomodoro_time_left = POMODORO_WORK_TIME if self.is_work_time else POMODORO_BREAK_TIME

    def update_pomodoro_label(self):
        mins, secs = divmod(self.pomodoro_time_left, 60)
        self.pomodoro_label.setText(f"{mins:02d}:{secs:02d}")

    def update_word_count(self):
        text = self.editor.toPlainText()
        cnt = len(text.split()) if text else 0
        self.word_count_label.setText(f"{self.loc.get('word_count_label')}: {cnt}")

    def attach_global_audio_widget(self, controller, loc=None):
        self._global_audio_controller = controller
        if self.audio_container is None:
            try:
                self.audio_container = QFrame(self)
                self.audio_container.setObjectName("audioWidgetContainer")
                wrapper = QVBoxLayout(self.audio_container)
                wrapper.setContentsMargins(10, 10, 10, 10)
                wrapper.setSpacing(6)
                self.global_audio_widget = GlobalAudioWidget(controller, loc or self.loc, self.audio_container)
                wrapper.addWidget(self.global_audio_widget)
                self.audio_container.hide()
            except Exception as e:
                print("attach_global_audio_widget init error:", e)
                self.audio_container = None
                return
        self.global_audio_widget.apply_theme_icons(self.settings)

    def _toggle_global_audio_widget(self):
        if self.audio_container is None:
            if self._global_audio_controller is None: return
            self.attach_global_audio_widget(self._global_audio_controller, self.loc)
            if self.audio_container is None: return
        
        if self.audio_container.isVisible():
            self.audio_container.hide()
            if self._audio_overlay: self._audio_overlay.hide()
        else:
            if not self._audio_overlay:
                self._audio_overlay = QWidget(self)
                self._audio_overlay.setObjectName("audioOverlay")
                self._audio_overlay.setStyleSheet("background: transparent;")
                self._audio_overlay.mousePressEvent = self._audio_overlay_clicked
            
            self._audio_overlay.setGeometry(self.rect())
            self._audio_overlay.show()
            
            self.audio_container.setParent(self)
            self.audio_container.adjustSize()
            width = max(360, self.audio_container.width())
            self.audio_container.setFixedWidth(width)
            x = (self.width() - self.audio_container.width()) // 2
            y = (self.height() - self.audio_container.height()) // 2
            self.audio_container.move(max(0, x), max(0, y))
            self.audio_container.show()
            self.audio_container.raise_()

    def _audio_overlay_clicked(self, event):
        if not self.audio_container.geometry().contains(event.pos()):
            self.audio_container.hide()
            self._audio_overlay.hide()

    def _update_styles(self):
        is_dark, accent, _, text_color, _ = theme_colors(self.settings)
        
        hp = self.width() * self.settings.get("zen_padding_horiz", 20) // 100
        vp = self.height() * self.settings.get("zen_padding_vert", 5) // 100
        
        if hasattr(self, 'editor_container'):
            self.editor_container.layout().setContentsMargins(hp, vp, hp, vp)
        
        opacity_level = self.settings.get("zen_editor_opacity", 85)
        font_family = self.settings.get("zen_font_family", "Georgia")
        font_size = self.settings.get("zen_font_size", 16)
        
        bg_key = "zen_dark_theme_bg" if is_dark else "light_theme_bg"
        editor_base_bg = QColor(self.settings.get(bg_key, "#000000"))
        editor_base_bg.setAlpha(int(opacity_level / 100 * 255))
        editor_bg_rgba = f"rgba({editor_base_bg.red()},{editor_base_bg.green()},{editor_base_bg.blue()},{editor_base_bg.alphaF()})"

        default_text_color = self.settings.get("dark_theme_text") if is_dark else self.settings.get("light_theme_text")
        editor_color = self.settings.get("zen_font_color") or default_text_color
        
        # --- НОВАЯ ЛОГИКА ОТСТУПОВ В ZEN ---
        padding_top = self.settings.get("editor_padding_top", 8)
        padding_bottom = self.settings.get("editor_padding_bottom", 8)
        padding_left = self.settings.get("editor_padding_left", 10)
        padding_right = self.settings.get("editor_padding_right", 10)
        
        # --- БОЛЕЕ КОНТРАСТНЫЕ ЦВЕТА ДЛЯ НИЖНЕЙ ПАНЕЛИ ---
        # Текст (белый для темной, черный для светлой)
        floating_fg = self.settings.get("dark_theme_text", "#e0e0e0") if is_dark else self.settings.get("light_theme_text", "#212529")
        # Фон компонентов (полупрозрачный)
        component_bg = "rgba(80, 80, 80, 0.5)" if is_dark else "rgba(240, 240, 240, 0.5)"
        hover_bg = "rgba(100, 100, 100, 0.7)" if is_dark else "rgba(220, 220, 220, 0.7)"
        # Границы (светлые для темной, темные для светлой)
        border_color = "rgba(255, 255, 255, 0.3)" if is_dark else "rgba(0, 0, 0, 0.3)"
        
        if self._overlay: self._overlay.setStyleSheet("background: transparent")

        self.editor_stack.setStyleSheet(f"""
            QTextEdit, QTextBrowser {{
                background-color: {editor_bg_rgba};
                border: 1px solid {border_color}; /* Возвращаем рамку */
                border-radius: 6px;
                font-family: "{font_family}";
                font-size: {font_size}pt; 
                color: {editor_color};
                padding: 0px;
            }}
        """)
        
        self.editor.setViewportMargins(padding_left, padding_top, padding_right, padding_bottom)
        self.previewer.setViewportMargins(padding_left, padding_top, padding_right, padding_bottom)


        self.bottom_panel.setStyleSheet(f"""
            QWidget#bottomPanel {{ 
                background-color: transparent; 
                border-top: 1px solid {border_color}; 
            }}                              
            QFrame#textContainer {{
                color: {floating_fg}; background-color: {component_bg};
                border: 1px solid {border_color}; padding: 5px 10px; border-radius: 4px;
            }}
            QWidget#bottomPanel QLabel {{ color: {floating_fg}; background-color: transparent; }}
            /* --- ОБНОВЛЕННЫЙ СТИЛЬ ДЛЯ ВСЕХ КНОПОК НА ПАНЕЛИ --- */
            QWidget#bottomPanel QPushButton {{
                color: {floating_fg}; background-color: {component_bg};
                border: 1px solid {border_color}; padding: 5px 10px; border-radius: 4px;
            }}
            QWidget#bottomPanel QPushButton:hover {{ 
                background-color: {hover_bg}; 
                border-color: {accent};
            }}
        """)
        
        if self.global_audio_widget:
            self.global_audio_widget.apply_zen_style(
                floating_fg=text_color, component_bg=component_bg,
                hover_bg=hover_bg, border_color=border_color, accent=accent
            )

        alignment = Qt.AlignmentFlag.AlignJustify if self.settings.get("zen_alignment") == "justify" else Qt.AlignmentFlag.AlignLeft
        
        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)

        block_format = cursor.blockFormat()
        
        block_format.setAlignment(alignment)
        
        cursor.mergeBlockFormat(block_format)
        
        cursor.clearSelection()
        self.editor.setTextCursor(cursor)
        
        button_bg = "transparent" # Было: "rgba(30,30,30,0.5)"
        button_hover_bg = "rgba(255,255,255,0.1)" if is_dark else "rgba(0,0,0,0.05)"

        self.settings_button.setStyleSheet(f"QPushButton {{ background:{button_bg}; border-radius:16px; border:none; }} QPushButton:hover {{ background-color:{button_hover_bg}; }}")
        self.exit_button.setStyleSheet(f"QPushButton {{ background:{button_bg}; border-radius:16px; border:none; }} QPushButton:hover {{ background-color:#dc3545; }}")

        self.settings_button.setIcon(ThemedIconProvider.icon("gear", self.settings, QSize(18, 18)))
        self.exit_button.setIcon(ThemedIconProvider.icon("close", self.settings, QSize(18, 18)))
        self.global_audio_btn.setIcon(ThemedIconProvider.icon("note", self.settings, QSize(18, 18)))
        self._update_preview_button_icon(self.preview_button.isChecked())
        
        if self.global_audio_widget:
            self.global_audio_widget.apply_theme_icons(self.settings) 


    def update_background_and_styles(self):
        bg_type = self.settings.get("zen_background_type", "procedural")
        is_dark = self.settings.get("theme") == "dark"

        if bg_type == "image":
            resolved_bg_path = resolve_path(self.settings.get("zen_bg_path"))
            if resolved_bg_path and os.path.exists(resolved_bg_path):
                safe_path = resolved_bg_path.replace('\\', '/')
                self.setStyleSheet(f"QWidget#ZenModeWindow {{ background-image: url({safe_path}); background-position: center; background-repeat: no-repeat; background-attachment: fixed; }}")
                self.background_widget.hide()
            else:
                bg_type = "procedural" 
        
        if bg_type == "procedural":
            self.setStyleSheet("QWidget#ZenModeWindow { background-color: black; }")
            self.background_widget.show()
            palette = {
                'sky_start': '#080c12' if is_dark else '#8ecae6',
                'sky_end': '#1c2541' if is_dark else '#ade8f4',
                'sun': '#b0c4de' if is_dark else '#ffb703',
                'sun_glow': 'rgba(176, 196, 222, 0.4)' if is_dark else '#fb8500',
                'mountains': ['#3a506b', '#2a3b4e', '#1a2a3e'] if is_dark else ['#219ebc', '#023047', '#0077b6']
            }
            self.background_widget.set_theme_palette(palette)

        elif bg_type == "color":
            self.background_widget.hide()
            bg_key = "zen_dark_theme_bg" if is_dark else "zen_light_theme_bg"
            bg_color = self.settings.get(bg_key, "#1c1c1c" if is_dark else "#e9ecef")
            self.setStyleSheet(f"QWidget#ZenModeWindow {{ background-color: {bg_color}; }}")

        self._update_styles()
        self.update()

    def update_zen_settings(self, new_settings):
        self.settings = new_settings
        self.update_background_and_styles()
        
    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)

    def resizeEvent(self, event):
        """Управляет размерами всех плавающих элементов."""
        super().resizeEvent(event)

        # Растягиваем фон и контейнер редактора на все окно
        if hasattr(self, 'background_widget'):
            self.background_widget.setGeometry(self.rect())
        if hasattr(self, 'editor_container'):
            self.editor_container.setGeometry(self.rect())

        # Позиционируем остальные плавающие элементы
        if hasattr(self, "exit_button") and self.exit_button:
            self.exit_button.move(self.width() - self.exit_button.width() - 20, 20)
            
        if self.audio_container and self.audio_container.isVisible():
            self.audio_container.adjustSize()
            x = (self.width() - self.audio_container.width()) // 2
            y = (self.height() - self.audio_container.height()) // 2
            self.audio_container.move(max(0, x), max(0, y))
            
        if self.settings_panel.isVisible():
            if self._overlay:
                self._overlay.setGeometry(self.rect())
            panel_size = self.settings_panel.sizeHint()
            x = (self.width() - panel_size.width()) // 2
            y = (self.height() - panel_size.height()) // 2
            self.settings_panel.move(x, y)

    def showEvent(self, event):
        self.update_background_and_styles()
        super().showEvent(event)
        
    def keyPressEvent(self, event):

        if event.key() == Qt.Key.Key_L and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.data_manager.lock_application()
            return

        if event.key() == Qt.Key.Key_F11:
            self.close()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.blockSignals(True)
            self.zen_saved_and_closed.emit(self.note_id, self.editor.toPlainText())
        else:
            super().keyPressEvent(event)
        
    def closeEvent(self, event):

        if self.data_manager.is_locking:
            event.accept()
            return


        self.data_manager.last_cursor_position = self.editor.textCursor().position()
        
        self.pomodoro_timer.stop()
        self.pomodoro_running = False
        
        if self.settings_panel.isVisible():
            self.settings_panel.hide()
        
        if not self.signalsBlocked():
            self.zen_exited.emit(self.note_id, self.editor.toPlainText())
            
        event.accept()

class MainPopup(QWidget, ThemedMenuMixin):
    animation_finished_and_hidden = pyqtSignal()

    def __init__(self, data_manager):
        super().__init__()
        self.setObjectName("MainPopup")
        self._is_closing = False
        self.preview_mode_active = False
        self.data_manager = data_manager
        self.loc = data_manager.loc_manager
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedWidth(380)
        self._overlay = None
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 5)
        main_layout.setSpacing(6)
        
        # --- ЗАГОЛОВОК И КНОПКИ УПРАВЛЕНИЯ (без изменений) ---
        title_bar_layout = QHBoxLayout()
        title_bar_layout.setSpacing(6)
        self.title_label = QLabel(self.loc.get("app_title_v3"))
        self.title_label.setObjectName("titleLabel")
        self.settings_toggle_btn = QPushButton()
        self.settings_toggle_btn.setFixedSize(40, 28)
        self.settings_toggle_btn.clicked.connect(self._toggle_settings_panel_main)
        self.close_button = QPushButton()
        self.close_button.setFixedSize(28, 28)
        self.close_button.setObjectName("close_button")
        self.close_button.clicked.connect(self.close)
        title_bar_layout.addWidget(self.title_label)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(self.settings_toggle_btn)
        title_bar_layout.addWidget(self.close_button)
        main_layout.addLayout(title_bar_layout)

        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("mainPopupTabWidget")
        
        work_tab = QWidget()
        work_layout = QVBoxLayout(work_tab)
        work_layout.setContentsMargins(0,0,0,0)
        
        self.tasks_panel = TasksPanel(data_manager, parent=self)
        self.notes_panel = NotesPanel(data_manager, parent=self)
        
        work_splitter = QSplitter(Qt.Orientation.Vertical)
        work_splitter.addWidget(self.tasks_panel)
        work_splitter.addWidget(self.notes_panel)

        splitter_sizes = self.data_manager.get_settings().get("popup_main_splitter_sizes", [250, 400])
        work_splitter.setSizes(splitter_sizes)
        work_splitter.splitterMoved.connect(self._save_main_splitter_sizes)
        
        work_layout.addWidget(work_splitter)
        
        self.audio_widget_container = QFrame()
        self.audio_widget_container.setObjectName("audioWidgetContainer")
        audio_layout = QVBoxLayout(self.audio_widget_container)
        audio_layout.setContentsMargins(8,8,8,8)
        self.audio_widget = GlobalAudioWidget(self.data_manager.global_audio, self.loc, self)
        audio_layout.addWidget(self.audio_widget)
        
        self.tab_widget.addTab(work_tab, "Работа")
        self.tab_widget.addTab(self.audio_widget_container, "Плеер")
        
        main_layout.addWidget(self.tab_widget, 1)
        
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(self.status_label)
        
        self.settings_panel_main = SettingsPanel(
            self.data_manager.get_settings(), self.loc, self.data_manager, self, context="main_popup"
        )
        self.settings_panel_main.settings_changed.connect(self.data_manager.update_settings)
        self.settings_panel_main.hide()
        self.settings_panel_main.installEventFilter(self)
        
        self.pos_animation = QPropertyAnimation(self, b"pos")
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation_group = QParallelAnimationGroup(self)
        self.animation_group.addAnimation(self.pos_animation)
        self.animation_group.addAnimation(self.opacity_animation)
        self.animation_group.finished.connect(self.on_animation_finished)
        self.set_status_saved()
        
        self.notes_panel.zen_mode_requested.connect(self._on_zen_mode_requested)
        
        self.notes_panel.dirty_state_changed.connect(self.on_data_changed)

        self._setup_shortcuts_popup()

        self.apply_theme(self.data_manager.get_settings())
        self.data_manager.load_data_into_ui(self)

    def _on_zen_mode_requested(self, note_id):
        """Перехватывает сигнал и вызывает data_manager с контекстом MainPopup."""
        self.data_manager.enter_zen_mode(note_id, source_window=self)

    def _toggle_top_panel(self, checked):
        self.toggle_top_button.setArrowType(Qt.ArrowType.UpArrow if checked else Qt.ArrowType.DownArrow)
        sizes = self.splitter.sizes()
        if not checked:
            self.splitter.setSizes([0, sizes[0] + sizes[1]])
        else: 
            self.splitter.setSizes([1, 1]) 

    def _toggle_bottom_panel(self, checked):
        self.toggle_bottom_button.setArrowType(Qt.ArrowType.UpArrow if checked else Qt.ArrowType.DownArrow)
        sizes = self.splitter.sizes()
        if not checked: 
            self.splitter.setSizes([sizes[0] + sizes[1], 0])
        else: 
            self.splitter.setSizes([1, 1])

    def _setup_shortcuts_popup(self):
        """Настраивает горячие клавиши для MainPopup."""
        QShortcut(QKeySequence("Ctrl+L"), self, self.data_manager.lock_application)
        QShortcut(QKeySequence("Ctrl+S"), self, self.notes_panel.save_current_note)
        QShortcut(QKeySequence("Ctrl+N"), self, lambda: self.notes_panel._create_new_item('note', None))
        
        # Shift+Enter обрабатывается через сигнал из NoteEditor
        self.notes_panel.notes_editor.save_and_new_requested.connect(self._handle_save_and_new_popup)
        
        # Горячие клавиши для плеера
        QShortcut(QKeySequence("Space"), self, activated=self._audio_toggle_play_pause)
        QShortcut(QKeySequence("Delete"), self, activated=self._audio_remove_selected)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._audio_add_files)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self, activated=self._audio_add_folder)
        QShortcut(QKeySequence("Ctrl+Left"), self, activated=self._audio_prev)
        QShortcut(QKeySequence("Ctrl+Right"), self, activated=self._audio_next)
        QShortcut(QKeySequence("M"), self, activated=lambda: self.audio_widget._toggle_mute())

    def _handle_save_and_new_popup(self):
        """Обрабатывает Shift+Enter в MainPopup."""
        self.notes_panel.save_current_note()
        
        parent_id = self.notes_panel.active_folder_id
        if not parent_id:
            try:
                saved_id = self.notes_panel.notes_editor.property("current_note_id")
                if saved_id:
                    parent_id = self.notes_panel.db.get_parent_id(saved_id)
            except RuntimeError:
                pass
        
        self.notes_panel.clear_for_new_note(force=True)
        self.notes_panel.notes_editor.setProperty("pending_parent_id", parent_id)
        self.notes_panel.notes_editor.setFocus()

    def eventFilter(self, obj, event):
        if obj is self.settings_panel_main and event.type() == QEvent.Type.Hide:
            if self._overlay and self._overlay.isVisible():
                self._overlay.hide()
        return super().eventFilter(obj, event)

    def _toggle_audio_view(self):
        self.tasks_audio_stack.setCurrentIndex(1 if self.tasks_audio_stack.currentIndex() == 0 else 0)

    def _toggle_settings_panel_main(self):
        if self.settings_panel_main.isVisible():
            self.settings_panel_main.hide()
            return

        if not self._overlay:
            self._overlay = QWidget(self.nativeParentWidget())
            self._overlay.setObjectName("settingsOverlay")
            self._overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
            self._overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self._overlay.setStyleSheet("background: rgba(0,0,0,0.5);")
            self._overlay.mousePressEvent = lambda event: self._overlay_clicked(event)

        screen_rect = self.screen().geometry()
        self._overlay.setGeometry(screen_rect)
        self._overlay.show()

        # Панель настроек делаем дочерней к оверлею, чтобы она была модальной для всего экрана
        self.settings_panel_main.setParent(self._overlay)
        panel_size = self.settings_panel_main.sizeHint()
        x = (screen_rect.width() - panel_size.width()) // 2
        y = (screen_rect.height() - panel_size.height()) // 2
        self.settings_panel_main.move(x, y)
        
        self.settings_panel_main.show()
        self.settings_panel_main.raise_()

    def _overlay_clicked(self, event):
        mapped_pos = self.settings_panel_main.mapFromGlobal(event.globalPosition().toPoint())
        if not self.settings_panel_main.rect().contains(mapped_pos):
            self.settings_panel_main.hide()
            self._overlay.hide()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Space"), self, activated=self._audio_toggle_play_pause)
        QShortcut(QKeySequence("Delete"), self, activated=self._audio_remove_selected)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._audio_add_files)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self, activated=self._audio_add_folder)
        QShortcut(QKeySequence("Ctrl+Left"), self, activated=self._audio_prev)
        QShortcut(QKeySequence("Ctrl+Right"), self, activated=self._audio_next)
        QShortcut(QKeySequence("M"), self, activated=lambda: self.audio_widget._toggle_mute())

    def _is_player_active(self):
        return hasattr(self, "tasks_audio_stack") and self.tasks_audio_stack.currentIndex() == 1

    def _audio_toggle_play_pause(self):
        if self._is_player_active(): self.data_manager.global_audio.toggle_play_pause()
    def _audio_prev(self):
        if self._is_player_active(): self.data_manager.global_audio.prev()
    def _audio_next(self):
        if self._is_player_active(): self.data_manager.global_audio.next()
    def _audio_add_files(self):
        if self._is_player_active(): self.audio_widget._add_files()
    def _audio_add_folder(self):
        if self._is_player_active(): self.audio_widget._add_folder()
    def _audio_remove_selected(self):
        if self._is_player_active(): self.audio_widget._remove_selected()

    def retranslate_ui(self):
        self.title_label.setText(self.loc.get("app_title_v3"))
        self.tasks_panel.retranslate_ui()
        self.notes_panel.retranslate_ui()
        
        self.tab_widget.setTabText(0, self.loc.get("main_popup_tab_work"))
        self.tab_widget.setTabText(1, self.loc.get("main_popup_tab_player"))
        
        self.settings_toggle_btn.setToolTip(self.loc.get("settings_title"))
        self.on_data_changed()
        self.set_status_saved()

    def apply_theme(self, settings):
        is_dark, accent, bg, text, list_text = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        panel_bg = QColor(comp_bg).lighter(108).name() if is_dark else QColor(comp_bg).lighter(103).name()
        border = "#555" if is_dark else "#ced4da"
        qtool_hover = "rgba(255,255,255,0.1)" if is_dark else "rgba(0,0,0,0.06)"

        selection_bg = "rgba(128,128,128,0.15)"
        
        scrollbar_style = get_scrollbar_style(settings)

        padding_top = settings.get("editor_padding_top", 8)
        padding_left = settings.get("editor_padding_left", 10)        

        stylesheet = f"""
            {scrollbar_style}
            QWidget#MainWindow, QWidget#MainPopup {{
                background-color: {bg};
            }}
            QWidget#settingsOverlay {{ background: rgba(0,0,0,0.5); }}
            QStatusBar {{
                background-color: {bg};
                border-top: 1px solid {border};
            }}
            QStatusBar::item {{ border: 0px; }}
            QWidget, QLabel {{ color:{text}; }}
            QWidget#cardContainer, QFrame#audioWidgetContainer {{
                background-color:{panel_bg}; border:1px solid {border}; border-radius:8px;
            }}
            QLabel#contextLabel {{ color:{accent}; font-weight:bold; padding-left: 2px; }}
            QFrame#audioWidgetContainer {{ background-color:{panel_bg}; border:none; border-radius:8px; }}
            QLabel#titleLabel{{font-size:14px;font-weight:bold;}}
            
            /* --- НОВЫЕ СТИЛИ ДЛЯ QTabWidget --- */
            QTabWidget#mainPopupTabWidget::pane {{
                border-top: 1px solid {border};
            }}
            QTabBar::tab {{
                background: transparent;
                border: none;
                padding: 8px 15px;
                color: {text};
                font-weight: bold;
                opacity: 0.7;
            }}
            QTabBar::tab:hover {{
                background-color: {qtool_hover};
            }}
            QTabBar::tab:selected {{
                color: {accent};
                border-bottom: 2px solid {accent};
                opacity: 1.0;
            }}
            QComboBox QAbstractItemView{{
                background-color:{comp_bg}; color:{text}; border:1px solid {border};
                selection-background-color:{accent}; selection-color:white; outline:0px;
            }}
            QLineEdit, QTextEdit, QComboBox, QTextBrowser {{
                background-color:{comp_bg}; border:1px solid {border};
                border-radius:6px; padding:6px;
            }}
            QTextBrowser {{
                font-family: "{settings.get('zen_font_family', 'sans-serif')}";
                font-size: {settings.get('popup_editor_font_size', 12)}pt;
                color: {text};
                }}
            QTextEdit[placeholderText] {{
                padding-top: {padding_top}px;
                padding-left: {padding_left}px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {comp_bg};
                border: 1px solid {border};
                selection-background-color: {accent};
            }}
            QTreeWidget, QListWidget {{
                background-color:{comp_bg}; border:1px solid {border}; border-radius:6px;
            }} 
            QTreeWidget:focus, QListWidget:focus {{ outline:none; }}
            
            QTreeWidget::item, QListWidget::item {{
                color:{list_text}; padding:6px; border-radius:4px;
                border: 1px solid transparent; 
            }}
            QTreeWidget::item:hover, QListWidget::item:hover {{
                background-color: {selection_bg};
            }}
            QTreeWidget::item:selected, QListWidget::item:selected {{
                background-color: {selection_bg};
            }}
            
            QCheckBox{{ spacing:8px; color:{text}; }}
            QCheckBox::indicator{{
                width:16px; height:16px; border:2px solid {'#888' if is_dark else '#adb5bd'};
                border-radius:3px; background:{'#2d2d2d' if is_dark else '#ffffff'};
            }}
            QCheckBox::indicator:hover{{ border-color:{accent}; }}
            QCheckBox::indicator:checked{{ border-color:{accent}; background:{accent}; }}
            
            QListWidget#TaskList::indicator {{
                width: 16px; height: 16px;
                border: 2px solid {'#888' if is_dark else '#adb5bd'};
                border-radius: 3px; background: transparent;
            }}
            QListWidget#TaskList::indicator:hover {{ border-color: {accent}; }}
            QListWidget#TaskList::indicator:checked {{ background-color: {accent}; border-color: {accent}; }}

            QPushButton {{
                background-color:{comp_bg}; color:{text}; border:1px solid {border};
                border-radius:4px; padding: 5px 10px;
            }}
            QToolButton {{
                background: transparent;
                border: none;
                padding: 2px;
                border-radius: 4px;
            }}
            QToolButton:hover {{
                background-color: {qtool_hover};
            }}

            QPushButton#close_button, QPushButton#window_button, QPushButton#settings_toggle_btn, QPushButton#audio_toggle_btn {{
                background-color:transparent; border:none;
            }}
            QPushButton#close_button, QPushButton#window_button, QPushButton#settings_toggle_btn, QPushButton#audio_toggle_btn {{
                background-color:transparent; border:none;
            }}
            
            /* Стили для кнопки предпросмотра */
            QPushButton:checkable {{
                background-color:{comp_bg};
            }}
            QPushButton:checkable:hover {{
                background-color: {qtool_hover};
            }}
            QPushButton:checkable:checked {{
                background-color: {accent};
                border-color: {accent};
            }}
            
            QSplitter::handle {{ background-color:transparent; }}
            QSplitter::handle:hover {{ background-color:rgba(128,128,128,0.15); }}

            QSlider::groove:horizontal {{
                background: {border};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {accent};
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider::sub-page:horizontal {{
                background: {accent};
                border-radius: 2px;
            }}
            QToolButton, QPushButton {{
                background-color:{comp_bg}; color:{text}; border:1px solid {border};
                border-radius:4px; padding: 5px 10px;
                spacing: 5px; /* Для кнопок с иконками */
            }}
            QToolButton:hover, QPushButton:hover {{
                background-color: {qtool_hover};
            }}

            QPushButton#close_button, QPushButton#settings_toggle_btn, QPushButton#audio_toggle_btn {{
                background-color:transparent; border:none;
            }}
            /* Добавляем WindowButton в исключения, если он QToolButton */
            QToolButton#window_button {{
                 background-color:transparent; border:none;
            }}
        """
        self.setStyleSheet(stylesheet)
        
        # --- УСТАНОВКА ИКОНОК ---
        self.settings_toggle_btn.setIcon(ThemedIconProvider.icon("gear", settings, QSize(18, 18)))
        self.close_button.setIcon(ThemedIconProvider.icon("close", settings, QSize(18, 18)))
        self.notes_panel.window_button.setIcon(ThemedIconProvider.icon("window", settings))
        self.notes_panel.preview_button.setIcon(ThemedIconProvider.icon("eye", settings)) # <--- ВОТ ОНА
        
        if hasattr(self, "audio_widget"):
            self.audio_widget.apply_theme_icons(settings)
        for i in range(self.tasks_panel.task_list_widget.count()):
            self.tasks_panel.update_task_item_style(self.tasks_panel.task_list_widget.item(i))

        popup_editor_settings = settings.copy()
        popup_editor_settings['window_editor_font_size'] = 0 # 0 означает "использовать размер по умолчанию"
        self.notes_panel.apply_editor_style(settings)

        if hasattr(self, "settings_panel_main"):
            self.settings_panel_main.apply_styles()

    def on_data_changed(self, is_dirty=None):
        """Обновляет статус сохранения."""
        if is_dirty is None:
            is_dirty = self.notes_panel.is_dirty

        if is_dirty:
            self.status_label.setText(self.loc.get("unsaved_changes_status"))
            self.status_label.setStyleSheet("color:#dc3545;font-size:10px;margin-right:5px;")
        else:
            self.set_status_saved()

    def set_status_saved(self):
        self.status_label.setText(self.loc.get("data_saved_status"))
        self.status_label.setStyleSheet("color:#28a745;font-size:10px;margin-right:5px;")

    def show_animated(self, position, from_left=False):
        if self.isVisible(): return
        screen_geo = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(position.x(), screen_geo.y(), 380, screen_geo.height())
        start_pos = QPoint(-self.width(), self.y()) if from_left else QPoint(screen_geo.width(), self.y())
        self.pos_animation.setDuration(300)
        self.pos_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.pos_animation.setStartValue(start_pos)
        self.pos_animation.setEndValue(self.pos())
        self.opacity_animation.setDuration(250)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.setWindowOpacity(0.0)
        self.move(start_pos)
        self.show()
        self.animation_group.start()

    def hide_animated(self, to_left=False):
        if not self.isVisible() or self._is_closing: return
        self._is_closing = True
        end_x = -self.width() if to_left else self.screen().geometry().width()
        end_pos = QPoint(end_x, self.y())
        self.pos_animation.setStartValue(self.pos())
        self.pos_animation.setEndValue(end_pos)
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)
        self.animation_group.start()

    def on_animation_finished(self):
        if self.windowOpacity() < 0.1:
            self.hide()
            self._is_closing = False
            self.animation_finished_and_hidden.emit()

    def close(self):
        self.hide_animated(to_left=self.data_manager.settings.get("trigger_pos") == "left")

    def closeEvent(self, event):

        if self.data_manager.is_locking:
            super().closeEvent(event)
            return

        """Сохраняет состояние при закрытии крестиком."""
        if not self.data_manager.is_switching_to_window:
            self.notes_panel.save_current_note()
            popup_state = self.data_manager.window_states['popup']
            current_item = self.notes_panel.tree_widget.currentItem()
            if current_item:
                popup_state['id'] = current_item.data(0, Qt.ItemDataRole.UserRole).get('id')
            else:
                popup_state['id'] = self.notes_panel.active_folder_id
            popup_state['cursor_pos'] = self.notes_panel.notes_editor.textCursor().position()
        
        super().closeEvent(event)

    def resizeEvent(self, event):
        if self._overlay and self._overlay.isVisible():
            self._overlay.resize(self.size())
            x = (self.width() - self.settings_panel_main.width()) // 2
            y = (self.height() - self.settings_panel_main.height()) // 2
            self.settings_panel_main.move(max(0, x), max(0, y))
        super().resizeEvent(event)

    def _save_main_splitter_sizes(self, pos, index):
        """Сохраняет размеры главного сплиттера в MainPopup."""
        sizes = self.tab_widget.widget(0).findChild(QSplitter).sizes()
        if all(s > 0 for s in sizes):
            settings = self.data_manager.get_settings()
            settings["popup_main_splitter_sizes"] = sizes
            self.data_manager.save_settings()

class NotesTreeWidget(QTreeWidget):
    dropped = pyqtSignal(QTreeWidgetItem, QTreeWidgetItem, QTreeWidgetItem)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setObjectName("NotesTree")
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(True)

    def _is_folder(self, item):
        if not item: return False
        nd = item.data(0, Qt.ItemDataRole.UserRole) or {}
        return nd.get("type") == "folder"

    def dragMoveEvent(self, event):
        pos = event.position().toPoint()
        item = self.itemAt(pos)
        drop_indicator_pos = self.dropIndicatorPosition()

        if drop_indicator_pos == QAbstractItemView.DropIndicatorPosition.OnItem:
            if not self._is_folder(item):
                event.ignore()
                return
        event.accept()

    def dropEvent(self, event):
        """Переопределяем стандартное событие, чтобы получить нужные данные."""
        moved_item = self.currentItem()
        if not moved_item:
            event.ignore()
            return
        
        old_parent = moved_item.parent() or self.invisibleRootItem()
        
        super().dropEvent(event)

        new_parent = moved_item.parent() or self.invisibleRootItem()
        self.dropped.emit(moved_item, old_parent, new_parent)

class SmartSplitter(QSplitter):
    """
    QSplitter, который автоматически сворачивает свои виджеты,
    если их размер становится меньше заданного порога.
    """
    panel_collapsed = pyqtSignal(int, bool) # index, is_collapsed

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)

        self.setChildrenCollapsible(True) 

    def set_collapse_threshold(self, index, threshold):
        """Устанавливает минимальный размер для виджета, после которого он сворачивается."""
        self.collapse_thresholds[index] = threshold

    def _check_collapse(self, pos, index):
        """Проверяет, не нужно ли свернуть/развернуть панель."""
        sizes = self.sizes()
        thresholds_met = [False] * len(sizes)
        
        for i, size in enumerate(sizes):
            threshold = self.collapse_thresholds.get(i)
            if threshold is not None:
                if 0 < size < threshold:
                    new_sizes = list(sizes)
                    new_sizes[i] = 0
                    self.setSizes(new_sizes)
                    self.panel_collapsed.emit(i, True)
                    return
                elif size == 0:
                    thresholds_met[i] = True
        
        if index > 0 and thresholds_met[index - 1]:
            self._expand_panel(index - 1)
        elif index < len(sizes) and thresholds_met[index]:
            self._expand_panel(index)

    def _expand_panel(self, index):
        """Разворачивает свернутую панель."""
        sizes = self.sizes()
        sizes[index] = self.collapse_thresholds.get(index, 150) # Восстанавливаем до порога
        self.setSizes(sizes)
        self.panel_collapsed.emit(index, False)
        
    def set_panel_visible(self, index, visible):
        """Программно сворачивает/разворачивает панель, используя setSizes."""
        sizes = self.sizes()
        # Проверяем, что действие необходимо
        is_currently_visible = sizes[index] > 10 # С допуском
        
        if visible and not is_currently_visible: # Разворачиваем
            # Восстанавливаем пропорции
            new_sizes = [1] * len(sizes)
            self.setSizes(new_sizes)
        elif not visible and is_currently_visible: # Сворачиваем
            # Устанавливаем размер в 0, а остальное пространство отдаем другому виджету
            other_index = 1 if index == 0 else 0
            total_size = sum(sizes)
            new_sizes = [0] * len(sizes)
            new_sizes[other_index] = total_size
            new_sizes[index] = 0
            self.setSizes(new_sizes)


class NotesTreeSidebar(QWidget):
    folder_selected = pyqtSignal(QTreeWidgetItem)
    note_selected = pyqtSignal(int)
    selection_cleared = pyqtSignal()
    note_deleted_from_tree = pyqtSignal(str) 
    
    def __init__(self, notes_panel: NotesPanel, loc_manager: LocalizationManager, main_window: 'WindowMain', parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.loc = loc_manager
        self.notes_panel = notes_panel
        self.db = main_window.data_manager.db
        self.pending_target_folder = None
        self._building = False
        self.active_folder_id = None
        self._item_creation_lock = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.tree = NotesTreeWidget(self)
        self.tree.setAllColumnsShowFocus(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._open_context_menu)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.dropped.connect(self._on_item_dropped)
        layout.addWidget(self.tree, 1)


    def load_tree_from_db(self):
        """Загружает и строит дерево из данных, полученных от DatabaseManager."""
        self._building = True
        try:
            self.tree.clear()
            tree_data = self.db.get_note_tree()
            self._populate_tree(self.tree.invisibleRootItem(), tree_data)
            self.tree.expandAll()
        finally:
            self._building = False

    def _populate_tree(self, parent_item, children_data):
        """Рекурсивно заполняет QTreeWidget данными из списка словарей."""
        settings = self.notes_panel.data_manager.get_settings()
        for node_data in children_data:
            title = node_data.get('title', self.loc.get("unnamed_note_title"))
            display_title = title[:30] + '...' if len(title) > 30 else title
            
            item = QTreeWidgetItem(parent_item, [display_title])
            
            item.setData(0, Qt.ItemDataRole.UserRole, dict(node_data))

            if node_data['type'] == 'folder':
                item.setIcon(0, ThemedIconProvider.icon("folder", settings))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsDragEnabled)
                if 'children' in node_data and node_data['children']:
                    self._populate_tree(item, node_data['children'])
            else: # note
                icon_name = "pin" if node_data.get('is_pinned') else "file"
                item.setIcon(0, ThemedIconProvider.icon(icon_name, settings))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsDragEnabled)

    def _append_node(self, parent_item, node_data):
        node_type = node_data.get("type")
        settings = self.notes_panel.data_manager.get_settings()
        if node_type == "folder":
            item = QTreeWidgetItem(parent_item, [node_data.get("name", "Folder")])
            item.setIcon(0, ThemedIconProvider.icon("folder", settings))
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "name": node_data.get("name", "")})
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsDragEnabled)
            if "children" in node_data:
                for child_node in node_data["children"]:
                    self._append_node(item, child_node)
        elif node_type == "note":
            ts = node_data.get("timestamp", "")
            alias = self._get_note_alias_from_cache(ts)
            item = QTreeWidgetItem(parent_item, [alias])
            item.setIcon(0, ThemedIconProvider.icon("file", settings))
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "note", "timestamp": ts})
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsDragEnabled)

    def refresh_aliases(self):
        """Обновляет заголовки и иконки (закреплено/не закреплено) в дереве."""
        ts_map = {}
        
        all_notes = self.db.get_all_notes_for_refresh()

        for note in all_notes:
            note_id = note.get("id")
            if note_id:
                title = note.get("title", "")
                pinned = note.get("pinned", False)

                display_title = title[:30] + '...' if len(title) > 30 else title
                ts_map[note_id] = (display_title, pinned) 
        
        settings = self.notes_panel.data_manager.get_settings()
        pin_icon = ThemedIconProvider.icon("pin", settings)
        file_icon = ThemedIconProvider.icon("file", settings)
        
        def apply(parent_item):
                for i in range(parent_item.childCount()):
                    ch = parent_item.child(i)
                    md = ch.data(0, Qt.ItemDataRole.UserRole) or {}
                    if md.get("type") == "note":
                        note_id = md.get("id")
                        if note_id and note_id in ts_map:
                            display_title, pinned = ts_map[note_id]
                            ch.setText(0, display_title)
                            ch.setIcon(0, pin_icon if pinned else file_icon)
                    else: # folder
                        ch.setIcon(0, ThemedIconProvider.icon("folder", settings))
                        apply(ch)
                        
        apply(self.tree.invisibleRootItem())

    def _create_themed_menu(self):
        if self.main_window and hasattr(self.main_window, '_create_themed_menu'):
            return self.main_window._create_themed_menu()
        return QMenu(self)

    def _open_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        menu = self._create_themed_menu()
        
        if item:
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            item_type = item_data.get('type')
            
            if item_type == 'folder':
                menu.addAction(self.loc.get("tree_new_note_here"), lambda: self._new_note_here(item))
                menu.addAction(self.loc.get("import_files_title"), lambda: self.main_window.data_manager.import_files_here(item))
                menu.addSeparator()
                # --- НОВЫЙ ЭКСПОРТ ---
                export_folder_menu = menu.addMenu(self.loc.get("export_note_title"))
                export_folder_menu.addAction(self.loc.get("in_one_file"), lambda: self.main_window.data_manager.export_notes(scope="folder", item=item))
                export_folder_menu.addAction(self.loc.get("as_a_folder"), lambda: self.main_window.data_manager.export_one_folder(item))
                # --- КОНЕЦ ---
                
                menu.addSeparator()
                menu.addAction(self.loc.get("tree_new_folder"), lambda: self._create_folder(item))
                menu.addAction(self.loc.get("tree_rename_folder"), lambda: self._rename_item(item))
                menu.addAction(self.loc.get("tree_delete_folder"), lambda: self._delete_item(item))
                
                if item.parent():
                    menu.addSeparator()
                    menu.addAction(self.loc.get("move_item_up_title"), lambda: self._move_item_up(item))
                    if item.parent().parent():
                         menu.addAction(self.loc.get("move_item_to_root_title"), lambda: self._move_item_to_root(item))
            else: # note
                menu.addAction(self.loc.get("export_note_title"), lambda: self.main_window.data_manager.export_notes(scope="note", item=item))
                menu.addSeparator()
                menu.addAction(self.loc.get("tree_delete_note"), lambda: self._delete_item(item))
                
                if item.parent():
                    menu.addSeparator()
                    menu.addAction(self.loc.get("move_item_up_title"), lambda: self._move_item_up(item))
                    if item.parent().parent():
                         menu.addAction(self.loc.get("move_item_to_root_title"), lambda: self._move_item_to_root(item))
        else:
            menu.addAction(self.loc.get("tree_new_note_here"), lambda: self._new_note_here(None))

            menu.addAction(self.loc.get("import_files_title"), lambda: self.main_window.data_manager.import_files_here(None))

            menu.addSeparator()
            menu.addAction(self.loc.get("tree_new_folder"), lambda: self._create_folder(None))
            
        menu.exec(self.tree.viewport().mapToGlobal(pos))
        
    def _move_item_up(self, item):
        if not item or not item.parent(): return
        current_parent = item.parent()
        new_parent = current_parent.parent() or self.tree.invisibleRootItem()
        new_parent.addChild(current_parent.takeChild(current_parent.indexOfChild(item)))
        self._save()

    def _move_item_to_root(self, item):
        if not item or not item.parent(): return
        root = self.tree.invisibleRootItem()
        current_parent = item.parent()
        root.addChild(current_parent.takeChild(current_parent.indexOfChild(item)))
        self._save()

    def _new_note_here(self, parent_folder_item):
        """Создает новую заметку внутри выбранной папки."""
        parent_id = parent_folder_item.data(0, Qt.ItemDataRole.UserRole).get('id') if parent_folder_item else None
        
        # --- ИСПОЛЬЗУЕМ ЗАМОК ---
        self._item_creation_lock = True
        try:
            new_note_id = self.db.create_note(parent_id)
            self.load_tree_from_db()
            self.select_item_by_id(new_note_id)
        finally:
            self._item_creation_lock = False
        # --- КОНЕЦ ---

    def clear_pending_folder(self):
        self.pending_target_folder = None

    def _create_folder(self, parent_item):
        """Создает новую папку."""
        name, ok = QInputDialog.getText(self, self.loc.get("tree_new_folder"), self.loc.get("tree_new_folder"))
        if not ok or not name.strip(): return
        
        parent_id = parent_item.data(0, Qt.ItemDataRole.UserRole).get('id') if parent_item else None
            
        # --- ИСПОЛЬЗУЕМ ЗАМОК ---
        self._item_creation_lock = True
        try:
            new_folder_id = self.db.create_folder(parent_id, name.strip())
            self.load_tree_from_db()
            self.select_item_by_id(new_folder_id)
        finally:
            self._item_creation_lock = False
        # --- КОНЕЦ ---

    def _rename_item(self, item):
        """Переименовывает и папку, и заметку."""
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        item_id = item_data.get('id')
        old_name = item_data.get('title', "")
        
        new_name, ok = QInputDialog.getText(self, "Переименовать", "Новое имя:", text=old_name)
        if not ok or not new_name.strip() or new_name.strip() == old_name:
            return

        # Для заметки обновляем и контент, так как title это часть контента
        if item_data.get('type') == 'note':
            note_details = self.db.get_note_details(item_id)
            self.db.update_note_content(item_id, new_name.strip(), note_details['content'])
        else: # Для папки просто обновляем title
            self.db.update_note_content(item_id, new_name.strip(), None)
        
        self.load_tree_from_db()
        self.select_item_by_id(item_id)

    def _delete_item(self, item):
        """Удаляет выбранный элемент."""
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        item_id = item_data.get('id')
        
        fresh_item_data = self.db.get_note_details(item_id) or item_data
        item_name = fresh_item_data.get('title', "")
        
        display_name = item_name[:50] + '...' if len(item_name) > 50 else item_name
        msg = f"Удалить '{display_name}'?"


        if item_data.get('type') == 'folder':
            msg += "\nВЕСЬ контент внутри папки будет удален!"
            
        reply = QMessageBox.question(self, "Подтверждение", msg)
        if reply != QMessageBox.StandardButton.Yes: return
        
        parent_id = None
        if item.parent():
            parent_id = item.parent().data(0, Qt.ItemDataRole.UserRole).get('id')
        
        if self.main_window.current_edit_target and self.main_window.current_edit_target[1] == item:
            self.main_window.current_edit_target = None
            self.main_window.notes_panel.clear_for_new_note(force=True)
        
        self.db.delete_note_or_folder(item_id)
        self.load_tree_from_db()

        if item_data.get('type') == 'note' and parent_id is not None:
            new_parent_item = self.select_item_by_id(parent_id)
            if new_parent_item:
                self.folder_selected.emit(new_parent_item)
        else:
             self.main_window.clear_editor()

    def select_item_by_id(self, item_id, select=True):
        """Находит и опционально выделяет элемент в дереве по его ID."""
        if not item_id: return None
        
        def find_item(parent):
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child.data(0, Qt.ItemDataRole.UserRole).get('id') == item_id:
                    return child
                found = find_item(child)
                if found:
                    return found
            return None

        item_to_select = find_item(self.tree.invisibleRootItem())
        if item_to_select and select:
            self.tree.setCurrentItem(item_to_select)
            self.tree.scrollToItem(item_to_select, QAbstractItemView.ScrollHint.PositionAtCenter)
        
        return item_to_select

    def _rename_folder(self, item):
        nd = item.data(0, Qt.ItemDataRole.UserRole) or {}
        old = nd.get("name", "")
        name, ok = QInputDialog.getText(self, self.loc.get("tree_rename_folder"), self.loc.get("tree_rename_folder"), QLineEdit.EchoMode.Normal, old)
        if not ok or not name.strip(): return
        nd["name"] = name.strip()
        item.setData(0, Qt.ItemDataRole.UserRole, nd)
        item.setText(0, name.strip())
        self._save()

    def _delete_folder(self, item):
        if not item: return
        nd = item.data(0, Qt.ItemDataRole.UserRole) or {}
        name = nd.get("name", "")
        reply = QMessageBox.question(self, self.loc.get("tree_delete_folder"), self.loc.get("tree_confirm_delete_folder").format(name=name))
        if reply != QMessageBox.StandardButton.Yes: return
        while item.childCount() > 0:
            child = item.child(0)
            if self.tree._is_folder(child): self._delete_folder(child)
            else: self._delete_note(child)
        parent = item.parent() or self.tree.invisibleRootItem()
        parent.removeChild(item)
        self._save()

    def _delete_note(self, item):
        if not item: return
        nd = item.data(0, Qt.ItemDataRole.UserRole) or {}
        ts = nd.get("timestamp")
        if not ts: return
        parent = item.parent() or self.tree.invisibleRootItem()
        parent.removeChild(item)
        self.note_deleted_from_tree.emit(ts)
        self.notes_panel.data_manager.delete_note_by_timestamp_from_all_data(ts)

    def _find_note_item(self, timestamp: str, parent_item=None):
        if not timestamp: return None
        if parent_item is None: parent_item = self.tree.invisibleRootItem()
        for i in range(parent_item.childCount()):
            it = parent_item.child(i)
            nd = it.data(0, Qt.ItemDataRole.UserRole) or {}
            if nd.get("type") == "note" and nd.get("timestamp") == timestamp: return it
            if nd.get("type") == "folder":
                if f := self._find_note_item(timestamp, it): return f
        return None

    def _on_selection_changed(self):
        if self._building or self._item_creation_lock:
            return
        
        self.main_window.save_current_item()
        
        items = self.tree.selectedItems()
        if not items:
            if self.main_window.current_edit_target is not None:
                 self.selection_cleared.emit()
            return
            
        it = items[0]
        if self.main_window.current_edit_target and self.main_window.current_edit_target[1] == it:
            return

        item_data = it.data(0, Qt.ItemDataRole.UserRole)
        
        if item_data.get("type") == "note":
            self.note_selected.emit(item_data.get('id')) # <-- ИСПУСКАЕМ ID
        elif item_data.get("type") == "folder":
            self._set_active_folder(it)
            self.folder_selected.emit(it)

    def apply_visibility(self, visible_timestamps: set):
        def is_visible_recursive(item):
            nd = item.data(0, Qt.ItemDataRole.UserRole) or {}
            if nd.get("type") == "note":
                is_vis = nd.get("timestamp") in visible_timestamps
                item.setHidden(not is_vis)
                return is_vis
            any_child_visible = False
            for i in range(item.childCount()):
                if is_visible_recursive(item.child(i)):
                    any_child_visible = True
            item.setHidden(not any_child_visible)
            return any_child_visible
        is_visible_recursive(self.tree.invisibleRootItem())
    
    def on_note_created(self, timestamp: str):
        if self._building or not timestamp: return
        parent_item = self.pending_target_folder or self.tree.invisibleRootItem()
        self.clear_pending_folder()
        if self._find_note_item(timestamp):
            self.refresh_aliases()
            return
        self._append_node(parent_item, {"type": "note", "timestamp": timestamp})
        self.tree.expandItem(parent_item)
        if new_item := self._find_note_item(timestamp, parent_item):
            self.tree.setCurrentItem(new_item)
        self.refresh_aliases()

    def on_note_deleted(self, timestamp: str):
        if self._building or not timestamp: return
        if item_to_delete := self._find_note_item(timestamp):
            parent = item_to_delete.parent() or self.tree.invisibleRootItem()
            parent.removeChild(item_to_delete)

    def _set_active_folder(self, folder_item):
        """Устанавливает и подсвечивает активную папку по ее ID."""
        # Сначала находим старый активный элемент по ID и снимаем подсветку
        if self.active_folder_id:
            old_item = self.select_item_by_id(self.active_folder_id, select=False)
            if old_item:
                font = old_item.font(0)
                font.setBold(False)
                old_item.setFont(0, font)

        # Устанавливаем и подсвечиваем новый
        if folder_item:
            self.active_folder_id = folder_item.data(0, Qt.ItemDataRole.UserRole).get('id')
            font = folder_item.font(0)
            font.setBold(True)
            folder_item.setFont(0, font)
        else:
            self.active_folder_id = None

    def _move_item_up(self, item):
        if not item or not item.parent(): return
        item_id = item.data(0, Qt.ItemDataRole.UserRole).get('id')
        grandparent_item = item.parent().parent()
        new_parent_id = grandparent_item.data(0, Qt.ItemDataRole.UserRole).get('id') if grandparent_item else None
        self.db.move_item(item_id, new_parent_id)
        self.load_tree_from_db()
        self.select_item_by_id(item_id)

    def _move_item_to_root(self, item):
        if not item or not item.parent(): return
        item_id = item.data(0, Qt.ItemDataRole.UserRole).get('id')
        self.db.move_item(item_id, None)
        self.load_tree_from_db()
        self.select_item_by_id(item_id)

    def _on_item_dropped(self, moved_item, old_parent, new_parent):
        """Вызывается после того, как пользователь перетащил элемент."""
        if not moved_item:
            return

        moved_item_data = moved_item.data(0, Qt.ItemDataRole.UserRole)
        moved_id = moved_item_data.get('id')

        new_parent_id = None
        if new_parent and new_parent != self.tree.invisibleRootItem():
            new_parent_id = new_parent.data(0, Qt.ItemDataRole.UserRole).get('id')

        self.db.update_item_parent_and_order(moved_id, new_parent_id, [])

        self._item_creation_lock = True
        try:
            self.load_tree_from_db()
            self.select_item_by_id(moved_id)
        finally:
            self._item_creation_lock = False

    def _move_item_up(self, item):
        """Перемещает элемент на один уровень вверх в иерархии."""
        if not item or not item.parent(): return
        item_id = item.data(0, Qt.ItemDataRole.UserRole).get('id')
        grandparent_item = item.parent().parent()
        new_parent_id = grandparent_item.data(0, Qt.ItemDataRole.UserRole).get('id') if grandparent_item else None
        
        self.db.move_item(item_id, new_parent_id)
        
        self.load_tree_from_db()
        self.select_item_by_id(item_id)

    def _move_item_to_root(self, item):
        """Перемещает элемент в корень."""
        if not item or not item.parent(): return
        item_id = item.data(0, Qt.ItemDataRole.UserRole).get('id')
        
        self.db.move_item(item_id, None)
        
        self.load_tree_from_db()
        self.select_item_by_id(item_id)

    def _flatten_children(self, node):
        """Рекурсивно собирает все дочерние заметки папки."""
        notes = []
        if 'children' in node:
            for child in node['children']:
                if child['type'] == 'note':
                    notes.append(child)
                else:
                    notes.extend(self._flatten_children(child))
        return notes

class WindowMain(QWidget, ThemedMenuMixin):
    window_closed = pyqtSignal()
    splitter_sizes_changed = pyqtSignal(list)

    def __init__(self, data_manager):
        super().__init__()
        self.setObjectName("MainWindow")
        self.setWindowFlags(Qt.WindowType.Window)
        
        self._overlay = None

        self.data_manager = data_manager
        self.loc = data_manager.loc_manager
        self.current_edit_target = None
        self._save_lock = False
        self._first_show = True
        self.preview_mode_active = False
        
        self.setWindowTitle(self.loc.get("app_title_v3"))

        self.datetime_timer = QTimer(self)
        self.datetime_timer.setInterval(1000)
        self.datetime_timer.timeout.connect(self._update_datetime_chips)
        
        min_left = self.data_manager.get_settings().get("window_min_width_left", 260)
        min_right = self.data_manager.get_settings().get("window_min_width_right", 380)
        self.setMinimumSize(min_left + min_right + 260, 700)
        self.resize(1200, 860)
        
        self.v_splitter_save_timer = QTimer(self)
        self.v_splitter_save_timer.setSingleShot(True)
        self.v_splitter_save_timer.setInterval(500)
        self.v_splitter_save_timer.timeout.connect(self._save_v_splitter_sizes)

        self.h_splitter_save_timer = QTimer(self)
        self.h_splitter_save_timer.setSingleShot(True)
        self.h_splitter_save_timer.setInterval(500)
        self.h_splitter_save_timer.timeout.connect(self._save_h_splitter_sizes)
        
        self.window_editor_font_size = self.data_manager.get_settings().get("window_editor_font_size", 0)
        
        container_layout = QVBoxLayout(self)
        container_layout.setContentsMargins(12, 12, 12, 10)
        container_layout.setSpacing(10)
        
        self.notes_panel = NotesPanel(data_manager, self)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(8)
        
        self.new_button = QToolButton()
        self.save_button = QToolButton()
        self.zen_button = QToolButton()
        self.to_task_btn = QPushButton()
        self.preview_button = QPushButton()
        self.preview_button.setCheckable(True)

        self.datetime_chip = QPushButton()
        self.datetime_chip.setObjectName("chipButton")
        self.time_chip = QPushButton()
        self.time_chip.setObjectName("chipButton")
        
        for btn in [self.save_button, self.new_button, self.zen_button]:
             if isinstance(btn, QToolButton):
                btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        toolbar_layout.addWidget(self.new_button)
        toolbar_layout.addWidget(self.save_button)
        toolbar_layout.addWidget(self.zen_button)
        toolbar_layout.addWidget(self.preview_button)
        toolbar_layout.addWidget(self.to_task_btn)
        toolbar_layout.addWidget(self.datetime_chip)
        toolbar_layout.addWidget(self.time_chip)
        
        toolbar_layout.addStretch()
        
        self.editor_context_label = QLabel()
        self.editor_context_label.setObjectName("contextLabel")
        toolbar_layout.addWidget(self.editor_context_label)
        
        toolbar_layout.addStretch()
        
        self.audio_toggle_btn = QToolButton()
        self.settings_toggle_btn = QToolButton()
        self.to_panel_button = QToolButton()
        self.to_panel_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toolbar_layout.addWidget(self.audio_toggle_btn)
        toolbar_layout.addWidget(self.settings_toggle_btn)
        toolbar_layout.addWidget(self.to_panel_button)
        
        container_layout.addLayout(toolbar_layout)

        self.tasks_panel = TasksPanel(data_manager, self)
        self.editor_stack = self.notes_panel.editor_stack

        self.left_container = QWidget()
        self.left_container.setObjectName("cardContainer")
        self.left_container.setMinimumWidth(min_left)
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(6)
        
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.notes_panel.search_input, 1)
        filter_layout.addWidget(self.notes_panel.tag_filter_combo)
        left_layout.addLayout(filter_layout)
        
        self.tree_sidebar = NotesTreeSidebar(self.notes_panel, self.loc, self, self)
        left_layout.addWidget(self.tree_sidebar, 1)

        self.center_container = QWidget()
        self.center_container.setObjectName("cardContainer")
        self.center_container.setMinimumWidth(260)
        center_layout = QVBoxLayout(self.center_container)
        center_layout.setContentsMargins(10, 10, 10, 10)
        center_layout.addWidget(self.editor_stack, 1)
        
        self.right_container = QWidget()
        self.right_container.setObjectName("cardContainer")
        self.right_container.setMinimumWidth(min_right)
        right_v = QVBoxLayout(self.right_container)
        right_v.setContentsMargins(10, 10, 10, 10)
        right_v.setSpacing(6)
        self.audio_widget_container = QFrame()
        self.audio_widget_container.setObjectName("audioWidgetContainer")
        audio_layout = QVBoxLayout(self.audio_widget_container)
        audio_layout.setContentsMargins(8,8,8,8)
        self.audio_widget = GlobalAudioWidget(self.data_manager.global_audio, self.loc, self)
        audio_layout.addWidget(self.audio_widget)
        self.right_stack = QStackedWidget()
        self.right_stack.addWidget(self.tasks_panel)
        self.right_stack.addWidget(self.audio_widget_container)
        right_v.addWidget(self.right_stack, 1)
        
        self.h_splitter = SmartSplitter(Qt.Orientation.Horizontal, self)
        self.h_splitter.addWidget(self.left_container)
        self.h_splitter.addWidget(self.center_container)

        self.v_splitter = SmartSplitter(Qt.Orientation.Horizontal, self)
        self.v_splitter.addWidget(self.h_splitter)
        self.v_splitter.addWidget(self.right_container)
        
        self.h_splitter.setHandleWidth(12)
        self.h_splitter.setOpaqueResize(False)
        self.v_splitter.setHandleWidth(12)
        self.v_splitter.setOpaqueResize(False)
        
        self.v_splitter.splitterMoved.connect(self.v_splitter_save_timer.start)
        self.h_splitter.splitterMoved.connect(self.h_splitter_save_timer.start)
        
        container_layout.addWidget(self.v_splitter, 1)
        
        self.resize_overlay = QFrame(self.v_splitter)
        self.resize_overlay.setObjectName("resizeOverlay")
        overlay_layout = QVBoxLayout(self.resize_overlay)
        overlay_label = QLabel("Пересчет макета...")
        overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        overlay_layout.addWidget(overlay_label)
        self.resize_overlay.hide()
        
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.setInterval(250)
        self.resize_timer.timeout.connect(self._on_resize_finished)

        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(True)
        self.status_bar.setStyleSheet("QStatusBar { min-height: 22px; max-height: 22px; }")
        self.status_text = QLabel("")
        self.word_count_label = QLabel("")
        self.status_bar.addWidget(self.status_text, 1)
        self.status_bar.addPermanentWidget(self.word_count_label)
        
        container_layout.addWidget(self.status_bar)
        
        self.settings_panel_main = SettingsPanel(
            self.data_manager.get_settings(), 
            self.loc, 
            self.data_manager,
            self, 
            context="window_main"
        )
        self.settings_panel_main.settings_changed.connect(self.data_manager.update_settings)
        self.settings_panel_main.hide()
        self.settings_panel_main.installEventFilter(self)
        
        self._setup_shortcuts()
        self.notes_panel.notes_editor.textChanged.connect(self.on_data_changed)
        
        self.audio_toggle_btn.clicked.connect(self._toggle_audio_view)
        self.settings_toggle_btn.clicked.connect(self._toggle_settings_panel_main)
        self.to_panel_button.clicked.connect(self.data_manager.switch_to_popup_from_window)
        
        self.new_button.clicked.connect(self.clear_editor)
        self.save_button.clicked.connect(self.save_current_item)
        self.zen_button.clicked.connect(self._enter_zen_mode_from_window)
        self.notes_panel.zen_mode_requested.connect(self._on_zen_mode_requested)
        
        self.to_task_btn.clicked.connect(self._add_selection_as_task)
        self.preview_button.toggled.connect(self.toggle_preview_mode)
        
        self.notes_panel.notes_editor.textChanged.connect(self._update_to_task_btn_state)
        self.notes_panel.notes_editor.cursorPositionChanged.connect(self._update_to_task_btn_state)
        
        self.notes_panel.search_input.textChanged.connect(self._apply_filter)
        self.notes_panel.tag_filter_combo.currentIndexChanged.connect(self._apply_filter)
        self.tree_sidebar.folder_selected.connect(self.edit_folder_description)
        self.tree_sidebar.note_selected.connect(self.edit_note)
        self.tree_sidebar.selection_cleared.connect(self.clear_editor)
        
        self.datetime_chip.clicked.connect(self._insert_date_chip_text)
        self.time_chip.clicked.connect(self._insert_datetime_chip_text)
        
        self._update_to_task_btn_state()
        self.data_manager.load_data_into_ui(self)
        
        self.retranslate_ui()
        self.apply_theme(self.data_manager.get_settings())
        self._restore_window_state_or_set_ratio()
        self._apply_left_right_visibility()
        self._update_word_count()
        self.clear_editor()
        self._align_toolbar_buttons()

        self.datetime_timer.start()

    def resizeEvent(self, event):
        """Показывает оверлей при изменении размера окна."""
        super().resizeEvent(event)
        
        if not hasattr(self, '_is_resizing'): self._is_resizing = False # На всякий случай

        if not self._is_resizing:
            self._is_resizing = True
            self.resize_overlay.setGeometry(self.v_splitter.geometry())
            self.resize_overlay.show()
            self.resize_overlay.raise_()
        
        # Перезапускаем таймер при каждом движении
        self.resize_timer.start()

    def _on_resize_finished(self):
        """Скрывает оверлей, когда изменение размера завершено."""
        self.resize_overlay.hide()
        self._check_adaptive_layout() 
        self._is_resizing = False


    def _check_adaptive_layout(self):
        try:
            st = self.data_manager.get_settings()
            min_left = st.get("window_min_width_left", 260)
            min_right = st.get("window_min_width_right", 380)
            min_center = st.get("window_min_width_center", 400)
            
            current_width = self.width()
            
            # 1. Определяем, какие панели ДОЛЖНЫ быть видимы, исходя из ширины
            should_right_be_visible = current_width >= min_left + min_center + min_right
            should_left_be_visible = current_width >= (min_right if should_right_be_visible else 0) + min_center + min_left

            # 2. Получаем текущую видимость
            left_is_visible = self.h_splitter.sizes()[0] > 10
            right_is_visible = self.v_splitter.sizes()[1] > 10
            
            # 3. Применяем изменения, если они нужны
            if left_is_visible != should_left_be_visible:
                self.h_splitter.set_panel_visible(0, should_left_be_visible)
            
            if right_is_visible != should_right_be_visible:
                self.v_splitter.set_panel_visible(1, should_right_be_visible)

            # 4. После сворачивания/разворачивания, восстанавливаем пропорции
            # Это перераспределит пространство правильно.
            QTimer.singleShot(0, self._restore_splitter_sizes)

        except (RuntimeError, IndexError):
            pass

    def _update_datetime_chips(self):
        """Обновляет текст на чипсах с датой и временем."""
        now = QDateTime.currentDateTime()
        current_date = now.date()
        
        day_index = current_date.dayOfWeek() 
        day_name = self.loc.get(f"day_{day_index}", current_date.toString('dddd'))

        # --- НОВЫЕ ФОРМАТЫ ТЕКСТА ---
        # Формат 1: День недели, дата
        date_str = day_name.capitalize() + now.toString(', dd.MM.yyyy')
        self.datetime_chip.setText(date_str)
        
        # Формат 2: Дата и время
        datetime_str = now.toString('dd.MM.yyyy HH:mm:ss')
        self.time_chip.setText(datetime_str)

    def _insert_date_chip_text(self):
        """Вставляет текст из чипса 'день недели, дата' в редактор."""
        text_to_insert = self.datetime_chip.text()
        self._insert_text_into_editor(text_to_insert)

    def _insert_datetime_chip_text(self):
        """Вставляет текст из чипса 'дата и время' в редактор."""
        text_to_insert = self.time_chip.text()
        self._insert_text_into_editor(text_to_insert)

       
        self._update_datetime_chips() # Обновляем дату и время
        
        all_tags = self.data_manager.db.get_all_tags()
        
        if all_tags:
            label = QLabel(self.loc.get("tags_label"))
            self.chips_layout.insertWidget(2, label)
        
        for tag in all_tags[:30]:
            chip_widget = QFrame()
            chip_widget.setObjectName("chipWidget")
            chip_layout = QHBoxLayout(chip_widget)
            chip_layout.setContentsMargins(5, 0, 0, 0)
            chip_layout.setSpacing(3)

            tag_btn = QPushButton(f"#{tag}")
            tag_btn.setObjectName("chipButton")
            tag_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            tag_btn.clicked.connect(lambda _, t=tag: self._insert_tag_into_editor(t))
            
            del_btn = QToolButton()
            del_btn.setText("×")
            del_btn.setObjectName("chipDeleteButton")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda _, t=tag: self._delete_tag(t))

            chip_layout.addWidget(tag_btn)
            chip_layout.addWidget(del_btn)
            

    def _insert_text_into_editor(self, text):
        """Вспомогательный метод для вставки текста в текущую позицию курсора."""
        editor = self.notes_panel.notes_editor
        cursor = editor.textCursor()
        cursor.insertText(text + " ")
        editor.setFocus()
        self.set_status_saved()


    def showEvent(self, event):
        """Вызывается при первом показе окна."""
        super().showEvent(event)
        if self._first_show:
            self._restore_splitter_sizes()

            self._apply_left_right_visibility()
            self._first_show = False

    def _save_v_splitter_sizes(self):
        """Сохраняет пропорции главного сплиттера."""
        sizes = self.v_splitter.sizes()
        total = sum(sizes)
        if total > 0 and all(s >= 0 for s in sizes):
            proportions = [s / total for s in sizes]
            st = self.data_manager.get_settings()
            st["window_v_splitter_proportions"] = proportions
            self.data_manager.save_settings()

    def _save_h_splitter_sizes(self):
        """Сохраняет пропорции вложенного сплиттера."""
        sizes = self.h_splitter.sizes()
        total = sum(sizes)
        if total > 0 and all(s >= 0 for s in sizes):
            proportions = [s / total for s in sizes]
            st = self.data_manager.get_settings()
            st["window_h_splitter_proportions"] = proportions
            self.data_manager.save_settings()

    def _restore_splitter_sizes(self):
        """Восстанавливает размеры сплиттеров на основе пропорций."""
        st = self.data_manager.get_settings()
        
        v_proportions = st.get("window_v_splitter_proportions", [0.7, 0.3])
        v_total_width = self.v_splitter.width()
        v_sizes = [int(p * v_total_width) for p in v_proportions]
        self.v_splitter.setSizes(v_sizes)

        h_proportions = st.get("window_h_splitter_proportions", [0.35, 0.65])
        h_total_width = self.h_splitter.width()
        h_sizes = [int(p * h_total_width) for p in h_proportions]
        self.h_splitter.setSizes(h_sizes)

    def _update_preview_button_icon(self, is_preview_mode):
        settings = self.data_manager.get_settings()
        icon_name = "edit_pencil" if is_preview_mode else "eye"
        self.preview_button.setIcon(ThemedIconProvider.icon(icon_name, settings))

    def toggle_preview_mode(self, checked):
        self.preview_mode_active = checked
        self._update_preview_button_icon(checked)
        
        if checked:
            settings = self.data_manager.get_settings()
            is_dark, _, bg, text_color, _ = theme_colors(settings)
            
            bg_color = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
            font_size = settings.get("window_editor_font_size", 0) or settings.get("zen_font_size", 12)
            font_family = settings.get("zen_font_family", "sans-serif")

            self.notes_panel.previewer.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: {bg_color};
                    color: {text_color};
                    font-family: "{font_family}";
                    font-size: {font_size}pt;
                    border: none;
                    padding: 8px;
                }}
            """)
            self.notes_panel.previewer.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.notes_panel.previewer.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

            text = self.notes_panel.notes_editor.toPlainText()
            escaped_text = escape_markdown_tags(text)
            html_body = markdown.markdown(escaped_text, extensions=['fenced_code', 'tables', 'nl2br'])
            style_head = generate_markdown_css(settings)
            
            doc = self.notes_panel.previewer.document()
            text_option = doc.defaultTextOption()
            alignment_str = settings.get("zen_alignment", "left")
            alignment = Qt.AlignmentFlag.AlignJustify if alignment_str == "justify" else Qt.AlignmentFlag.AlignLeft
            text_option.setAlignment(alignment)
            doc.setDefaultTextOption(text_option)
            doc.setDefaultStyleSheet(style_head)
            self.notes_panel.previewer.setHtml(html_body)

            self.notes_panel.editor_stack.setCurrentIndex(1)
        else:
            self.notes_panel.editor_stack.setCurrentIndex(0)
            self.notes_panel.notes_editor.setFocus()

    def edit_folder_description(self, item):
        self.save_current_item() 
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        self.notes_panel.display_folder_info(item_data)
        
        # Обновляем UI WindowMain
        self.editor_context_label.setText(f"<b>Папка:</b> {item_data.get('title', '')}")
        
        self.notes_panel.is_dirty = False
        self.set_status_saved()


        self.notes_panel.zen_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.to_task_btn.setEnabled(False)
        self.notes_panel.save_button.setEnabled(False)

    def edit_note(self, note_id):
        if not note_id: return
        
        current_item_in_tree = self.tree_sidebar.select_item_by_id(note_id)
        if not current_item_in_tree: return

        self.current_edit_target = ("note", current_item_in_tree)

        self.notes_panel.notes_editor.setReadOnly(False)
        self.notes_panel.zen_button.setEnabled(True)
        self.preview_button.setEnabled(True)
        self.notes_panel.save_button.setEnabled(True)
        
        note_details = self.data_manager.db.get_note_details(note_id)
        if note_details:
            content = note_details.get('content', '')
            self.notes_panel.notes_editor.blockSignals(True)
            self.notes_panel.notes_editor.setPlainText(content)
            self.notes_panel.notes_editor.blockSignals(False)
            
            # 1. Устанавливаем "чистый" флаг в дочерней панели
            self.notes_panel.is_dirty = False
            
            # 2. ЯВНО обновляем статус в родительском окне
            self.set_status_saved()

            # Установка курсора
            window_state = self.data_manager.window_states['window']
            if note_id == window_state.get('id'):
                cursor = self.notes_panel.notes_editor.textCursor()
                pos = min(window_state.get('cursor_pos', 0), len(content))
                cursor.setPosition(pos)
                self.notes_panel.notes_editor.setTextCursor(cursor)
            else:
                self.notes_panel.notes_editor.moveCursor(QTextCursor.MoveOperation.End)
            
            if self.preview_mode_active:
                self.preview_button.setChecked(True)
                self.toggle_preview_mode(True)
            else:
                self.preview_button.setChecked(False)
                self.notes_panel.editor_stack.setCurrentIndex(0)
                
        self.notes_panel.zen_button.setEnabled(True)
        self.editor_context_label.setText(f"<b>{self.loc.get('note_editing', 'Редактирование заметки')}</b>")
        self._update_to_task_btn_state()

    def clear_editor(self):
        self.save_current_item()
        self.current_edit_target = None
        
        self.tree_sidebar._set_active_folder(None)
        self.tree_sidebar.tree.clearSelection()
        
        self.notes_panel.notes_editor.setReadOnly(False)
        self.notes_panel.zen_button.setEnabled(True)
        self.preview_button.setEnabled(True)
        self.notes_panel.save_button.setEnabled(True)

        
        self.notes_panel.clear_for_new_note(force=True)
        
        self.notes_panel.is_dirty = False
        self.set_status_saved()
        self.notes_panel.notes_editor.setFocus()
        
        self.editor_context_label.setText(f"<b>{self.loc.get('new_note_title', self.loc.get("new_note_title"))}</b>")

    def save_current_item(self, force_save=False):
        """Сохраняет текущий элемент в WindowMain."""
        if self._save_lock: return None, None
        
        self._save_lock = True
        try:
            is_dirty = self.notes_panel.is_dirty
            content = self.notes_panel.notes_editor.toPlainText()
        except RuntimeError:
            self._save_lock = False
            return None, None

        # Проверяем, жив ли еще объект QTreeWidgetItem
        if self.current_edit_target:
            try:
                _ = self.current_edit_target[1].data(0, Qt.ItemDataRole.UserRole)
            except RuntimeError:
                self.current_edit_target = None

        if not is_dirty and not force_save:
            if self.current_edit_target and self.current_edit_target[0] == 'note':
                item_data = self.current_edit_target[1].data(0, Qt.ItemDataRole.UserRole)
                parent_id = self.data_manager.db.get_parent_id(item_data.get('id'))
                self._save_lock = False
                return item_data.get('id'), parent_id
            self._save_lock = False
            return None, None

        saved_item_id = None
        parent_id = None
        
        if self.current_edit_target and self.current_edit_target[0] == "note":

            _, item = self.current_edit_target
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            item_id = item_data.get('id')
            
            title = content.split('\n', 1)[0].strip() or self.loc.get("unnamed_note_title")
            self.data_manager.db.update_note_content(item_id, title, content)
            
            display_title = re.sub(r'#', '', title).strip()
            display_title = display_title[:30] + '...' if len(display_title) > 30 else display_title
            item.setText(0, display_title)
            
            saved_item_id = item_id
            parent_id = self.data_manager.db.get_parent_id(item_id)
            
        elif self.current_edit_target is None and content.strip():

            title = content.split('\n', 1)[0].strip() or self.loc.get("unnamed_note_title")
            parent_id = self.tree_sidebar.active_folder_id
            new_id = self.data_manager.db.create_note(parent_id, title, content)
            
            self.tree_sidebar.load_tree_from_db()
            new_item = self.tree_sidebar.select_item_by_id(new_id)
            if new_item:
                self.current_edit_target = ("note", new_item)
            saved_item_id = new_id
        
        self.notes_panel.is_dirty = False
        self.set_status_saved()
        
            
        self._save_lock = False
        return saved_item_id, parent_id

    def _toggle_audio_view(self):
        self.right_stack.setCurrentIndex(1 if self.right_stack.currentIndex() == 0 else 0)
    
    def _toggle_settings_panel_main(self):
        if self.settings_panel_main.isVisible():
            self.settings_panel_main.hide()
            if self._overlay:
                self._overlay.hide()
            return

        if not self._overlay:
            parent_widget = self.nativeParentWidget() or self
            self._overlay = QWidget(parent_widget)
            self._overlay.setObjectName("settingsOverlay")

            self._overlay.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
            self._overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self._overlay.setStyleSheet("background: rgba(0,0,0,0.5);")
            self._overlay.mousePressEvent = self._overlay_clicked

        # Позиционируем оверлей на весь экран, где находится главное окно
        screen_rect = self.screen().geometry()
        self._overlay.setGeometry(screen_rect)
        self._overlay.show()

        # Панель настроек делаем дочерней к оверлею
        self.settings_panel_main.setParent(self._overlay)
        panel_size = self.settings_panel_main.sizeHint()
        # Вычисляем центр экрана
        x = screen_rect.x() + (screen_rect.width() - panel_size.width()) // 2
        y = screen_rect.y() + (screen_rect.height() - panel_size.height()) // 2
        self.settings_panel_main.move(x, y)
        
        self.settings_panel_main.show()
        self.settings_panel_main.raise_()
        # --- КОНЕЦ ---

    def _overlay_clicked(self, event):
        """Закрывает панель настроек, если клик был не по ней."""
        self.settings_panel_main.hide()
        self._overlay.hide()

    def _overlay_clicked(self, event):
        """Закрывает панель настроек, если клик был не по ней."""
        # Клик по оверлею всегда скрывает и оверлей, и панель
        self.settings_panel_main.hide()
        self._overlay.hide()
        
    def eventFilter(self, obj, event):
        if obj is self.settings_panel_main and event.type() == QEvent.Type.Hide:
            if self._overlay and self._overlay.isVisible():
                self._overlay.hide()
        return super().eventFilter(obj, event)

    def load_note_tree(self, tree_data=None): # tree_data больше не нужен
        self.tree_sidebar.load_tree_from_db()


    def get_note_tree_data(self) -> list: return self.tree_sidebar.get_model()

    def _setup_shortcuts(self):
        """Настраивает горячие клавиши для WindowMain."""
        QShortcut(QKeySequence("Ctrl+L"), self, self.data_manager.lock_application)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_current_item)
        QShortcut(QKeySequence("Ctrl+N"), self, self.clear_editor)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: self.notes_panel.search_input.setFocus())
        QShortcut(QKeySequence("F11"), self, activated=self.toggle_fullscreen)
        
        # Масштабирование редактора
        QShortcut(QKeySequence("Ctrl++"), self, activated=lambda: self._zoom_editor(+1))
        QShortcut(QKeySequence("Ctrl+="), self, activated=lambda: self._zoom_editor(+1)) # Для удобства
        QShortcut(QKeySequence("Ctrl+-"), self, activated=lambda: self._zoom_editor(-1))
        QShortcut(QKeySequence("Ctrl+0"), self, activated=self._zoom_editor_reset)
        
        # Закрытие окна
        QShortcut(QKeySequence("Ctrl+W"), self, activated=self.close)
        
        # Горячие клавиши для плеера
        QShortcut(QKeySequence("Space"), self, activated=self._audio_toggle_play_pause)
        QShortcut(QKeySequence("Delete"), self, activated=self._audio_remove_selected)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._audio_add_files)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self, activated=self._audio_add_folder)
        QShortcut(QKeySequence("Ctrl+Left"), self, activated=self._audio_prev)
        QShortcut(QKeySequence("Ctrl+Right"), self, activated=self._audio_next)
        QShortcut(QKeySequence("M"), self, activated=self.audio_widget._toggle_mute)
    
    def _on_zen_mode_requested(self, note_id):
        """Перехватывает сигнал из NotesPanel и вызывает data_manager с нужным контекстом."""
        self.data_manager.enter_zen_mode(note_id, source_window=self)

    def _is_player_active(self):
        return hasattr(self, "right_stack") and self.right_stack.currentIndex() == 1

    def _audio_toggle_play_pause(self):
        if self._is_player_active(): self.data_manager.global_audio.toggle_play_pause()
    def _audio_prev(self):
        if self._is_player_active(): self.data_manager.global_audio.prev()
    def _audio_next(self):
        if self._is_player_active(): self.data_manager.global_audio.next()
    def _audio_add_files(self):
        if self._is_player_active(): self.audio_widget._add_files()
    def _audio_add_folder(self):
        if self._is_player_active(): self.audio_widget._add_folder()
    def _audio_remove_selected(self):
        if self._is_player_active(): self.audio_widget._remove_selected()

    def _restore_window_state_or_set_ratio(self, force_recalc=False):
        st = self.data_manager.get_settings()
        
        if not force_recalc and st.get("window_geometry"):
            try:
                self.restoreGeometry(QByteArray.fromHex(st["window_geometry"].encode("ascii")))
            except Exception:
                pass
        
        self._restore_splitter_sizes()

    def toggle_fullscreen(self):
        """Переключает полноэкранный режим."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _apply_left_right_visibility(self):
        st = self.data_manager.get_settings()
        lv = st.get("window_left_visible", True)
        rv = st.get("window_right_visible", True)
        
        self.h_splitter.widget(0).setVisible(lv)
        self.v_splitter.widget(1).setVisible(rv)
        
        
    def _ensure_nonzero_split_sizes(self):
        sizes = self.splitter.sizes()
        min_left = self.data_manager.get_settings().get("window_min_width_left", 260)
        min_right = self.data_manager.get_settings().get("window_min_width_right", 380)
        if self.left_container.isVisible() and sizes[0] < min_left: sizes[0] = min_left
        if self.center_container.isVisible() and sizes[1] < self.center_container.minimumWidth(): sizes[1] = self.center_container.minimumWidth()
        if self.right_container.isVisible() and sizes[2] < min_right: sizes[2] = min_right
        self.splitter.setSizes(sizes)
        
    def _add_selection_as_task(self):
        cursor = self.notes_panel.notes_editor.textCursor()
        text = cursor.selectedText().strip()
        if not text:
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            text = cursor.selectedText().strip()
        text = text.replace('\u2029', ' ').replace('\n', ' ').strip()
        if text:
            self.tasks_panel.add_task(text)
        
        
    def _insert_tag_into_editor(self, tag):
        ed = self.notes_panel.notes_editor
        cursor = ed.textCursor()
        cursor.insertText(f"#{tag} ")
        ed.setTextCursor(cursor)
        ed.setFocus()
        
    def _update_word_count(self):
        text = self.notes_panel.notes_editor.toPlainText().strip()
        words = len(text.split()) if text else 0
        self.word_count_label.setText(f"{self.loc.get('word_count_label')}: {words}")
        
    def _update_to_task_btn_state(self):
        cursor = self.notes_panel.notes_editor.textCursor()
        text = cursor.selectedText().strip()
        if not text:
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            text = cursor.selectedText().strip()
        self.to_task_btn.setEnabled(bool(text))
        self.save_current_item()
        
    def _sync_tree_filter(self):
        visible_ts = set()
        for i in range(self.notes_panel.note_list_widget.count()):
            it = self.notes_panel.note_list_widget.item(i)
            if not it.isHidden():
                if ts := (it.data(Qt.ItemDataRole.UserRole) or {}).get("timestamp"):
                    visible_ts.add(ts)
        self.tree_sidebar.apply_visibility(visible_ts)
        
    def retranslate_ui(self):
        self.tasks_panel.retranslate_ui()
        self.notes_panel.retranslate_ui()
        self.setWindowTitle(self.loc.get("app_title_v3"))
        

        self.new_button.setText(self.loc.get("new_note_button"))
        self.new_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        
        self.save_button.setText(self.loc.get("save_button"))
        self.save_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        
        self.zen_button.setText(self.loc.get("zen_button"))
        self.zen_button.setToolTip(self.loc.get("zen_button_tooltip"))
        
        self.to_panel_button.setText(self.loc.get("to_panel_button"))
        self.to_panel_button.setToolTip(self.loc.get("to_panel_tooltip"))
        
        self.audio_toggle_btn.setToolTip(self.loc.get("audio_toggle_tooltip"))
        self.settings_toggle_btn.setToolTip(self.loc.get("settings_title"))
        
        if hasattr(self, 'to_task_btn'):
            self.to_task_btn.setText(self.loc.get("to_task_btn"))
            self.to_task_btn.setToolTip(self.loc.get("to_task_tooltip"))
            
        self.set_status_saved()
        
        
    def apply_theme(self, settings):
        is_dark, accent, bg, text, list_text = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        panel_bg = QColor(comp_bg).lighter(108).name() if is_dark else QColor(comp_bg).lighter(103).name()
        border = "#555" if is_dark else "#ced4da"
        qtool_hover = "rgba(255,255,255,0.1)" if is_dark else "rgba(0,0,0,0.06)"
        
        scrollbar_style = get_scrollbar_style(settings)
        
        padding_top = settings.get("editor_padding_top", 8)
        padding_left = settings.get("editor_padding_left", 10)

        stylesheet = f"""
            {scrollbar_style}

            QMainWindow, QWidget {{
                background-color: {bg};
            }}
            
            QStatusBar {{
                background-color: {bg};
                border-top: 1px solid {border};
            }}
            QStatusBar::item {{
                border: 0px;
            }}
            
            QWidget, QLabel {{ color:{text}; }}
            QLabel#contextLabel {{ color:{accent}; font-weight:bold; padding-left: 2px; }}
            QWidget#cardContainer, QFrame#audioWidgetContainer {{
                background-color:{panel_bg}; border:1px solid {border}; border-radius:8px;
            }}
            QLineEdit, QTextEdit, QComboBox, QTextBrowser {{
                background-color:{comp_bg}; border:1px solid {border};
                border-radius:6px; padding:6px;
            }}
            /* --- ИСПРАВЛЕНИЕ ДЛЯ ВЫПАДАЮЩЕГО СПИСКА --- */
            QComboBox QAbstractItemView {{
                background-color: {comp_bg};
                border: 1px solid {border};
                selection-background-color: {accent};
            }}
            QTreeWidget, QListWidget {{
                background-color:{comp_bg}; border:1px solid {border};
                border-radius:6px;
            }}
            
            QTextEdit[placeholderText] {{
                padding-top: {padding_top}px;
                padding-left: {padding_left}px;
            }}
            QComboBox QAbstractItemView{{
                background-color:{comp_bg};color:{text};border:1px solid {border};
                selection-background-color:{accent};selection-color:white;outline:0px;
            }}
            
            QListWidget::item, QTreeWidget#NotesTree::item {{
                color:{list_text}; padding:6px; border-radius:4px;
                border: 1px solid transparent; 
            }}
            QListWidget::item:hover, QTreeWidget#NotesTree::item:hover {{
                background-color:rgba(128,128,128,0.15);
            }}
            QListWidget::item:selected, QTreeWidget#NotesTree::item:selected {{
                background-color:rgba(128,128,128,0.15); 
            }}

            QListWidget#TaskList::indicator {{
                width: 16px; height: 16px;
                border: 2px solid {'#888' if is_dark else '#adb5bd'};
                border-radius: 3px; background: transparent;
            }}
            QListWidget#TaskList::indicator:hover {{ border-color: {accent}; }}
            QListWidget#TaskList::indicator:checked {{ background-color: {accent}; border-color: {accent}; }}
            
            QToolButton, QPushButton#toPanelButton, QPushButton {{
                background-color:{comp_bg}; color:{text}; border:1px solid {border};
                border-radius:4px; padding: 5px 10px;
                spacing: 5px;
            }}
            QToolButton:hover, QPushButton:hover {{ background-color: {qtool_hover}; }}
            QToolButton:checked, QPushButton:checkable:checked {{ 
                background-color:{accent}; color:white; border-color:{accent}; 
            }}
            QToolButton, QPushButton {{
                background-color:{comp_bg}; color:{text}; border:1px solid {border};
                border-radius:4px; padding: 5px 10px;
                spacing: 5px;
            }}
            QToolButton:hover, QPushButton:hover {{ 
                background-color: {qtool_hover}; 
            }}
            QToolButton:checked, QPushButton:checkable:checked {{ 
                background-color:{accent}; color:white; border-color:{accent}; 
            }}
            QCheckBox{{ spacing:8px; color:{text}; }}
            QCheckBox::indicator{{
                width:16px; height:16px; border:2px solid {'#888' if is_dark else '#adb5bd'};
                border-radius:3px; background:{'#2d2d2d' if is_dark else '#ffffff'};
            }}
            QCheckBox::indicator:hover{{ border-color:{accent}; }}
            QCheckBox::indicator:checked{{ border-color:{accent}; background:{accent}; }}
            
            QSplitter::handle {{ background-color:transparent; }}
            QSplitter::handle:hover {{ background-color:rgba(128,128,128,0.15); }}
            QFrame#chipWidget {{
                border: 1px solid {border};
                border-radius: 11px; /* Более круглый */
                background-color: transparent;
                max-height: 22px; /* Фиксируем высоту */
            }}
            /* Кнопка с самим тегом */
            QPushButton#chipButton {{
                border: none;
                background: transparent;
                padding: 2px 2px 2px 8px; /* Отступ слева */
                color: {text};
                font-size: 9pt;
            }}
            QPushButton#chipButton:hover {{
                text-decoration: underline;
            }}QPushButton#chipButton {{
                 border: 1px solid {border};
                 border-radius: 4px; /* Делаем как обычные кнопки */
                 padding: 5px 10px;
                 background-color: transparent;
                 font-size: 9pt;
            }}
            QPushButton#chipButton:hover {{
                background-color: {qtool_hover};
            }}
            #windowControlButton, #windowCloseButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }}
            #windowControlButton:hover {{
                background-color: {qtool_hover};
            }}
            #windowCloseButton:hover {{
                background-color: #E81123;
            }}
            #nowPlayingLabel {{
                font-style: italic;
                color: {text};
                opacity: 0.8;
                padding: 0 10px;
                min-height: 2.5em;
            }}
            QSlider#volumeSlider::groove:horizontal {{
                height: 6px; border-radius: 3px; background: {border};
            }}
            QSlider#volumeSlider::handle:horizontal {{
                background: {text}; width: 12px;
                margin: -3px 0; border-radius: 6px;
            }}
            QFrame#tagsContainer {{ /* Рамка вокруг тегов */
                border: 1px solid {border};
                border-radius: 6px;
                margin-top: 5px;
            }}
            QFrame#chipWidget {{ /* Контейнер для тега с крестиком */
                border: 1px solid {border};
                border-radius: 11px;
                background-color: transparent;
                max-height: 22px;
            }}
        """

        self.setStyleSheet(stylesheet)
        self.audio_toggle_btn.setIcon(ThemedIconProvider.icon("note", settings))
        self.settings_toggle_btn.setIcon(ThemedIconProvider.icon("gear", settings))
        self.to_panel_button.setIcon(ThemedIconProvider.icon("chev_l", settings))
    
        self._update_preview_button_icon(self.preview_button.isChecked())
        if hasattr(self, "audio_widget"): self.audio_widget.apply_theme_icons(settings)
        
        
        stylesheet += f"""
            QSlider#volumeSlider::groove:horizontal {{
                height: 6px; border-radius: 3px; background: {border};
            }}
            QSlider#volumeSlider::handle:horizontal {{
                background: {text}; width: 12px;
                margin: -3px 0; border-radius: 6px;
            }}
        """
        
        self.setStyleSheet(stylesheet)

        if hasattr(self, "audio_widget"): self.audio_widget.apply_theme_icons(settings)
        
        min_left = settings.get("window_min_width_left", 260)
        min_right = settings.get("window_min_width_right", 380)
        self.left_container.setMinimumWidth(min_left)
        self.right_container.setMinimumWidth(min_right)
        s = settings.copy()
        if self.window_editor_font_size: s["window_editor_font_size"] = self.window_editor_font_size
        self.notes_panel.apply_editor_style(s)
        
        self.tree_sidebar.refresh_aliases()
        if hasattr(self, "settings_panel_main"):
            self.settings_panel_main.apply_styles()

    def on_data_changed(self, is_dirty=None):
        """Обновляет статус сохранения."""
        # Если состояние не передано, берем его из notes_panel
        if is_dirty is None:
            is_dirty = self.notes_panel.is_dirty

        if is_dirty:
            self.status_text.setText(self.loc.get("unsaved_changes_status"))
            self.status_text.setStyleSheet("color: #dc3545;")
        else:
            self.set_status_saved()
        
    def set_status_saved(self):
        self.status_text.setText(self.loc.get("data_saved_status"))
        self.status_text.setStyleSheet("color: #28a745;")
        
    def _save_splitter_sizes(self):
        sizes = self.splitter.sizes()
        if all(s > 0 for s in sizes):
            st = self.data_manager.get_settings()
            st["window_splitter_sizes"] = sizes
            self.data_manager.save_settings()

    def closeEvent(self, event):
        if self.data_manager.is_locking:
            event.accept()
            return
        self.save_current_item()
        st = self.data_manager.get_settings()
        try:
            if not self.isMaximized() and not self.isMinimized():
                st["window_geometry"] = self.saveGeometry().toHex().data().decode("ascii")
            
            self.v_splitter_save_timer.timeout.emit()
            self.h_splitter_save_timer.timeout.emit()
            st["window_editor_font_size"] = self.window_editor_font_size or 0
            
            # --- СОХРАНЯЕМ СОСТОЯНИЕ В СВОЮ ЯЧЕЙКУ ---
            window_state = self.data_manager.window_states['window']
            current_item = self.tree_sidebar.tree.currentItem()
            if current_item:
                window_state['id'] = current_item.data(0, Qt.ItemDataRole.UserRole).get('id')
            else:
                window_state['id'] = self.tree_sidebar.active_folder_id
            window_state['cursor_pos'] = self.notes_panel.notes_editor.textCursor().position()
            # --- КОНЕЦ ---
            
            st["window_left_visible"] = self.h_splitter.sizes()[0] > 10
            st["window_right_visible"] = self.v_splitter.sizes()[1] > 10
        except Exception as e:
            print(f"Error saving window state: {e}")
        
        self.data_manager.save_settings()
        self.window_closed.emit()
        super().closeEvent(event)
            
    def _zoom_editor(self, delta):
        st = self.data_manager.get_settings()
        current = self.window_editor_font_size or st.get("zen_font_size", 18)
        new_size = max(8, min(72, int(current) + delta))
        self.window_editor_font_size = new_size
        s = st.copy()
        s["window_editor_font_size"] = new_size
        self.notes_panel.apply_editor_style(s)
        
    def _zoom_editor_reset(self):
        self.window_editor_font_size = 0
        self.notes_panel.apply_editor_style(self.data_manager.get_settings())

    def _apply_filter(self):
        """Применяет фильтр к дереву заметок на основе полей поиска."""
        search_text = self.notes_panel.search_input.text().strip()
        
        selected_tag = self.notes_panel.tag_filter_combo.currentText()
        all_tags_text = self.loc.get("all_tags_combo")
        if selected_tag == all_tags_text:
            selected_tag = ""
            
        # Если оба поля пусты, ничего не делаем
        if not search_text and not selected_tag:
            self.tree_sidebar.load_tree_from_db() # Показываем все дерево
            return
            
        # Ищем в БД и получаем ID подходящих заметок
        visible_ids = set(self.data_manager.db.search_notes(search_text, selected_tag))
        
        # Перезагружаем дерево, передавая ему ID для отображения
        self.tree_sidebar._building = True
        try:
            self.tree_sidebar.tree.clear()
            tree_data = self.data_manager.db.get_note_tree()
            self.tree_sidebar._populate_tree(self.tree_sidebar.tree.invisibleRootItem(), tree_data, visible_ids)
            self.tree_sidebar.tree.expandAll()
        finally:
            self.tree_sidebar._building = False

    def _align_toolbar_buttons(self):
        """Выравнивает высоту всех кнопок на главной панели инструментов."""
        QApplication.processEvents() # Даем Qt время вычислить размеры
        
        buttons_to_align = [
            self.notes_panel.new_button, self.notes_panel.save_button,
            self.notes_panel.zen_button, self.preview_button,
            self.to_task_btn, self.datetime_chip, self.time_chip
        ]
        
        max_height = 0
        for btn in buttons_to_align:
            if btn.sizeHint().height() > max_height:
                max_height = btn.sizeHint().height()
        
        if max_height > 0:
            for btn in buttons_to_align:
                btn.setFixedHeight(max_height)

    def _enter_zen_mode_from_window(self):
        """Просто вызывает open_zen_mode в дочерней панели."""
        # NotesPanel.open_zen_mode сам определит ID и испустит сигнал
        self.notes_panel.open_zen_mode()

class GlobalAudioController(QObject):
    playlists_changed = pyqtSignal(list, str)
    current_playlist_changed = pyqtSignal(str)
    tracks_changed = pyqtSignal(list)
    current_index_changed = pyqtSignal(int)
    state_changed = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.playbackStateChanged.connect(self._relay_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status)
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        self._playlists_file = os.path.join(base_dir, "audio_playlists.json")
        self.playlists = {}
        self.playlist_order = []
        self.current_playlist = ""

        self.playing_playlist_name = "" # Имя плейлиста, который сейчас играет
        self.playing_index = -1       # Индекс в этом плейлисте

        self.index = -1
        self.audio_output.setVolume(0.5)
        self._load_playlists()

    def _load_playlists(self):
        playlist_file = os.path.join(BASE_PATH, "audio_playlists.json")
        try:
            if not os.path.exists(playlist_file): raise FileNotFoundError
            with open(playlist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)


            # Загружаем плейлисты и сразу преобразуем пути в абсолютные
            loaded_playlists = data.get("playlists", {})
            self.playlists = {}
            for name, tracks in loaded_playlists.items():
                self.playlists[name] = [resolve_path(t) for t in tracks]
            
            self.playlist_order = data.get("order", list(self.playlists.keys()))
            self.current_playlist = data.get("current", "")
        except (FileNotFoundError, json.JSONDecodeError):
            self.playlists = {}
            self.playlist_order = []
            self.current_playlist = ""
            
        if "Zen" not in self.playlists:
            zen_dir = os.path.join(BASE_PATH, "zen_audio")
            if os.path.isdir(zen_dir):
                exts = ('.mp3', '.wav', '.ogg', '.flac', '.m4a')
                zen_tracks = [os.path.join(zen_dir, f) for f in os.listdir(zen_dir) if f.lower().endswith(exts)]
                if zen_tracks:
                    self.playlists["Zen"] = zen_tracks
                    if "Zen" not in self.playlist_order:
                        self.playlist_order.insert(0, "Zen")
                    self._save_playlists()

        if not self.playlists: self.playlists["Default"] = []
        if not self.playlist_order: self.playlist_order = list(self.playlists.keys())
        if not self.current_playlist or self.current_playlist not in self.playlists:
            self.current_playlist = self.playlist_order[0] if self.playlist_order else ""
        self._emit_all()


    def _save_playlists(self):

        # Перед сохранением преобразуем абсолютные пути в относительные, если возможно
        portable_playlists = {}
        for name, tracks in self.playlists.items():
            portable_tracks = []
            for track_path in tracks:
                try:
                    rel_path = os.path.relpath(track_path, BASE_PATH)
                    if not rel_path.startswith('..'):
                        portable_tracks.append(rel_path)
                    else:
                        portable_tracks.append(track_path) # Путь вне папки программы
                except ValueError:
                    portable_tracks.append(track_path) # Путь на другом диске
            portable_playlists[name] = portable_tracks

        try:
            playlist_file = os.path.join(BASE_PATH, "audio_playlists.json")
            data = {"playlists": portable_playlists, "order": self.playlist_order, "current": self.current_playlist}
            with open(playlist_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except (IOError, TypeError) as e:
            print(f"Не удалось сохранить плейлисты: {e}")

    def _emit_all(self):
        names = [n for n in self.playlist_order if n in self.playlists]
        if not names:
            names = list(self.playlists.keys())
            self.playlist_order = names[:]
        if self.current_playlist not in names and names:
            self.current_playlist = names[0]
            
        self.playlists_changed.emit(names, self.current_playlist)
        self.current_playlist_changed.emit(self.current_playlist)
        self.tracks_changed.emit(self.get_tracks())

        # Показываем выделение, только если текущий плейлист совпадает с играющим
        if self.current_playlist == self.playing_playlist_name:
            self.current_index_changed.emit(self.playing_index)
        else:
            self.current_index_changed.emit(-1) # Снимаем выделение в других плейлистах
            
        self.state_changed.emit(self.player.playbackState())

    def get_tracks(self):
        return list(self.playlists.get(self.current_playlist, []))

    def switch_playlist_by_offset(self, delta: int):
        names = [n for n in self.playlist_order if n in self.playlists]
        if not names: return
        try:
            i = names.index(self.current_playlist)
            i = (i + delta) % len(names)
            self.set_current_playlist(names[i])
        except ValueError:
            if names: self.set_current_playlist(names[0])
    
    def set_current_playlist(self, name: str):
        if name not in self.playlists: return
        self.current_playlist = name
        #self.index = -1
        self._emit_all()
        self._save_playlists()
    
    def add_playlist(self, name: str):
        name = name.strip() or "New"
        base = name
        k = 1
        while name in self.playlists:
            k += 1
            name = f"{base} {k}"
        self.playlists[name] = []
        self.playlist_order.append(name)
        self.set_current_playlist(name)
    
    def rename_playlist(self, old: str, new: str):
        if old not in self.playlists: return
        new = new.strip() or old
        if new == old or new in self.playlists: return
        self.playlists[new] = self.playlists.pop(old)
        self.playlist_order = [new if x == old else x for x in self.playlist_order]
        if self.current_playlist == old: self.current_playlist = new
        self._emit_all()
        self._save_playlists()
    
    def delete_playlist(self, name: str):
        if name not in self.playlists or len(self.playlists) <= 1: return
        del self.playlists[name]
        self.playlist_order = [x for x in self.playlist_order if x != name]
        if self.current_playlist == name:
            self.current_playlist = self.playlist_order[0] if self.playlist_order else ""
            self.index = -1
        self._emit_all()
        self._save_playlists()
    
    def add_files(self, paths: list[str]):
        if not paths: return
        tracks = self.get_tracks()
        added = 0
        for p in paths:
            if p and os.path.isfile(p) and p not in tracks:
                tracks.append(p)
                added += 1
        if added:
            self.playlists[self.current_playlist] = tracks
            self.tracks_changed.emit(self.get_tracks())
            self._save_playlists()
    
    def add_folder(self, folder_path: str):
        if not folder_path or not os.path.isdir(folder_path): return
        exts = ('.mp3', '.wav', '.ogg', '.flac', '.m4a')
        tracks = self.get_tracks()
        added = 0
        try:
            for root, _, files in os.walk(folder_path):
                for f in files:
                    if f.lower().endswith(exts):
                        p = os.path.join(root, f)
                        if p not in tracks:
                            tracks.append(p)
                            added += 1
        except Exception as e:
            print("add_folder error:", e)
        if added:
            self.playlists[self.current_playlist] = tracks
            self.tracks_changed.emit(self.get_tracks())
            self._save_playlists()
    
    def remove_indexes(self, idxs: list[int]):
        if not idxs: return
        tracks = self.get_tracks()
        idxs = sorted(set([i for i in idxs if 0 <= i < len(tracks)]), reverse=True)
        cur_path = self.player.source().toLocalFile() if self.player.source().isValid() else None
        for i in idxs: del tracks[i]
        self.playlists[self.current_playlist] = tracks
        if cur_path not in tracks:
            self.index = -1
            self.stop()
        else:
            self.index = tracks.index(cur_path)
        self.tracks_changed.emit(self.get_tracks())
        self.current_index_changed.emit(self.index)
        self._save_playlists()
    
    def set_order(self, new_files_list: list[str], current_path: str | None = None):
        self.playlists[self.current_playlist] = list(new_files_list or [])
        if current_path and current_path in self.playlists[self.current_playlist]:
            self.index = self.playlists[self.current_playlist].index(current_path)
            self.current_index_changed.emit(self.index)
        elif not self.playlists[self.current_playlist]:
            self.index = -1
            self.stop()
        self.tracks_changed.emit(self.get_tracks())
        self._save_playlists()

    def is_playing(self):
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def play_index(self, i: int):
        tracks = self.get_tracks()
        if not tracks: return
        i = max(0, min(len(tracks) - 1, i))
        
        self.playing_index = i
        self.playing_playlist_name = self.current_playlist


        self.player.setSource(QUrl.fromLocalFile(tracks[self.playing_index]))
        self.player.play()
        self.current_index_changed.emit(self.playing_index)

    def toggle_play_pause(self):
        if self.is_playing():
            self.player.pause()
            return

        # Если трек уже был выбран (на паузе или просто загружен)
        if self.playing_index != -1 and self.playing_playlist_name:
            # --- НОВАЯ ЛОГИКА ПРОВЕРКИ ---
            # Если текущий плейлист НЕ совпадает с тем, который должен играть
            if self.current_playlist != self.playing_playlist_name:
                # Тихо переключаемся обратно на нужный плейлист
                self.set_current_playlist(self.playing_playlist_name)
            # --- КОНЕЦ ---

            # Теперь мы гарантированно в правильном плейлисте
            tracks = self.get_tracks()
            if 0 <= self.playing_index < len(tracks):
                self.player.play()
            else: # На случай, если трек был удален
                self.stop()
        
        # Если вообще ничего не играло, начинаем с начала текущего плейлиста
        else:
            tracks = self.get_tracks()
            if tracks:
                self.play_index(0)

    def next(self):
        """Переключает на следующий трек."""
        tracks = self.get_tracks() # Берем треки из ТЕКУЩЕГО (видимого) плейлиста
        if not tracks: return
        
        # Просто увеличиваем индекс на 1, без зацикливания
        next_index = self.playing_index + 1
        
        # Проверяем, не вышли ли мы за пределы плейлиста
        if 0 <= next_index < len(tracks):
            self.play_index(next_index)
        else:
            # Если следующего трека нет, останавливаемся
            self.stop()

    def prev(self):
        """Переключает на предыдущий трек."""
        tracks = self.get_tracks()
        if not tracks: return
        
        # Просто уменьшаем индекс на 1
        prev_index = self.playing_index - 1
        
        # Проверяем, что мы не вышли за левую границу списка
        if 0 <= prev_index < len(tracks):
            self.play_index(prev_index)
        else:
            # Если предыдущего трека нет (это был первый),
            # можно либо остановиться, либо начать с того же трека заново.
            # Начнем заново, это более стандартное поведение.
            self.play_index(self.playing_index)

    def stop(self):
        self.player.stop()
        # --- НОВАЯ ЛОГИКА: СБРАСЫВАЕМ СОСТОЯНИЕ ---
        self.playing_index = -1
        self.playing_playlist_name = ""
        self.current_index_changed.emit(-1)

    def set_volume(self, v: int):
        new_volume_float = max(0.0, min(1.0, v / 100.0))
        if self.audio_output.volume() != new_volume_float:
            self.audio_output.setVolume(new_volume_float)

    def volume(self) -> int:
        return int(round(self.audio_output.volume() * 100))

    def toggle_mute(self):
        self.audio_output.setMuted(not self.audio_output.isMuted())

    def is_muted(self) -> bool:
        return self.audio_output.isMuted()

    def _relay_state_changed(self, st):
        self.state_changed.emit(st)

    def _on_media_status(self, status):
        """Вызывается при изменении статуса медиа."""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            
            # Получаем актуальный список треков из играющего плейлиста
            current_tracks = self.playlists.get(self.playing_playlist_name, [])
            if not current_tracks:
                self.stop()
                return

            # Проверяем, не является ли текущий трек последним в списке
            is_last_track = (self.playing_index >= len(current_tracks) - 1)

            if not is_last_track:
                # Если это НЕ последний трек, просто переключаемся на следующий
                self.next()
            else:
                # Если это был последний трек, останавливаем воспроизведение
                self.stop()
            # --- КОНЕЦ НОВОЙ ЛОГИКИ ---

class GlobalAudioWidget(QWidget):
    close_requested = pyqtSignal()

    def __init__(self, controller: GlobalAudioController, loc: LocalizationManager, parent=None):
        super().__init__(parent)
        self.ctrl = controller
        self.loc = loc
        self.is_slider_pressed = False
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)
        head = QHBoxLayout()
        head.setSpacing(6)
        self.prev_pl_btn = QToolButton()
        self.next_pl_btn = QToolButton()
        self.playlist_label = QPushButton()
        self.playlist_label.setFixedHeight(32)
        self.playlist_label.setFlat(True)
        self.playlist_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.playlist_label.setObjectName("playlistLabel")
        self.playlist_label.clicked.connect(self._open_playlist_menu)
        head.addWidget(self.prev_pl_btn)
        head.addWidget(self.playlist_label, 1)
        head.addWidget(self.next_pl_btn)
        main_layout.addLayout(head)

        self.now_playing_label = QLabel("...")
        self.now_playing_label.setObjectName("nowPlayingLabel")
        self.now_playing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.now_playing_label.setWordWrap(True) # На случай длинных названий
        main_layout.addWidget(self.now_playing_label)

        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(6)
        self.time_label = QLabel("00:00")
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.duration_label = QLabel("00:00")
        progress_layout.addWidget(self.time_label)
        progress_layout.addWidget(self.progress_slider, 1)
        progress_layout.addWidget(self.duration_label)
        main_layout.addLayout(progress_layout)

        transport = QHBoxLayout()
        transport.setSpacing(6)
        self.prev_btn = QToolButton()
        self.play_btn = QToolButton()
        self.stop_btn = QToolButton()
        self.next_btn = QToolButton()
        transport.addStretch()
        transport.addWidget(self.prev_btn)
        transport.addWidget(self.play_btn)
        transport.addWidget(self.stop_btn)
        transport.addWidget(self.next_btn)
        transport.addStretch()
        main_layout.addLayout(transport)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
        main_layout.addWidget(self.list, 1)

        self.audio_filebar = QWidget()
        fb = QHBoxLayout(self.audio_filebar)
        fb.setContentsMargins(0, 0, 0, 0)
        fb.setSpacing(8)
        self.audio_add_files_btn = QToolButton()
        self.audio_add_folder_btn = QToolButton()
        self.audio_remove_btn = QToolButton()
        self.audio_vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.audio_vol_slider.setObjectName("volumeSlider")
        self.audio_vol_slider.setRange(0, 100)
        self.audio_vol_slider.setFixedSize(64, 16)
        self.audio_mute_btn = QToolButton()
        fb.addWidget(self.audio_add_files_btn)
        fb.addWidget(self.audio_add_folder_btn)
        fb.addWidget(self.audio_remove_btn)
        fb.addStretch()
        fb.addWidget(self.audio_vol_slider)
        fb.addWidget(self.audio_mute_btn)
        main_layout.addWidget(self.audio_filebar)

        self.prev_pl_btn.clicked.connect(lambda: self.ctrl.switch_playlist_by_offset(-1))
        self.next_pl_btn.clicked.connect(lambda: self.ctrl.switch_playlist_by_offset(1))
        self.prev_btn.clicked.connect(self.ctrl.prev)
        self.play_btn.clicked.connect(self.ctrl.toggle_play_pause)
        self.stop_btn.clicked.connect(self.ctrl.stop)
        self.next_btn.clicked.connect(self.ctrl.next)
        self.progress_slider.sliderMoved.connect(self.ctrl.player.setPosition)
        self.progress_slider.sliderPressed.connect(lambda: setattr(self, 'is_slider_pressed', True))
        self.progress_slider.sliderReleased.connect(lambda: setattr(self, 'is_slider_pressed', False))
        self.list.itemDoubleClicked.connect(self._play_selected)
        self.list.model().rowsMoved.connect(self._on_rows_moved)
        self.audio_add_files_btn.clicked.connect(self._add_files)
        self.audio_add_folder_btn.clicked.connect(self._add_folder)
        self.audio_remove_btn.clicked.connect(self._remove_selected)
        self.audio_vol_slider.valueChanged.connect(self.ctrl.set_volume)
        self.audio_mute_btn.clicked.connect(self._toggle_mute)

        self.ctrl.playlists_changed.connect(self._on_playlists_changed)
        self.ctrl.current_playlist_changed.connect(self._on_current_playlist)
        self.ctrl.tracks_changed.connect(self._reload_tracks)
        self.ctrl.current_index_changed.connect(self._on_current_changed)
        self.ctrl.state_changed.connect(self._on_state_changed)
        self.ctrl.player.positionChanged.connect(self._on_position_changed)
        self.ctrl.player.durationChanged.connect(self._on_duration_changed)
        self.ctrl.audio_output.volumeChanged.connect(self.update_slider_volume)
        self.ctrl.audio_output.mutedChanged.connect(lambda muted: self._update_mute_icon())
        
        self._on_playlists_changed(getattr(self.ctrl, "playlist_order", []), getattr(self.ctrl, "current_playlist", ""))
        self._reload_tracks(self.ctrl.get_tracks())
        self._on_current_changed(getattr(self.ctrl, "index", -1))
        
        dm = self.ctrl.parent()
        if dm and hasattr(dm, 'get_settings'):
            self.apply_theme_icons(dm.get_settings())
        
        self.update_slider_volume(self.ctrl.audio_output.volume())
        self._on_duration_changed(self.ctrl.player.duration())

    def apply_zen_style(self, floating_fg, component_bg, hover_bg, border_color, accent):
        stylesheet = f"""
            QListWidget {{
                background-color: {component_bg}; color: {floating_fg};
                border: 1px solid {border_color}; border-radius: 6px;
            }}
            QListWidget::item {{ padding: 5px; color: {floating_fg}; }}
            QListWidget::item:selected {{ background-color: {hover_bg}; border-radius: 4px; }}
            QPushButton#playlistLabel {{
                color: {floating_fg};
                background-color: {component_bg};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 5px;
                text-align: center;
                font-weight: bold;
            }}
            QPushButton#playlistLabel:hover {{ background-color: {hover_bg}; border-radius: 4px; }}
            QLabel {{ color: {floating_fg}; background: transparent; }}
            QToolButton {{ background: transparent; border: none; border-radius: 4px; }}
            QToolButton:hover {{ background-color: {hover_bg}; }}
            QSlider::groove:horizontal {{
                background: {border_color};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {accent};
                width: 14px;
                margin: -5px 0;
                border-radius: 7px; /* Делает ползунок круглым */
            }}
            QSlider::sub-page:horizontal {{
                background: {accent};
                border-radius: 2px;
            }}
        """
        self.setStyleSheet(stylesheet)


    def update_slider_volume(self, volume_float):
        if hasattr(self, 'audio_vol_slider'):
            new_value = int(round(volume_float * 100))
            self.audio_vol_slider.blockSignals(True)
            self.audio_vol_slider.setValue(new_value)
            self.audio_vol_slider.blockSignals(False)

    def apply_theme_icons(self, settings: dict):
        self.next_pl_btn.setIcon(ThemedIconProvider.icon("chev_r", settings))
        self.prev_pl_btn.setIcon(ThemedIconProvider.icon("chev_l", settings))
        self.prev_btn.setIcon(ThemedIconProvider.icon("prev", settings))
        self.stop_btn.setIcon(ThemedIconProvider.icon("stop", settings))
        self.next_btn.setIcon(ThemedIconProvider.icon("next", settings))
        self.audio_add_files_btn.setIcon(ThemedIconProvider.icon("add_file", settings))
        self.audio_add_folder_btn.setIcon(ThemedIconProvider.icon("add_folder", settings))
        self.audio_remove_btn.setIcon(ThemedIconProvider.icon("trash", settings))
        self._on_state_changed(self.ctrl.player.playbackState())
        self._update_mute_icon()
        self.retranslate_ui()

    def retranslate_ui(self):
        self.playlist_label.setText(self.ctrl.current_playlist or self.loc.get("playlist", "Плейлист"))
        self.audio_add_files_btn.setToolTip(self.loc.get("audio_add_files", "Добавить файлы"))
        self.audio_add_folder_btn.setToolTip(self.loc.get("audio_add_folder", "Добавить папку"))
        self.audio_remove_btn.setToolTip(self.loc.get("audio_remove_selected", "Удалить выбранные"))
        self.audio_vol_slider.setToolTip(self.loc.get("audio_volume", "Громкость"))
        self._update_mute_icon()
        
    def _on_position_changed(self, pos):
        if not self.is_slider_pressed:
            self.progress_slider.setValue(pos)
        self.time_label.setText(f"{pos//60000:02d}:{pos//1000%60:02d}")

    def _on_duration_changed(self, dur):
        self.progress_slider.setRange(0, dur)
        self.duration_label.setText(f"{dur//60000:02d}:{dur//1000%60:02d}")
        if dur > 0:
            self._on_position_changed(self.ctrl.player.position())

    def _on_playlists_changed(self, names, current):
        self.playlist_label.setText(current or (names[0] if names else self.loc.get("playlist", "Плейлист")))

    def _on_current_playlist(self, name: str):
        self.playlist_label.setText(name or self.loc.get("playlist", "Плейлист"))

    def _open_playlist_menu(self):
        dm = self.ctrl.parent()
        settings = dm.get_settings() if dm and hasattr(dm, 'get_settings') else DEFAULT_SETTINGS
        menu = QMenu(self)
        is_dark, accent, bg, text, _ = theme_colors(settings)
        border = "#555" if is_dark else "#ced4da"
        comp = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        menu.setStyleSheet(f"QMenu{{background-color:{comp};color:{text};border:1px solid {border};border-radius:6px;padding:5px;}} "
                           f"QMenu::item{{padding:6px 15px;}} QMenu::item:selected{{background-color:{accent};color:white;}} "
                           f"QMenu::separator{{height:1px;background:{border};margin:6px 10px;}}")
        menu.addAction(self.loc.get("add_list_menu"), self._add_playlist)
        menu.addAction(self.loc.get("rename_list_menu"), self._rename_playlist)
        if len(self.ctrl.playlists) > 1:
            menu.addAction(self.loc.get("delete_list_menu"), self._delete_playlist)
        menu.exec(self.playlist_label.mapToGlobal(self.playlist_label.rect().bottomLeft()))

    def _add_playlist(self):
        name, ok = QInputDialog.getText(self, self.loc.get("add_list_menu"), self.loc.get("new_list_prompt"))
        if ok and name.strip():
            self.ctrl.add_playlist(name.strip())

    def _rename_playlist(self):
        cur = self.ctrl.current_playlist
        name, ok = QInputDialog.getText(self, self.loc.get("rename_list_menu"), self.loc.get("rename_list_prompt"), QLineEdit.EchoMode.Normal, cur)
        if ok and name.strip() and name.strip() != cur:
            self.ctrl.rename_playlist(cur, name.strip())

    def _delete_playlist(self):
        cur = self.ctrl.current_playlist
        if len(self.ctrl.playlists) <= 1: return
        ok = QMessageBox.question(self, self.loc.get("delete_list_menu"), self.loc.get("delete_list_confirm").format(list_name=cur))
        if ok == QMessageBox.StandardButton.Yes:
            self.ctrl.delete_playlist(cur)

    def _reload_tracks(self, files: list):
        self.list.clear()
        for i, path in enumerate(files):
            it = QListWidgetItem(f"{i+1}. {os.path.basename(path)}")
            it.setData(Qt.ItemDataRole.UserRole, path)
            self.list.addItem(it)

    def _on_rows_moved(self, parent, start, end, destParent, destRow):
        new_files = [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())]
        current_path = self.ctrl.player.source().toLocalFile() if self.ctrl.player.source().isValid() else None
        self.ctrl.set_order(new_files, current_path)
        self._renumber()

    def _renumber(self):
        for i in range(self.list.count()):
            it = self.list.item(i)
            it.setText(f"{i+1}. {os.path.basename(it.data(Qt.ItemDataRole.UserRole))}")

    def _on_current_changed(self, idx: int):
        if self.ctrl.playing_playlist_name and self.ctrl.playing_index != -1:
            try:
                playing_track_path = self.ctrl.playlists[self.ctrl.playing_playlist_name][self.ctrl.playing_index]
                self.now_playing_label.setText(os.path.basename(playing_track_path))
            except (KeyError, IndexError):
                self.now_playing_label.setText("...")
        else:
            self.now_playing_label.setText("...")

        for i in range(self.list.count()):
            it = self.list.item(i)
            f = it.font()
            f.setBold(False)
            it.setFont(f)

        if self.ctrl.current_playlist == self.ctrl.playing_playlist_name and 0 <= self.ctrl.playing_index < self.list.count():
            item_to_select = self.list.item(self.ctrl.playing_index)
            if item_to_select:
                font = item_to_select.font()
                font.setBold(True)
                item_to_select.setFont(font)
                
                if not item_to_select.isSelected():

                    self.list.setCurrentItem(item_to_select)
                self.list.scrollToItem(item_to_select, QAbstractItemView.ScrollHint.PositionAtCenter)
        else:
            self.list.clearSelection()

    def _on_state_changed(self, st):
        dm = self.ctrl.parent()
        settings = dm.get_settings() if dm and hasattr(dm, 'get_settings') else DEFAULT_SETTINGS
        if st == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setIcon(ThemedIconProvider.icon("pause", settings))
            self.play_btn.setToolTip(self.loc.get("audio_pause", "Пауза"))
        else:
            self.play_btn.setIcon(ThemedIconProvider.icon("play", settings))
            self.play_btn.setToolTip(self.loc.get("audio_play", "Воспроизвести"))

    def _play_selected(self, item: QListWidgetItem):
        self.ctrl.play_index(self.list.row(item))

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, self.loc.get("audio_add_files", "Добавить файлы"), "", "Audio Files (*.mp3 *.wav *.ogg *.flac *.m4a);;All Files (*)")
        if paths:
            self.ctrl.add_files(paths)

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.loc.get("audio_add_folder", "Добавить папку"), "")
        if folder:
            self.ctrl.add_folder(folder)

    def _remove_selected(self):
        rows = [self.list.row(it) for it in self.list.selectedItems()]
        self.ctrl.remove_indexes(rows)

    def _toggle_mute(self):
        self.ctrl.toggle_mute()

    def _update_mute_icon(self):
        dm = self.ctrl.parent()
        settings = dm.get_settings() if dm and hasattr(dm, 'get_settings') else DEFAULT_SETTINGS
        icon_name = "volume_mute" if self.ctrl.is_muted() else "volume"
        self.audio_mute_btn.setIcon(ThemedIconProvider.icon(icon_name, settings))
        self.audio_mute_btn.setToolTip(self.loc.get("audio_mute_on", "Включить звук") if self.ctrl.is_muted() else self.loc.get("audio_mute_off", "Выключить звук"))

class TriggerButton(QWidget):
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, loc_manager):
        super().__init__()
        self.setObjectName("trigger_button_container")
        self.loc = self.loc_manager = loc_manager
        
        self.button = QPushButton(self)
        self.button.setObjectName("trigger_button")

        self.button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.db = DatabaseManager() # Создаем экземпляр нашего менеджера БД
        self.global_audio = GlobalAudioController(self) # Это оставляем как есть

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.button)

        self.settings = DEFAULT_SETTINGS.copy()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(20, 100)

        self.main_popup = None 
        self.main_window = None
        self.about_dialog = None
        self.zen_window = None
        self.zen_source_timestamp = None
        self.pending_zen_data = None
        self.is_entering_zen = False
        self.is_switching_to_window = False
        self.is_switching_to_popup = False
        self.is_locking = False
        self._unlocked = False

        self.window_states = {
            'popup': {'id': None, 'cursor_pos': 0},
            'window': {'id': None, 'cursor_pos': 0}
        }

        self.note_to_select_after_load = None
        self.notes_root_folder = "Заметки"
        self.global_audio = GlobalAudioController(self)
        self.zen_return_to_window_mode = False
        
        self.loc.language_changed.connect(self._on_language_changed)
        
        self.update_position_and_style()
        self.button.clicked.connect(self._on_left_click)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
        
        self.backup_timer = QTimer(self)
        self.backup_timer.timeout.connect(self.create_backup)
        self._restart_backup_timer()
        
        QApplication.instance().aboutToQuit.connect(self.on_app_quit)
        self._popup_lock = False
        self.login_window = None

        # Мы делаем его дочерним к самому TriggerButton,
        # поэтому он будет активен, пока существует приложение.
        QShortcut(QKeySequence("Ctrl+L"), self, self.lock_application)

        self.load_settings()
        self.loc.set_language(self.settings.get("language", "ru_RU"))


    def load_data_into_ui(self, container):
        """Загружает данные из БД в активный UI контейнер."""
        if not container:
            return

        if isinstance(container, WindowMain):
            container.load_note_tree()

        elif isinstance(container, MainPopup):
            container.notes_panel.load_notes_for_popup()

        if hasattr(container, 'tasks_panel'):
            container.tasks_panel.load_task_lists()
             
        if container.isVisible():
            container.set_status_saved()

    def _restart_backup_timer(self):
        self.backup_timer.stop()
        interval_ms = self.settings.get("backup_interval_min", 60) * 60 * 1000
        if interval_ms > 0:
            self.backup_timer.start(interval_ms)

    def on_app_quit(self):
        container = self._choose_ui()
        if isinstance(container, WindowMain):
            container.save_current_item()
        elif isinstance(container, MainPopup):
            container.notes_panel.save_current_note()
        
    def _on_left_click(self):
        if self.db.is_password_set() and not self._unlocked:
            self._show_login_dialog()
            return
            
        if self.main_window and self.main_window.isVisible():
            self.main_window.activateWindow()
            return

        if self._popup_lock: return
        self._popup_lock = True
        QTimer.singleShot(400, lambda: setattr(self, "_popup_lock", False))
        
        if self.main_popup and self.main_popup.isVisible():
            self.main_popup.close()
        else:
            self.show_main_popup()

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    def load_settings(self):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
            settings = DEFAULT_SETTINGS.copy()
            settings.update(loaded_settings)
            self.settings = settings
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = DEFAULT_SETTINGS.copy()

    def get_settings(self): return self.settings
    def get_all_notes_from_cache(self): return self.all_notes_cache

    def _choose_ui(self):
        if self.main_window and self.main_window.isVisible():
            return self.main_window
        if self.main_popup and self.main_popup.isVisible():
            return self.main_popup
        return None
        
    def _get_current_note_ts(self, container):
        if not container: return None
        try:
            if item := container.notes_panel.current_note_item:
                return (item.data(Qt.ItemDataRole.UserRole) or {}).get('timestamp')
        except Exception:
            pass
        return None

    def _on_language_changed(self):
        if self.main_popup: self.main_popup.retranslate_ui()
        if self.main_window: self.main_window.retranslate_ui()
        if self.zen_window: self.zen_window.retranslate_ui()
        if self.about_dialog: self.about_dialog.retranslate_ui()
        self.update_position_and_style()

    def update_position_and_style(self):
        screen = QApplication.primaryScreen().geometry()
        pos = self.settings.get("trigger_pos", "right")
        icon = ThemedIconProvider.icon("chev_l" if pos == "left" else "chev_r", self.settings, QSize(16, 16))
        self.button.setIcon(icon)
        self.button.setIconSize(QSize(16, 16))
        self.button.setText("")
        accent = self.settings.get("accent_color", "#007bff")
        style = f"background-color:{accent};color:white; border: none;"
        if pos == "left":
            self.move(0, int(screen.height() * 0.4))
            style += "border-top-right-radius:5px;border-bottom-right-radius:5px;"
        else:
            self.move(screen.width() - self.width(), int(screen.height() * 0.4))
            style += "border-top-left-radius:5px;border-bottom-left-radius:5px;"
        self.button.setStyleSheet(f"QPushButton#trigger_button{{{style}}} QPushButton#trigger_button:hover{{opacity:0.9;}}")

    def _on_context_menu(self, pos):
        menu = QMenu(self)
        menu.setObjectName("contextMenu")
        is_dark, accent, bg, text, _ = theme_colors(self.settings)
        border = "#555" if is_dark else "#ced4da"
        comp = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        menu.setStyleSheet(f"QMenu{{background-color:{comp};color:{text};border:1px solid {border};border-radius:6px;padding:5px;}} "
                           f"QMenu::item{{padding:6px 15px;}} QMenu::item:selected{{background-color:{accent};color:white;}} "
                           f"QMenu::separator{{height:1px;background:{border};margin:6px 10px;}}")
        
        if self.db.is_password_set():
            menu.addAction(self.loc.get("lock_app"), self.lock_application)
            menu.addSeparator()
        
        menu.addAction(self.loc.get("about_menu"), self.show_about_dialog)
        menu.addAction(self.loc.get("open_window_menu"), self.show_main_window)
        menu.addSeparator()

        export_menu = menu.addMenu(self.loc.get("export_menu_title", "Экспорт..."))
        export_menu.addAction(self.loc.get("export_all_to_file", "Экспортировать всё в один файл..."), lambda: self.export_notes(scope="all"))
        export_menu.addAction(self.loc.get("export_all_to_folders", "Экспортировать всё в папки..."), self.export_notes_to_folders)
        
        menu.addAction(self.loc.get("import_folder_title"), self.import_notes_from_folders)

        menu.addAction(self.loc.get("restore_menu"), self.restore_from_backup)
        menu.addSeparator()
        menu.addAction(self.loc.get("export_settings"), self.export_settings_file)
        menu.addAction(self.loc.get("import_settings"), self.import_settings_file)
        menu.addSeparator()
        menu.addAction(self.loc.get("exit_menu"), QApplication.instance().quit)
        menu.exec(self.mapToGlobal(pos))
    
    def show_main_popup(self, note_to_select=None):

        if self.main_popup is None:
            self.main_popup = MainPopup(self)
            self.main_popup.animation_finished_and_hidden.connect(self.on_popup_closed)
        
        self.load_data_into_ui(self.main_popup)
        
        if note_to_select:
            item_to_select = self.main_popup.notes_panel._find_item_by_id(note_to_select)
            if item_to_select:
                self.main_popup.notes_panel.tree_widget.setCurrentItem(item_to_select)
                self.main_popup.notes_panel._on_tree_item_clicked(item_to_select, 0)

        self.main_popup.retranslate_ui()
        self.main_popup.apply_theme(self.get_settings())
        
        pos = self.settings.get("trigger_pos", "right")
        screen = QApplication.primaryScreen().availableGeometry()
        popup_x = self.width() if pos == "left" else screen.width() - 380
        player_pos = QPoint(popup_x, screen.y())
        self.main_popup.show_animated(player_pos, from_left=(pos == "left"))

    def _on_main_window_splitter_moved(self, sizes):
        if self.main_window and self.main_window.settings_panel_main.isVisible():
            self.main_window.settings_panel_main.update_splitter_values(sizes)

    def show_main_window(self, note_to_select=None):
        self.setEnabled(False)
        self.setWindowOpacity(0.5)
        
        if self.main_window is None:
            self.main_window = WindowMain(self)
            self.main_window.window_closed.connect(self.on_window_closed)
            self.main_window.splitter_sizes_changed.connect(self._on_main_window_splitter_moved)
        
        self.load_data_into_ui(self.main_window)
        
        item_id_to_select = note_to_select

        if item_id_to_select:
            item_to_process = self.main_window.tree_sidebar.select_item_by_id(item_id_to_select)
            
            if item_to_process:
                item_data = item_to_process.data(0, Qt.ItemDataRole.UserRole)
                if item_data.get('type') == 'note':
                    self.main_window.edit_note(item_to_process)
                elif item_data.get('type') == 'folder':
                    self.main_window.edit_folder_description(item_to_process)
            else:
                self.main_window.clear_editor()
        else:
             self.main_window.clear_editor()

        self.main_window.retranslate_ui()
        self.main_window.apply_theme(self.get_settings())
        self.main_window._restore_window_state_or_set_ratio()
        self.main_window._apply_left_right_visibility()
        self.main_window._update_word_count()
        
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()
        self.main_window._first_show = True

    def switch_to_popup_from_window(self):
        if self.main_window and self.main_window.isVisible():
            self.is_switching_to_popup = True
            self.main_window.close()

    def switch_to_window_mode(self):
        if self.main_popup and self.main_popup.isVisible():
            self.main_popup.notes_panel.save_current_note()

            self.is_switching_to_window = True

            popup_state = self.window_states['popup']
            current_item = self.main_popup.notes_panel.tree_widget.currentItem()
            if current_item:
                popup_state['id'] = current_item.data(0, Qt.ItemDataRole.UserRole).get('id')
            else:
                popup_state['id'] = self.main_popup.notes_panel.active_folder_id
            popup_state['cursor_pos'] = self.main_popup.notes_panel.notes_editor.textCursor().position()
            
            self.main_popup.close()

    def enter_zen_mode(self, note_id, source_window=None):
        active_ui = source_window or self._choose_ui()
        
        if isinstance(active_ui, WindowMain):
            self.zen_return_to_window_mode = True

            self.last_cursor_position = active_ui.notes_panel.notes_editor.textCursor().position()
            self.last_selected_item_id = active_ui.tree_sidebar.active_folder_id

        elif isinstance(active_ui, MainPopup):
            self.zen_return_to_window_mode = False
            self.last_cursor_position = active_ui.notes_panel.notes_editor.textCursor().position()
            self.last_selected_item_id = active_ui.notes_panel.active_folder_id
        
        self.pending_zen_data = note_id
        self.is_entering_zen = True
        
        if active_ui:
            active_ui.close()
        else:
            self.on_popup_closed()

    def on_window_closed(self):
        if self.main_window:
            try:
                self.main_window.window_closed.disconnect(self.on_window_closed)
            except TypeError:
                pass
            self.main_window.deleteLater()
            self.main_window = None

        if self.is_entering_zen:
            self._launch_zen_window()
        elif self.is_switching_to_popup:
            self.is_switching_to_popup = False
            self.setEnabled(True)
            self.setWindowOpacity(1.0)
            
            # --- ИСПРАВЛЕНИЕ: Читаем ID из правильного места ---
            note_id = self.window_states['window'].get('id')
            QTimer.singleShot(10, lambda: self.show_main_popup(note_to_select=note_id))
            # --- КОНЕЦ ---

        else: # Обычное закрытие крестиком
            self.setEnabled(True)
            self.setWindowOpacity(1.0)
            self.show()

    def on_popup_closed(self, note_to_open_in_window=None):


        if self.main_popup:
            try:
                self.main_popup.animation_finished_and_hidden.disconnect()
            except TypeError:
                pass
            self.main_popup.animation_finished_and_hidden.connect(self.on_popup_closed)

        if self.is_switching_to_window:
            self.is_switching_to_window = False
            note_id = self.window_states['popup'].get('id')
            self.show_main_window(note_to_select=note_id)
            return

        if self.is_entering_zen:
            self._launch_zen_window()
        else:
            self.setEnabled(True)
            self.setWindowOpacity(1.0)


    def _launch_zen_window(self):
        note_id = self.pending_zen_data
        self.is_entering_zen = False
        self.pending_zen_data = None
        
        self.hide()
        self.zen_window = ZenModeWindow(note_id, self.get_settings(), self.loc, self)
        
        try:
            self.zen_window.attach_global_audio_widget(self.global_audio, self.loc)
        except Exception as e:
            print(f"Failed to attach audio widget to Zen: {e}")
            
        self.zen_window.zen_exited.connect(self.handle_zen_exit)
        self.zen_window.zen_saved_and_closed.connect(self.handle_zen_exit)
        self.zen_window.showFullScreen()

    def handle_zen_exit(self, note_id, text_from_zen):
        if self.zen_window:
            self.zen_window.close()
            self.zen_window = None
        
        saved_note_id = note_id
        
        if text_from_zen.strip():
            title = text_from_zen.split('\n', 1)[0].strip() or self.loc.get("unnamed_note_title")
            
            if note_id:
                self.db.update_note_content(note_id, title, text_from_zen)
            else:

                parent_id = self.last_selected_item_id
                saved_note_id = self.db.create_note(parent_id, title, text_from_zen)
        
        self.show()
        
        note_to_select = saved_note_id
        
        if self.zen_return_to_window_mode:
            self.show_main_window(note_to_select=note_to_select)
        else:
            self.show_main_popup(note_to_select=note_to_select)

    def update_settings(self, new_settings):
        self.settings = new_settings
        self.save_settings()
        self.update_position_and_style()
        
        if self.main_popup: 
            self.main_popup.apply_theme(new_settings)
            self.main_popup.retranslate_ui()
        if self.main_window: 
            self.main_window.apply_theme(new_settings)
            self.main_window.retranslate_ui()
        if self.zen_window: 
            self.zen_window.update_zen_settings(new_settings)
            
        if active_ui := self._choose_ui():
            if hasattr(active_ui, 'settings_panel_main') and active_ui.settings_panel_main.isVisible():
                active_ui.settings_panel_main.apply_styles()
                active_ui.settings_panel_main.retranslate_ui()

        
        self._restart_backup_timer()
        self.settings_changed.emit(self.settings)

    def create_backup(self, notify=False):
       
        db_file = self.db.db_path
        
        if not os.path.exists(db_file):
            print("Файл базы данных не найден. Бэкап не создан.")
            return

        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"assistant_{timestamp}.db.bak")
        try:
            shutil.copyfile(db_file, backup_path)
            if notify:
                active_window = QApplication.activeWindow() or self._choose_ui() or self
                
                msg_box = QMessageBox(active_window)
                msg_box.setWindowTitle(self.loc.get("backup_title"))
                msg_box.setText(self.loc.get("backup_created_success_popup"))
                msg_box.setIcon(QMessageBox.Icon.Information)
                
                dialog_style = get_global_dialog_stylesheet(self.get_settings())
                msg_box.setStyleSheet(dialog_style)
                
                msg_box.exec()
            else:
                print(self.loc.get("backup_creation_silent_success"))

            # Удаление старых бэкапов
            max_count = self.settings.get("backup_max_count", 10)
            all_backups = sorted(glob(os.path.join(BACKUP_DIR, "assistant_*.db.bak")))
            if len(all_backups) > max_count:
                for old_backup in all_backups[:-max_count]:
                    os.remove(old_backup)
                    print(f"Удален старый бэкап: {old_backup}")
        except Exception as e:
            print(f"Не удалось создать резервную копию: {e}")

    def restore_from_backup(self):
        active_window = QApplication.activeWindow() or self._choose_ui() or self
        dialog = BackupManagerDialog(active_window, self.loc)
        
        dialog_style = get_global_dialog_stylesheet(self.get_settings())

        dialog.setStyleSheet(dialog_style.replace("QMessageBox", "QDialog"))
        
        if dialog.exec():
            selected_file = dialog.selected_backup
            if not selected_file:
                return

            update_style_for_dialogs(self.get_settings())
            reply = QMessageBox.question(active_window, self.loc.get("restore_menu"), self.loc.get("backup_confirm_restore").format(date=dialog.get_date_from_filename(selected_file)))
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    db_file = self.db.db_path
                    if self.main_popup and self.main_popup.isVisible():
                        self.main_popup.close()
                    if self.main_window and self.main_window.isVisible():
                        self.main_window.close()
                    
                    shutil.copyfile(selected_file, db_file)
                    
                    update_style_for_dialogs(self.get_settings())
                    QMessageBox.information(active_window, self.loc.get("success_title"), self.loc.get("backup_restored_success"))
                    QApplication.instance().exit(123)
                except Exception as e:
                    update_style_for_dialogs(self.get_settings())
                    QMessageBox.critical(active_window, self.loc.get("error_title"), self.loc.get("backup_restore_error").format(error=e))

    def export_notes(self, scope="all", item=None):
        from PyQt6.QtCore import QMarginsF, QSizeF
        from PyQt6.QtGui import QPageLayout, QTextOption, QPageSize
        
        notes_to_export, default_filename = self._collect_notes_for_export(scope, item)

        if not notes_to_export:
            update_style_for_dialogs(self.get_settings())
            QMessageBox.information(self._choose_ui() or self, self.loc.get("export_menu"), self.loc.get("export_no_notes"))
            return

        update_style_for_dialogs(self.get_settings())
        export_dialog = ExportDialog(self._choose_ui() or self, self.settings)
        if not export_dialog.exec(): return
        
        file_format = export_dialog.get_selected_format()

        if file_format == 'md':
            filter_str = "Markdown Files (*.md);;Text Files (*.txt)"
            default_filename += ".md"
        else:
            filter_str = "PDF Files (*.pdf)"
            default_filename += ".pdf"
            
        path, _ = QFileDialog.getSaveFileName(self._choose_ui() or self, self.loc.get("export_notes_dialog_title"), default_filename, filter_str)
        if not path: return

        md_content = ""
        for note_data in notes_to_export:
            ts = note_data.get('created_at', 'N/A')
            text = note_data.get('content', '')
            md_content += f"## {self.loc.get('export_note_default_filename')} {ts}\n\n"
            md_content += f"{text}\n\n---\n\n"


        try:
            if file_format == 'md':
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(md_content)
            else: # PDF
                style_head = generate_markdown_css(self.settings, for_pdf=True)
                escaped_md = escape_markdown_tags(md_content)
                html_body = markdown.markdown(escaped_md, extensions=['fenced_code', 'tables', 'nl2br'])
                full_html = f"<html><head>{style_head}</head><body>{html_body}</body></html>"
                
                doc = QTextDocument()
                doc.setHtml(full_html)
                
                text_option = QTextOption()
                alignment_str = self.settings.get("zen_alignment", "left")
                alignment = Qt.AlignmentFlag.AlignJustify if alignment_str == "justify" else Qt.AlignmentFlag.AlignLeft
                text_option.setAlignment(alignment)
                doc.setDefaultTextOption(text_option)

                printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                printer.setOutputFileName(path)
                printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
                
                top = self.settings.get("pdf_margin_top", 20)
                bottom = self.settings.get("pdf_margin_bottom", 20)
                left = self.settings.get("pdf_margin_left", 15)
                right = self.settings.get("pdf_margin_right", 15)
                margins = QMarginsF(left, top, right, bottom)
                printer.setPageMargins(margins, QPageLayout.Unit.Millimeter)

                doc.print(printer)

            update_style_for_dialogs(self.get_settings())
            QMessageBox.information(self._choose_ui() or self, self.loc.get("success_title"), self.loc.get("export_file_success").format(path=path))
        except Exception as e:
            update_style_for_dialogs(self.get_settings())
            QMessageBox.critical(self._choose_ui() or self, self.loc.get("error_title"), self.loc.get("export_file_error").format(error=e))

    def _collect_notes_for_export(self, scope, item):
        all_notes_map = {note['id']: note for note in self.db.get_all_notes_flat()}
        notes_to_export = []
        default_filename = "export"

        if scope == "all":
            notes_to_export = list(all_notes_map.values())
            default_filename = self.loc.get("export_all_notes_default_filename")

        elif scope == "note" and item:
            note_data = item.data(0, Qt.ItemDataRole.UserRole)
            note_id = note_data.get("id")
            if note_id in all_notes_map:
                note_content_data = all_notes_map[note_id]
                notes_to_export.append(note_content_data)
                
                ts = note_content_data.get("created_at")
                if ts:
                    default_filename = f"{self.loc.get("export_note_default_filename")}_{ts.split(' ')[0]}"
                else:
                    default_filename = f"{self.loc.get("export_note_default_filename")}_{note_id}"

        elif scope == "folder" and item:
            folder_data = item.data(0, Qt.ItemDataRole.UserRole)
            default_filename = f"{self.loc.get("export_folder_default_filename")}_{folder_data.get('title', 'export')}"
            
            ids_in_folder = set()
            def collect_ids(parent_item):
                for i in range(parent_item.childCount()):
                    child = parent_item.child(i)
                    child_data = child.data(0, Qt.ItemDataRole.UserRole)
                    if child_data.get("type") == "note":
                        ids_in_folder.add(child_data.get("id"))
                    elif child_data.get("type") == "folder":
                        collect_ids(child)
            collect_ids(item)
            
            for note_id in ids_in_folder:
                if note_id in all_notes_map:
                    notes_to_export.append(all_notes_map[note_id])

        notes_to_export.sort(key=lambda x: x.get("created_at", ""), reverse=False)
        return notes_to_export, default_filename


    def export_settings_file(self):
        path, _ = QFileDialog.getSaveFileName(self, self.loc.get("export_settings"), "settings_export.json", "JSON (*.json)")
        if not path: return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
            QMessageBox.information(self, "OK", self.loc.get("settings_export_success"))
        except Exception as e:
            QMessageBox.critical(self, "error_title", self.loc.get("settings_export_error"))

    def import_settings_file(self):
        path, _ = QFileDialog.getOpenFileName(self, self.loc.get("import_settings"), "", "JSON (*.json)")
        if not path: return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                incoming = json.load(f)
            new_settings = DEFAULT_SETTINGS.copy()
            new_settings.update(self.settings)
            new_settings.update(incoming)
            self.update_settings(new_settings)
            QMessageBox.information(self, "OK", self.loc.get("settings_import_success"))
        except Exception as e:
            QMessageBox.critical(self, "error_title", self.get.loc("settings_import_error"))

    def show_about_dialog(self):
        if self.about_dialog is None:
            self.about_dialog = AboutDialog(self)
        screen = self.screen().geometry() if self.screen() else QApplication.primaryScreen().geometry()
        self.about_dialog.retranslate_ui()
        dlg_size = self.about_dialog.size()
        x = screen.x() + (screen.width() - dlg_size.width()) // 2
        y = screen.y() + (screen.height() - dlg_size.height()) // 2
        self.about_dialog.move(x, y)
        self.about_dialog.exec()

    def lock_application(self):
        """Блокирует приложение, "тихо" закрывая все окна."""
        self.is_locking = True
        self._unlocked = False 
        
        self.setEnabled(True)
        self.setWindowOpacity(1.0)
        self.hide()
        
        if self.main_popup and self.main_popup.isVisible(): self.main_popup.close()
        if self.main_window and self.main_window.isVisible(): self.main_window.close()
        if self.zen_window and self.zen_window.isVisible(): self.zen_window.close()
        
        self.is_locking = False

        if not self.db.is_password_set():
            self.show()
            return

        self._show_login_dialog()

    def unlock_application(self):
        """Разблокирует приложение, показывая скрытые окна."""

        if self.main_window: 
            self.main_window.show()
        elif self.main_popup:
            self.main_popup.show()
        
        self.show()

    def export_notes_to_folders(self):
        parent_widget = self._choose_ui() or self
        target_dir = QFileDialog.getExistingDirectory(parent_widget, self.loc.get("select_folder_to_export"))
        if not target_dir:
            return
        exporter = Exporter(self.db, self.loc)
        exporter.export_to_directory(target_dir, parent_widget)

    def import_notes_from_folders(self):
        """Запускает импорт заметок из структуры папок."""
        source_dir = QFileDialog.getExistingDirectory(self, self.loc.get("select_folder_to_import"))
        if not source_dir:
            return
            
        tree_data = self.db.get_note_tree()
        target_dialog = ImportTargetDialog(tree_data, self.db, self._choose_ui() or self, self.settings)
        
        if not target_dialog.exec():
            return
            
        parent_id = target_dialog.selected_parent_id
        
        importer = Importer(self.db, self.loc)
        if importer.import_from_directory(source_dir, parent_id):
            if active_ui := self._choose_ui():
                self.load_data_into_ui(active_ui)

    def export_one_folder(self, folder_item):
        """Экспортирует одну конкретную папку и ее содержимое."""
        target_dir = QFileDialog.getExistingDirectory(self, self.loc.get("select_folder_to_export"))
        if not target_dir: return
        
        folder_data = folder_item.data(0, Qt.ItemDataRole.UserRole)
        exporter = Exporter(self.db, self.loc)
        exporter.export_to_directory(target_dir, single_folder_data=folder_data)

    def import_files_here(self, parent_item):
        """Импортирует отдельные файлы в указанную папку."""
        parent_id = parent_item.data(0, Qt.ItemDataRole.UserRole).get('id') if parent_item else None
        
        files, _ = QFileDialog.getOpenFileNames(self, self.loc.get("import_files_dialog_title"), "", "Markdown/Text Files (*.md *.txt)")
        if not files: return
            
        importer = Importer(self.db, self.loc)
        if importer.import_files(files, parent_id):
            if active_ui := self._choose_ui():
                self.load_data_into_ui(active_ui)

    def _show_login_dialog(self):
        """Создает, показывает диалог входа и обрабатывает результат."""
        if not self.login_window:
            self.login_window = LoginWindow(self, self.loc_manager)
            self.login_window.login_successful.connect(self._on_unlock)
        
        self.login_window.password_input.clear()
        self.login_window.error_label.hide()
        
        result = self.login_window.exec()
        
        if not self._unlocked:
            QApplication.instance().quit()
    
    def _on_unlock(self):
        """Вызывается после успешного ввода пароля при разблокировке."""
        if self.login_window:
            self.login_window.accept()
        
        self._unlocked = True
        self.setEnabled(True)
        self.setWindowOpacity(1.0)

    def _is_any_window_visible(self):
        """Проверяет, видимо ли хотя бы одно из основных окон."""
        return ( (self.main_popup and self.main_popup.isVisible()) or
                 (self.main_window and self.main_window.isVisible()) )

class BackupManagerDialog(QDialog):
    def __init__(self, parent, loc):
        super().__init__(parent)
        self.loc = loc
        self.setWindowTitle(self.loc.get("backup_manager_title"))
        self.setMinimumSize(400, 300)
        self.selected_backup = None
        layout = QVBoxLayout(self)
        info_label = QLabel(self.loc.get("backup_available_copies"))
        self.backup_list_widget = QListWidget()
        button_layout = QHBoxLayout()
        self.restore_button = QPushButton(self.loc.get("backup_restore_btn"))
        self.delete_button = QPushButton(self.loc.get("backup_delete_btn"))
        self.cancel_button = QPushButton("Cancel")
        button_layout.addStretch()
        button_layout.addWidget(self.restore_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.cancel_button)
        layout.addWidget(info_label)
        layout.addWidget(self.backup_list_widget)
        layout.addLayout(button_layout)
        self.restore_button.clicked.connect(self.accept)
        self.delete_button.clicked.connect(self.delete_selected)
        self.cancel_button.clicked.connect(self.reject)
        self.backup_list_widget.itemSelectionChanged.connect(self.update_button_states)
        self.backup_list_widget.itemDoubleClicked.connect(self.accept)
        self.populate_backups()
        self.update_button_states()
        settings = parent.get_settings() if hasattr(parent, 'get_settings') else {}
        is_dark, accent, bg, text, _ = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border = "#555" if is_dark else "#ced4da"
        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; }} QLabel {{ color: {text}; }}
            QListWidget {{ background-color: {comp_bg}; border: 1px solid {border}; color: {text}; border-radius: 4px; }}
            QListWidget::item:selected {{ background-color: {accent}; }}
            QPushButton {{
                background-color: {comp_bg}; color: {text}; border: 1px solid {border};
                padding: 6px 12px; border-radius: 4px; min-width: 80px;
            }}
            QPushButton:hover {{ border-color: {accent}; }}
        """)

    def populate_backups(self):
        self.backup_list_widget.clear()
        if not os.path.exists(BACKUP_DIR):
            self.backup_list_widget.addItem(self.loc.get("backup_no_copies"))
            return
            
        backups = sorted(glob(os.path.join(BACKUP_DIR, "assistant_*.db.bak")), reverse=True)
        if not backups:
            self.backup_list_widget.addItem(self.loc.get("backup_no_copies"))
            return
        
        for backup_file in backups:
            item_text = self.get_date_from_filename(backup_file)
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, backup_file)
            self.backup_list_widget.addItem(item)
    
    def get_date_from_filename(self, filename):
        try:
            timestamp_str = os.path.basename(filename).replace("assistant_", "").replace(".db.bak", "")
            dt_obj = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            return dt_obj.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return os.path.basename(filename)

    def update_button_states(self):
        has_selection = bool(self.backup_list_widget.selectedItems())
        self.restore_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)
        
    def accept(self):
        if self.backup_list_widget.selectedItems():
            self.selected_backup = self.backup_list_widget.selectedItems()[0].data(Qt.ItemDataRole.UserRole)
            super().accept()
        
    def delete_selected(self):
        if not self.backup_list_widget.selectedItems(): return
        item = self.backup_list_widget.selectedItems()[0]
        file_path = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, self.loc.get("delete_note_tooltip"), self.loc.get("backup_confirm_delete"))
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(file_path); self.populate_backups(); self.update_button_states()
            except OSError as e: QMessageBox.critical(self, "error_title",  self.loc.get("delete_faied").format(error=e))
    
   

class ThemedIconProvider:
    SVG = {
        "play":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M8 5v14l11-7z'/></svg>", "pause":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M6 5h5v14H6V5zm7 0h5v14h-5V5z'/></svg>",
        "stop":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M6 6h12v12H6z'/></svg>", "prev":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M6 6h2v12H6zM9 12l9 6V6z'/></svg>",
        "next":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M16 6h2v12h-2zM6 18l9-6-9-6z'/></svg>", "chev_l":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M15.41 7.41 14 6l-6 6 6 6 1.41-1.41L10.83 12z'/></svg>",
        "chev_r": "<svg viewBox='0 0 24 24'><path fill='{c}' d='M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z'/></svg>",
        "add_file":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8m-6-6v6h6M11 10v3H8v2h3v3h2v-3h3v-2h-3v-3z'/></svg>",
        "add_folder":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M10 4H4a2 2 0 0 0-2 2v2h20V8a2 2 0 0 0-2-2h-8l-2-2m-8 6v8a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-8H2m10 2h2v3h3v2h-3v3h-2v-3H9v-2h3v-3z'/></svg>",
        "trash":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M9 3v1H4v2h16V4h-5V3H9m-3 6v11a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V9H6Z'/></svg>",
        "volume":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M5 9v6h4l5 4V5L9 9H5m12.5 3a4.5 4.5 0 0 0-3-4.24v8.48c1.76-.62 3-2.29 3-4.24Z'/></svg>",
        "volume_mute":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M12 4.44 9.77 6.67 12 8.9V4.44M4.27 3 3 4.27l6 6V14H3v-4H0v4h3v5h5l4 4V17.9l4.73 4.73L21 21.73 4.27 3M19 12a7 7 0 0 0-5-6.71v2.06A5 5 0 0 1 17 12a5 5 0 0 1-1 3l1.45 1.45A7 7 0 0 0 19 12Z'/></svg>",
        "gear":"<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='{c}' class='bi bi-gear' viewBox='0 0 16 16'><path d='M8 4.754a3.246 3.246 0 1 0 0 6.492 3.246 3.246 0 0 0 0-6.492M5.754 8a2.246 2.246 0 1 1 4.492 0 2.246 2.246 0 0 1-4.492 0'/><path d='M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 0 1-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 0 1-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 0 1 .52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 0 1 1.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 0 1 1.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 0 1 .52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 0 1-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 0 1-1.255-.52zm-2.633.283c.246-.835 1.428-.835 1.674 0l.094.319a1.873 1.873 0 0 0 2.693 1.115l.291-.16c.764-.415 1.6.42 1.184 1.185l-.159.292a1.873 1.873 0 0 0 1.116 2.692l.318.094c.835.246.835 1.428 0 1.674l-.319.094a1.873 1.873 0 0 0-1.115 2.693l.16.291c.415.764-.42 1.6-1.185 1.184l-.291-.159a1.873 1.873 0 0 0-2.693 1.116l-.094.318c-.246.835-1.428.835-1.674 0l-.094-.319a1.873 1.873 0 0 0-2.692-1.115l-.292.16c-.764.415-1.6-.42-1.184-1.185l.159-.291A1.873 1.873 0 0 0 1.945 8.93l-.319-.094c-.835-.246-.835-1.428 0-1.674l.319-.094A1.873 1.873 0 0 0 3.06 4.377l-.16-.292c-.415-.764.42-1.6 1.185-1.184l.292.159a1.873 1.873 0 0 0 2.692-1.115z'/></svg>",
        #"gear":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M12 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7ZM19.43 12.98c.04-.32.07-.65.07-.98s-.03-.66-.07-.98l2.11-1.65a.5.5 0 0 0 .12-.64l-2-3.46a.5.5 0 0 0-.6-.22l-2.49 1a7.05 7.05 0 0 0-1.7-.98l-.38-2.65A.5.5 0 0 0 12 1h-4a.5.5 0 0 0-.5.42l-.38 2.65a7.05 7.05 0 0 0-1.7-.98l-2.49-1a.5.5 0 0 0-.6.22l-2 3.46a.5.5 0 0 0 .12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98L.96 14.62a.5.5 0 0 0-.12.64l2 3.46a.5.5 0 0 0 .6.22l2.49-1c.52.4 1.09.73 1.7.98l.38 2.65A.5.5 0 0 0 8 23h4a.5.5 0 0 0 .5-.42l.38-2.65c.61-.25 1.18-.58 1.7-.98l2.49 1a.5.5 0 0 0 .6-.22l2-3.46a.5.5 0 0 0-.12-.64l-2.11-1.64Z'/></svg>",
        "window":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Zm1 3h14v9H5V8Z'/></svg>",
        "note":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M12 3v10.55A4 4 0 1 0 14 17V7h4V3h-6Z'/></svg>",
        "close":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12Z'/></svg>",
        "folder":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M10 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-8l-2-2z'/></svg>",
        "file":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z M13 9V3.5L18.5 9H13z'/></svg>",
        "pin":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z'/></svg>",
        "eye":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z'/></svg>",
        "edit_pencil":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34a.9959.9959 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z'/></svg>",
        "minimize": "<svg viewBox='0 0 24 24'><path fill='{c}' d='M20 14H4v-4h16v4z'/></svg>",
        "maximize": "<svg viewBox='0 0 24 24'><path fill='{c}' d='M4 4h16v16H4V4zm2 4v10h12V8H6z'/></svg>",
        "restore":  "<svg viewBox='0 0 24 24'><path fill='{c}' d='M4 8h4V4h12v12h-4v4H4V8zm12-2H8v2H6v10h10v-2h2V6h-2V6z'/></svg>",
        "resize_grip": "<svg viewBox='0 0 10 10'><path fill='{c}' d='M 0 10 L 10 0 L 10 2 L 2 10 Z M 4 10 L 10 4 L 10 6 L 6 10 Z M 8 10 L 10 8 L 10 10 Z'/></svg>",
    }
    @staticmethod
    def icon(name: str, settings: dict, size: QSize = QSize(18, 18)) -> QIcon:
        svg = ThemedIconProvider.SVG.get(name)
        if not svg: return QIcon()
        is_dark = settings.get("theme") == "dark"
        color = settings.get("dark_theme_text") if is_dark else settings.get("light_theme_text")
        data = svg.replace("{c}", color)
        renderer = QSvgRenderer(bytearray(data, encoding="utf-8"))
        pm = QPixmap(size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        renderer.render(p)
        p.end()
        return QIcon(pm)

# --- Точка входа ---
def main():

    flag_file = os.path.join(
        os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__)),
        "_reset.flag"
    )
    db_file = os.path.join(os.path.dirname(flag_file), "assistant.db")

    if os.path.exists(flag_file):
        try:
            if os.path.exists(db_file):
                os.remove(db_file)
                print("Файл базы данных успешно удален.")
            os.remove(flag_file)
            print("Файл-флаг сброса удален.")
        except Exception as e:
            print(f"Ошибка при сбросе данных перед запуском: {e}")
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    loc_manager = LocalizationManager()
    
    trigger = TriggerButton(loc_manager)
    db = trigger.db

    login_required = db.is_password_set()
    
    if login_required:
        trigger._show_login_dialog()

    else:

        trigger._unlocked = True

    if trigger._unlocked:
        startup_mode = trigger.get_settings().get("startup_mode", "panel")
        
        if startup_mode == "window":
            trigger.show_main_window()
        else: # "panel"
            trigger.show()
  
    exit_code = app.exec()
    if exit_code == 123:
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv)
    else:
        sys.exit(exit_code)

if __name__ == "__main__":
    main()