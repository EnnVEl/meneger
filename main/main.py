# main.py
import sys
import json
import os
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from functools import partial

# Константы
SAVE_FILE = "savegame.json"
SONGS_FOLDER = "songs"
BACKGROUND_MUSIC = os.path.join(SONGS_FOLDER, "background.mp3")
MENU_SOUND = os.path.join(SONGS_FOLDER, "menu_music.wav")

DEFAULT_SETTINGS = {
    "bg_color": "#2b2b2b",
    "text_color": "#ffffff",
    "table_color": "#3c3c3c",
    "music_volume": 50,
    "sound_effects": True
}

class Task:
    def __init__(self, name="", reward=0, status=False, deadline=""):
        self.name = name
        self.reward = reward
        self.status = status
        self.deadline = deadline

    def to_dict(self):
        return {"name": self.name, "reward": self.reward, "status": self.status, "deadline": self.deadline}

class StoreItem:
    def __init__(self, icon="😊", name="", cost=0):
        self.icon = icon
        self.name = name
        self.cost = cost

    def to_dict(self):
        return {"icon": self.icon, "name": self.name, "cost": self.cost}

class DataManager:
    @staticmethod
    def load_data():
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        return {"tasks": [], "completed": [], "store": [], "temp_tasks": [], "balance": 0, "settings": DEFAULT_SETTINGS.copy()}

    @staticmethod
    def save_data(data):
        with open(SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

class DraggableTable(QTableWidget):
    def __init__(self, parent, task_type="active"):
        super().__init__(parent)
        self.parent = parent
        self.task_type = task_type
        self.drag_row = -1
        self.setup_ui()
        self.load_tasks()
        
    def setup_ui(self):
        if self.task_type == "temp":
            self.setColumnCount(4)
            self.setHorizontalHeaderLabels(["Задания", "Награда", "Статус", "Время"])
        else:
            self.setColumnCount(3)
            self.setHorizontalHeaderLabels(["Задания", "Награда", "Статус"])
        
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().setVisible(True)
        self.verticalHeader().setDefaultSectionSize(40)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTableWidget.InternalMove)
        
        # Делаем первую колонку с индикатором перетаскивания
        self.verticalHeader().setSectionsMovable(True)
        
        self.cellClicked.connect(self.on_cell_clicked)
        self.cellDoubleClicked.connect(self.on_cell_double_clicked)
        
    def get_task_list(self):
        if self.task_type == "active":
            return self.parent.data["tasks"]
        elif self.task_type == "completed":
            return self.parent.data["completed"]
        elif self.task_type == "temp":
            return self.parent.data["temp_tasks"]
        return []

    def load_tasks(self):
        self.clearContents()
        tasks = self.get_task_list()
        self.setRowCount(len(tasks) + 1)  # +1 для пустой строки
        
        for i, task in enumerate(tasks):
            self.setItem(i, 0, QTableWidgetItem(task["name"]))
            self.setItem(i, 1, QTableWidgetItem(str(task["reward"])))
            status_item = QTableWidgetItem("✅" if task["status"] else "☐")
            status_item.setTextAlignment(Qt.AlignCenter)
            self.setItem(i, 2, status_item)
            
            if self.task_type == "temp" and "deadline" in task:
                self.setItem(i, 3, QTableWidgetItem(task.get("deadline", "")))
            
            if self.task_type == "completed":
                for col in range(self.columnCount()):
                    item = self.item(i, col)
                    if item:
                        item.setBackground(QColor("#4a4a4a"))
        
        # Пустая строка для создания нового задания
        empty_row = len(tasks)
        for col in range(self.columnCount()):
            item = QTableWidgetItem("")
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.setItem(empty_row, col, item)

    def on_cell_clicked(self, row, col):
        tasks = self.get_task_list()
        if row >= len(tasks):
            return  # Пустая строка
            
        if col == 2 and self.task_type in ["active", "temp"]:
            self.complete_task(row)
            
    def on_cell_double_clicked(self, row, col):
        tasks = self.get_task_list()
        if row >= len(tasks):
            self.create_new_task(row)
        elif col in (0, 1) and self.task_type in ["active", "temp"]:
            self.edit_cell(row, col)

    def create_new_task(self, row):
        if self.task_type == "temp":
            dialog = QDialog(self)
            dialog.setWindowTitle("Новое временное задание")
            layout = QVBoxLayout(dialog)
            
            name_edit = QLineEdit()
            reward_edit = QLineEdit("0")
            deadline_edit = QDateTimeEdit()
            deadline_edit.setCalendarPopup(True)
            deadline_edit.setDateTime(QDateTime.currentDateTime().addDays(1))
            
            layout.addWidget(QLabel("Название:"))
            layout.addWidget(name_edit)
            layout.addWidget(QLabel("Награда:"))
            layout.addWidget(reward_edit)
            layout.addWidget(QLabel("Дедлайн:"))
            layout.addWidget(deadline_edit)
            
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            
            if dialog.exec_():
                task = Task(
                    name_edit.text() or "Новое задание",
                    int(reward_edit.text()) if reward_edit.text().isdigit() else 0,
                    False,
                    deadline_edit.dateTime().toString("dd.MM.yyyy HH:mm")
                ).to_dict()
                self.parent.data["temp_tasks"].append(task)
                DataManager.save_data(self.parent.data)
                self.parent.update_all_tables()
                self.parent.play_sound()
        else:
            task = Task("Новое задание", 0, False).to_dict()
            self.parent.data["tasks"].append(task)
            DataManager.save_data(self.parent.data)
            self.parent.update_all_tables()
            self.parent.play_sound()

    def edit_cell(self, row, col):
        tasks = self.get_task_list()
        task = tasks[row]
        current_value = task["name"] if col == 0 else str(task["reward"])
        new_value, ok = QInputDialog.getText(self, "Редактировать", "Введите новое значение:", text=current_value)
        if ok and new_value:
            if col == 0:
                task["name"] = new_value
            else:
                try:
                    task["reward"] = int(new_value)
                except:
                    pass
            DataManager.save_data(self.parent.data)
            self.load_tasks()

    def complete_task(self, row):
        tasks = self.get_task_list()
        task = tasks[row]
        if not task["status"]:
            task["status"] = True
            self.parent.data["balance"] += task["reward"]
            reward_text = f"+{task['reward']}" if task['reward'] >= 0 else str(task['reward'])
            QMessageBox.information(self, "Поздравляем!", f"Молодец, вот твоя награда: {reward_text} баллов!")
            
            # Добавляем в завершенные
            completed_task = task.copy()
            completed_task["status"] = True
            self.parent.data["completed"].append(completed_task)
            
            # Удаляем из текущего списка
            del tasks[row]
            DataManager.save_data(self.parent.data)
            self.parent.update_all_tables()
            self.parent.update_balance()
            self.parent.play_sound()

    def dropEvent(self, event):
        super().dropEvent(event)
        # Сохраняем новый порядок
        tasks = self.get_task_list()
        new_order = []
        for row in range(self.rowCount() - 1):  # -1 для пустой строки
            if row < len(tasks):
                new_order.append(tasks[row])
        
        if self.task_type == "active":
            self.parent.data["tasks"] = new_order
        elif self.task_type == "temp":
            self.parent.data["temp_tasks"] = new_order
        elif self.task_type == "completed":
            self.parent.data["completed"] = new_order
            
        DataManager.save_data(self.parent.data)

class StoreGrid(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.layout = QGridLayout(self)
        self.layout.setSpacing(10)
        self.load_store_items()

    def load_store_items(self):
        self.clear_layout()
        store_items = self.parent.data["store"]
        for i, item in enumerate(store_items):
            btn = QPushButton(item["icon"])
            btn.setFixedSize(80, 80)
            btn.setStyleSheet("""
                font-size: 30px; 
                background-color: %s; 
                border: 2px solid #555; 
                border-radius: 10px;
                color: %s;
            """ % (self.parent.data["settings"]["table_color"], self.parent.data["settings"]["text_color"]))
            btn.clicked.connect(partial(self.add_task_from_store, i))
            btn.installEventFilter(self)
            btn.setProperty("index", i)
            self.layout.addWidget(btn, i // 4, i % 4)
        
        # Кнопка добавления
        add_btn = QPushButton("+")
        add_btn.setFixedSize(80, 80)
        add_btn.setStyleSheet("""
            font-size: 30px; 
            background-color: %s; 
            border: 2px solid #555; 
            border-radius: 10px;
            color: %s;
        """ % (self.parent.data["settings"]["table_color"], self.parent.data["settings"]["text_color"]))
        add_btn.clicked.connect(self.add_store_item)
        self.layout.addWidget(add_btn, len(self.parent.data["store"]) // 4, len(self.parent.data["store"]) % 4)

    def clear_layout(self):
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self.press_time = QDateTime.currentDateTime()
            self.press_pos = event.pos()
        elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            if self.press_time.msecsTo(QDateTime.currentDateTime()) > 1500:
                index = obj.property("index")
                if index is not None:
                    self.edit_store_item(index)
                    return True
        return super().eventFilter(obj, event)

    def add_store_item(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Новое задание магазина")
        layout = QVBoxLayout(dialog)
        icon_edit = QLineEdit("😊")
        name_edit = QLineEdit("Новое задание")
        cost_edit = QLineEdit("10")
        layout.addWidget(QLabel("Иконка:"))
        layout.addWidget(icon_edit)
        layout.addWidget(QLabel("Название:"))
        layout.addWidget(name_edit)
        layout.addWidget(QLabel("Стоимость:"))
        layout.addWidget(cost_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec_():
            item = StoreItem(icon_edit.text() or "😊", name_edit.text() or "Новое задание", int(cost_edit.text()) if cost_edit.text().isdigit() else 10).to_dict()
            self.parent.data["store"].append(item)
            DataManager.save_data(self.parent.data)
            self.load_store_items()
            self.parent.play_sound()

    def edit_store_item(self, index):
        item = self.parent.data["store"][index]
        dialog = QDialog(self)
        dialog.setWindowTitle("Редактировать задание")
        layout = QVBoxLayout(dialog)
        icon_edit = QLineEdit(item["icon"])
        name_edit = QLineEdit(item["name"])
        cost_edit = QLineEdit(str(item["cost"]))
        layout.addWidget(QLabel("Иконка:"))
        layout.addWidget(icon_edit)
        layout.addWidget(QLabel("Название:"))
        layout.addWidget(name_edit)
        layout.addWidget(QLabel("Стоимость:"))
        layout.addWidget(cost_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Delete)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        buttons.button(QDialogButtonBox.Delete).clicked.connect(lambda: self.delete_store_item(index, dialog))
        layout.addWidget(buttons)
        if dialog.exec_():
            self.parent.data["store"][index] = StoreItem(
                icon_edit.text() or "😊", 
                name_edit.text() or "Новое задание", 
                int(cost_edit.text()) if cost_edit.text().isdigit() else 10
            ).to_dict()
            DataManager.save_data(self.parent.data)
            self.load_store_items()
            self.parent.play_sound()

    def delete_store_item(self, index, dialog):
        del self.parent.data["store"][index]
        DataManager.save_data(self.parent.data)
        dialog.reject()
        self.load_store_items()
        self.parent.play_sound()

    def add_task_from_store(self, index):
        item = self.parent.data["store"][index]
        self.parent.data["tasks"].append(Task(item["name"], -item["cost"], False).to_dict())
        DataManager.save_data(self.parent.data)
        self.parent.update_all_tables()
        self.parent.play_sound()

class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Настройки")
        self.setFixedSize(500, 700)
        layout = QVBoxLayout(self)
        
        # Цвета
        layout.addWidget(QLabel("Цвет фона:"))
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setStyleSheet(f"background-color: {parent.data['settings']['bg_color']}")
        self.bg_color_btn.clicked.connect(lambda: self.choose_color("bg_color"))
        layout.addWidget(self.bg_color_btn)
        
        layout.addWidget(QLabel("Цвет текста:"))
        self.text_color_btn = QPushButton()
        self.text_color_btn.setStyleSheet(f"background-color: {parent.data['settings']['text_color']}")
        self.text_color_btn.clicked.connect(lambda: self.choose_color("text_color"))
        layout.addWidget(self.text_color_btn)
        
        layout.addWidget(QLabel("Цвет таблиц:"))
        self.table_color_btn = QPushButton()
        self.table_color_btn.setStyleSheet(f"background-color: {parent.data['settings']['table_color']}")
        self.table_color_btn.clicked.connect(lambda: self.choose_color("table_color"))
        layout.addWidget(self.table_color_btn)
        
        # Звук
        layout.addWidget(QLabel("Громкость музыки:"))
        self.music_slider = QSlider(Qt.Horizontal)
        self.music_slider.setRange(0, 100)
        self.music_slider.setValue(parent.data["settings"]["music_volume"])
        self.music_slider.valueChanged.connect(self.change_volume)
        self.music_slider.mousePressEvent = self.slider_click
        layout.addWidget(self.music_slider)
        
        self.sound_check = QCheckBox("Звуковые эффекты")
        self.sound_check.setChecked(parent.data["settings"]["sound_effects"])
        self.sound_check.stateChanged.connect(self.toggle_sound)
        layout.addWidget(self.sound_check)
        
        # Кнопка сброса
        reset_btn = QPushButton("Сбросить все настройки")
        reset_btn.setStyleSheet("background-color: #8B0000; color: white; padding: 10px;")
        reset_btn.clicked.connect(self.reset_all)
        layout.addWidget(reset_btn)
        
        layout.addStretch()

    def slider_click(self, event):
        # Перемещаем ползунок в место клика
        value = self.music_slider.minimum() + (self.music_slider.maximum() - self.music_slider.minimum()) * event.x() / self.music_slider.width()
        self.music_slider.setValue(int(value))
        self.change_volume(int(value))

    def choose_color(self, setting):
        color = QColorDialog.getColor(QColor(self.parent.data["settings"][setting]))
        if color.isValid():
            self.parent.data["settings"][setting] = color.name()
            getattr(self, f"{setting}_btn").setStyleSheet(f"background-color: {color.name()}")
            self.parent.apply_settings()
            DataManager.save_data(self.parent.data)

    def change_volume(self, value):
        self.parent.data["settings"]["music_volume"] = value
        self.parent.music_player.player.setVolume(value)
        DataManager.save_data(self.parent.data)

    def toggle_sound(self, state):
        self.parent.data["settings"]["sound_effects"] = bool(state)
        DataManager.save_data(self.parent.data)

    def reset_all(self):
        reply = QMessageBox.question(self, "Сброс", "Сбросить все настройки и баланс?", 
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.parent.data["settings"] = DEFAULT_SETTINGS.copy()
            self.parent.data["balance"] = 0
            self.parent.data["tasks"] = []
            self.parent.data["completed"] = []
            self.parent.data["store"] = []
            self.parent.data["temp_tasks"] = []
            DataManager.save_data(self.parent.data)
            self.parent.apply_settings()
            self.parent.update_all_tables()
            self.parent.update_balance()
            self.close()

class MusicPlayer(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.player = QMediaPlayer()
        self.playlist = []
        self.current_index = 0
        self.load_songs()
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setFixedSize(40, 40)
        self.prev_btn.clicked.connect(self.prev_song)
        layout.addWidget(self.prev_btn)
        
        self.play_btn = QPushButton("⏸")
        self.play_btn.setFixedSize(40, 40)
        self.play_btn.clicked.connect(self.toggle_play)
        layout.addWidget(self.play_btn)
        
        self.next_btn = QPushButton("⏭")
        self.next_btn.setFixedSize(40, 40)
        self.next_btn.clicked.connect(self.next_song)
        layout.addWidget(self.next_btn)
        
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        if self.playlist:
            self.play_song(0)

    def load_songs(self):
        if os.path.exists(SONGS_FOLDER):
            for file in sorted(os.listdir(SONGS_FOLDER)):
                if file.startswith("background") and file.endswith(".mp3"):
                    self.playlist.append(os.path.join(SONGS_FOLDER, file))

    def play_song(self, index):
        if 0 <= index < len(self.playlist):
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(self.playlist[index])))
            self.player.setVolume(self.parent.data["settings"]["music_volume"])
            self.player.play()
            self.current_index = index

    def toggle_play(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.play_btn.setText("▶")
        else:
            self.player.play()
            self.play_btn.setText("⏸")

    def next_song(self):
        if self.playlist:
            self.play_song((self.current_index + 1) % len(self.playlist))

    def prev_song(self):
        if self.playlist:
            self.play_song((self.current_index - 1) % len(self.playlist))

    def on_media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.next_song()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data = DataManager.load_data()
        self.initUI()
        self.apply_settings()
        self.update_balance()
        self.sound_player = QMediaPlayer()

    def initUI(self):
        self.setWindowTitle("Менеджер заданий")
        self.setGeometry(100, 100, 1000, 800)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Верхняя панель
        top_panel = QHBoxLayout()
        self.balance_label = QLabel("Баланс: 0")
        self.balance_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 5px;")
        top_panel.addStretch()
        top_panel.addWidget(self.balance_label)
        
        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(45, 45)
        settings_btn.setStyleSheet("font-size: 20px;")
        settings_btn.clicked.connect(self.open_settings)
        top_panel.addWidget(settings_btn)
        main_layout.addLayout(top_panel)
        
        # Музыкальный плеер
        self.music_player = MusicPlayer(self)
        main_layout.addWidget(self.music_player)
        
        # Вкладки
        self.tabs = QTabWidget()
        self.tasks_tab = QWidget()
        self.completed_tab = QWidget()
        self.store_tab = QWidget()
        self.temp_tab = QWidget()
        self.tabs.addTab(self.tasks_tab, "Задания")
        self.tabs.addTab(self.completed_tab, "Завершённые задания")
        self.tabs.addTab(self.store_tab, "Магазин")
        self.tabs.addTab(self.temp_tab, "Временные задания")
        main_layout.addWidget(self.tabs)
        
        # Вкладка Задания
        tasks_layout = QVBoxLayout(self.tasks_tab)
        self.task_table = DraggableTable(self, "active")
        tasks_layout.addWidget(self.task_table)
        
        # Кнопки навигации
        nav_layout = QHBoxLayout()
        nav_layout.addStretch()
        nav_buttons = QVBoxLayout()
        up_btn = QPushButton("▲")
        up_btn.setFixedSize(40, 30)
        up_btn.clicked.connect(lambda: self.scroll_table(self.task_table, -1))
        down_btn = QPushButton("▼")
        down_btn.setFixedSize(40, 30)
        down_btn.clicked.connect(lambda: self.scroll_table(self.task_table, 1))
        nav_buttons.addWidget(up_btn)
        nav_buttons.addWidget(down_btn)
        nav_layout.addLayout(nav_buttons)
        tasks_layout.addLayout(nav_layout)
        
        # Вкладка Завершённые
        completed_layout = QVBoxLayout(self.completed_tab)
        self.completed_table = DraggableTable(self, "completed")
        completed_layout.addWidget(self.completed_table)
        
        # Вкладка Магазин
        store_layout = QVBoxLayout(self.store_tab)
        self.store_grid = StoreGrid(self)
        store_layout.addWidget(self.store_grid)
        
        # Вкладка Временные задания
        temp_layout = QVBoxLayout(self.temp_tab)
        self.temp_table = DraggableTable(self, "temp")
        temp_layout.addWidget(self.temp_table)
        
        # Кнопки навигации для временных заданий
        temp_nav_layout = QHBoxLayout()
        temp_nav_layout.addStretch()
        temp_nav_buttons = QVBoxLayout()
        temp_up_btn = QPushButton("▲")
        temp_up_btn.setFixedSize(40, 30)
        temp_up_btn.clicked.connect(lambda: self.scroll_table(self.temp_table, -1))
        temp_down_btn = QPushButton("▼")
        temp_down_btn.setFixedSize(40, 30)
        temp_down_btn.clicked.connect(lambda: self.scroll_table(self.temp_table, 1))
        temp_nav_buttons.addWidget(temp_up_btn)
        temp_nav_buttons.addWidget(temp_down_btn)
        temp_nav_layout.addLayout(temp_nav_buttons)
        temp_layout.addLayout(temp_nav_layout)

    def scroll_table(self, table, direction):
        current = table.verticalScrollBar().value()
        step = 40  # Высота строки
        table.verticalScrollBar().setValue(current + direction * step * 3)

    def update_all_tables(self):
        self.task_table.load_tasks()
        self.completed_table.load_tasks()
        self.temp_table.load_tasks()
        self.store_grid.load_store_items()

    def update_balance(self):
        self.balance_label.setText(f"Баланс: {self.data['balance']}")

    def apply_settings(self):
        settings = self.data["settings"]
        style = f"""
            QMainWindow {{ background-color: {settings['bg_color']}; }}
            QLabel, QTabWidget, QWidget, QPushButton {{
                color: {settings['text_color']};
            }}
            QTableWidget {{
                background-color: {settings['table_color']};
                color: {settings['text_color']};
                gridline-color: {settings['text_color']};
            }}
            QHeaderView::section {{
                background-color: {settings['table_color']};
                color: {settings['text_color']};
                padding: 5px;
            }}
            QPushButton {{
                background-color: {settings['table_color']};
                border: 1px solid {settings['text_color']};
                border-radius: 5px;
                padding: 5px;
            }}
            QPushButton:hover {{
                background-color: {settings['text_color']};
                color: {settings['table_color']};
            }}
            QTabWidget::pane {{
                background-color: {settings['bg_color']};
                border: 1px solid {settings['text_color']};
            }}
            QTabBar::tab {{
                background-color: {settings['table_color']};
                color: {settings['text_color']};
                padding: 8px 15px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {settings['text_color']};
                color: {settings['table_color']};
            }}
            QDialog {{
                background-color: {settings['bg_color']};
            }}
            QLineEdit, QDateTimeEdit {{
                background-color: {settings['table_color']};
                color: {settings['text_color']};
                padding: 5px;
                border: 1px solid {settings['text_color']};
                border-radius: 3px;
            }}
        """
        self.setStyleSheet(style)

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

    def play_sound(self):
        if self.data["settings"]["sound_effects"] and os.path.exists(MENU_SOUND):
            self.sound_player.setMedia(QMediaContent(QUrl.fromLocalFile(MENU_SOUND)))
            self.sound_player.setVolume(50)
            self.sound_player.play()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
