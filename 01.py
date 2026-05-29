# pip install pyqt6 plyer
import sys
import json
import sqlite3
import os
from datetime import datetime, date
from threading import Timer
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget, QPushButton, QHBoxLayout, QMessageBox, QComboBox, QDialog, QLabel, QDialogButtonBox,
    QHeaderView, QStyleFactory, QStyledItemDelegate, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QPalette
from plyer import notification

# روزهای هفته به پارسی
days_fa = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه']

# ساعت‌ها از 9 تا 23
hours = list(range(9, 24))

# فایل دیتابیس (SQLite)
db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'class_schedule.db')


# ایجاد دیتابیس و جدول اگر وجود نداشته باشد
def init_db():
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedule (
            day TEXT,
            hour INTEGER,
            class_name TEXT,
            PRIMARY KEY (day, hour)
        )
    ''')
    conn.commit()
    conn.close()


# بارگذاری برنامه از دیتابیس
def load_schedule_from_db():
    class_schedule = {day: {hour: '' for hour in hours} for day in days_fa}
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('SELECT day, hour, class_name FROM schedule')
    rows = cursor.fetchall()
    for day, hour, class_name in rows:
        if day in class_schedule and hour in class_schedule[day]:
            class_schedule[day][hour] = class_name
    conn.close()
    return class_schedule


# ذخیره برنامه در دیتابیس
def save_schedule_to_db(class_schedule):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    for day in days_fa:
        for hour in hours:
            cursor.execute('''
                INSERT OR REPLACE INTO schedule (day, hour, class_name)
                VALUES (?, ?, ?)
            ''', (day, hour, class_schedule[day][hour]))
    conn.commit()
    conn.close()


# فایل تنظیمات برای روز هفته
config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

# بارگذاری تنظیمات
config = {}
try:
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
except FileNotFoundError:
    pass


# تابع برای محاسبه روز فعلی بر اساس config
def get_current_day_fa():
    if not config:
        return None
    last_date_str = config.get('last_date')
    saved_day_fa = config.get('day_fa')
    if not last_date_str or not saved_day_fa:
        return None
    last_date = datetime.strptime(last_date_str, '%Y-%m-%d').date()
    current_date = date.today()
    days_diff = (current_date - last_date).days % 7
    day_index = days_fa.index(saved_day_fa)
    current_index = (day_index + days_diff) % 7
    return days_fa[current_index]


# نقشه روزهای انگلیسی به پارسی
day_map = {
    'Saturday': 'شنبه',
    'Sunday': 'یکشنبه',
    'Monday': 'دوشنبه',
    'Tuesday': 'سه‌شنبه',
    'Wednesday': 'چهارشنبه',
    'Thursday': 'پنجشنبه',
    'Friday': 'جمعه'
}


# تابع برای پیدا کردن کلاس بعدی
def get_next_class(class_schedule):
    current_day_fa = get_current_day_fa()
    if not current_day_fa:
        now = datetime.now()
        current_day_fa = day_map.get(now.strftime('%A'), 'نامعلوم')
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    if current_hour >= 23:
        return "کلاس‌ها برای امروز تمام شده. فردا چک کنید."
    for hour in range(max(current_hour, 9), 24):
        if hour in class_schedule.get(current_day_fa, {}) and class_schedule[current_day_fa][hour]:
            if hour > current_hour or (hour == current_hour and current_minute < 5):
                return f"ساعت بعدی: {class_schedule[current_day_fa][hour]} در {hour}:00"
    return "هیچ کلاس بعدی امروز نیست."


# تابع برای ارسال نوتیفیکیشن سیستم عامل
def send_notification(class_schedule):
    next_class = get_next_class(class_schedule)
    notification.notify(
        title='یادآوری کلاس',
        message=next_class,
        app_icon=None,
        timeout=10,
    )


# کلاس دیالوگ برای تنظیم روز
class DayConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تنظیم روز فعلی")
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; border: 1px solid #ccc; border-radius: 8px; }
            QLabel { font-size: 14px; color: #333; }
            QComboBox { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
            QPushButton { background-color: #2196F3; color: white; padding: 8px 16px; border: none; border-radius: 4px; }
            QPushButton:hover { background-color: #1976D2; }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        label = QLabel("روز فعلی هفته را انتخاب کنید (چون ممکن است با سیستم متفاوت باشد):")
        layout.addWidget(label)
        self.combo = QComboBox()
        self.combo.addItems(days_fa)
        layout.addWidget(self.combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_day(self):
        return self.combo.currentText()


# delegate برای کنترل فونت editor هنگام ویرایش
class FontDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        font = editor.font()
        font.setPointSize(12)
        editor.setFont(font)
        editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return editor


# کلاس اصلی برنامه
class ClassScheduleApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("برنامه کلاس‌ها - حرفه‌ای و مدرن")
        self.setGeometry(100, 100, 1200, 800)

        # تنظیم تم حرفه‌ای
        app = QApplication.instance()
        app.setStyle(QStyleFactory.create('Fusion'))
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(33, 33, 33))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.Text, QColor(33, 33, 33))
        palette.setColor(QPalette.ColorRole.Button, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(33, 33, 33))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(33, 150, 243))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        app.setPalette(palette)

        self.setStyleSheet("""
            QMainWindow { background-color: #f5f5f5; font-family: 'Segoe UI', Arial; font-size: 13px; }
            QTableWidget {
                background-color: white;
                gridline-color: #e0e0e0;
                border: 1px solid #ddd;
                border-radius: 8px;
                selection-background-color: #bbdefb;
            }
            QHeaderView::section {
                background-color: #e3f2fd;
                padding: 10px;
                font-weight: bold;
                border-bottom: 1px solid #ddd;
                color: #1565c0;
                font-size: 10px;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1976D2; }
            QPushButton:pressed { background-color: #0d47a1; }
            QMessageBox { background-color: #ffffff; border: 1px solid #ccc; border-radius: 8px; }
            QLabel#next_class_label {
                font-size: 20px;
                font-weight: bold;
                color: #d32f2f;
                background-color: #ffebee;
                padding: 15px;
                border-radius: 8px;
                border: 1px solid #ef9a9a;
            }
        """)
        # ابتدایی‌سازی دیتابیس
        init_db()
        # بارگذاری برنامه
        self.class_schedule = load_schedule_from_db()
        # چک تنظیم اولیه
        self.configure_day_if_needed()
        # ویجت مرکزی
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        # label برای نمایش کلاس بعدی (همیشه حاضر)
        self.next_class_label = QLabel(get_next_class(self.class_schedule), self)
        self.next_class_label.setObjectName("next_class_label")
        self.next_class_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.next_class_label)
        # جدول
        self.table = QTableWidget(len(hours), len(days_fa))
        self.table.setHorizontalHeaderLabels(days_fa)
        self.table.setVerticalHeaderLabels([f"{h}:00" for h in hours])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setFont(QFont('Segoe UI', 12))
        self.table.setItemDelegate(FontDelegate())  # تنظیم delegate برای editor
        layout.addWidget(self.table)
        # پر کردن جدول
        self.populate_table()
        # فقط یک دکمه: ذخیره
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        save_btn = QPushButton("ذخیره تغییرات")
        save_btn.clicked.connect(self.save_schedule)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        # آپدیت label هر دقیقه و نوتیفیکیشن
        self.update_next_class_label()
        Timer(60, self.update_timer).start()
        # اتصال resize event برای تغییر دینامیک فونت
        self.table.resizeEvent = self.on_table_resize

    def on_table_resize(self, event):
        # ارتفاع هر ردیف
        row_height = max(20, self.table.viewport().height() // len(hours) - 2)
        for row in range(len(hours)):
            self.table.setRowHeight(row, row_height)
        # تنظیم فونت دینامیک
        font_size = max(10, row_height // 3)
        font = QFont('Segoe UI', font_size)
        self.table.setFont(font)
        QTableWidget.resizeEvent(self.table, event)

    def update_next_class_label(self):
        self.next_class_label.setText(get_next_class(self.class_schedule))
        send_notification(self.class_schedule)

    def update_timer(self):
        self.update_next_class_label()
        Timer(60, self.update_timer).start()

    def configure_day_if_needed(self):
        global config
        if not config:
            dialog = DayConfigDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_day = dialog.get_day()
                config = {
                    'last_date': date.today().strftime('%Y-%m-%d'),
                    'day_fa': selected_day
                }
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "تنظیم", "روز فعلی تنظیم شد.")
            else:
                QMessageBox.warning(self, "هشدار", "بدون تنظیم روز، از روز سیستم استفاده می‌شود.")

    def save_schedule(self):
        self.update_schedule_from_table()
        save_schedule_to_db(self.class_schedule)
        path = os.path.abspath(db_file)
        QMessageBox.information(self, "ذخیره", f"تغییرات با موفقیت ذخیره شد در دیتابیس:\n{path}")
        print(f"ذخیره موفق در: {path}")

    def populate_table(self):
        for col, day in enumerate(days_fa):
            for row, hour in enumerate(hours):
                item = QTableWidgetItem(self.class_schedule.get(day, {}).get(hour, ''))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)

    def update_schedule_from_table(self):
        for col, day in enumerate(days_fa):
            for row, hour in enumerate(hours):
                item = self.table.item(row, col)
                self.class_schedule[day][hour] = item.text() if item else ''


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ClassScheduleApp()
    window.show()
    sys.exit(app.exec())