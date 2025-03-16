import sys
import os
import math
import re
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QMessageBox
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QImage
from PyQt5.QtCore import Qt


# Класс для области drag-and-drop
class DragDropArea(QWidget):
    def __init__(self, text, color, hover_color, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)  # Включаем поддержку drag-and-drop
        self.default_style = f"background-color: {color}; border: 2px solid black;"
        self.hover_style = f"background-color: {hover_color}; border: 2px solid black;"
        self.setStyleSheet(self.default_style)

        # Создаем текст внутри области
        layout = QVBoxLayout(self)
        label = QLabel(text, self)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        # Подсвечиваем область, если перетаскивается файл
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self.hover_style)

    def dragLeaveEvent(self, event):
        # Возвращаем исходный стиль при выходе курсора
        self.setStyleSheet(self.default_style)

    def dropEvent(self, event: QDropEvent):
        # Обрабатываем сброшенный файл и возвращаем исходный стиль
        self.setStyleSheet(self.default_style)
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.parent().process_file(file_path, self)


# Основное окно приложения
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Конвертер файлов в PNG")
        self.setGeometry(100, 100, 1000, 600)  # Увеличиваем размер окна до 1000x600

        # Создаем горизонтальный layout для двух областей
        main_layout = QHBoxLayout(self)

        # Область для шифрования
        self.encrypt_area = DragDropArea("Зашифровать файл в PNG", "lightblue", "skyblue", self)
        # Область для расшифровки
        self.decrypt_area = DragDropArea("Расшифровать файл из PNG", "lightgreen", "limegreen", self)

        # Добавляем области в layout
        main_layout.addWidget(self.encrypt_area)
        main_layout.addWidget(self.decrypt_area)

    def process_file(self, file_path, area):
        # Определяем, в какую область сброшен файл
        if area == self.encrypt_area:
            self.convert_to_png(file_path)
        elif area == self.decrypt_area:
            self.load_png(file_path)

    def get_unique_filename(self, base_path):
        """
        Генерирует уникальное имя файла, добавляя номер в скобках, если файл уже существует.
        """
        dir_name, file_name = os.path.split(base_path)
        name, ext = os.path.splitext(file_name)

        if not os.path.exists(base_path):
            return base_path

        pattern = re.compile(rf"{re.escape(name)} \((\d+)\){re.escape(ext)}")
        max_num = 0
        for file in os.listdir(dir_name):
            match = pattern.match(file)
            if match:
                num = int(match.group(1))
                max_num = max(max_num, num)

        new_name = f"{name} ({max_num + 1}){ext}"
        return os.path.join(dir_name, new_name)

    def convert_to_png(self, file_path):
        # Получаем расширение файла
        ext = os.path.splitext(file_path)[1].encode('utf-8')
        ext_len = len(ext).to_bytes(1, 'little')

        # Читаем байты файла
        with open(file_path, 'rb') as f:
            file_bytes = f.read()

        # Добавляем размер файла
        size = len(file_bytes)
        size_bytes = size.to_bytes(4, 'little')

        # Объединяем данные
        total_bytes = ext_len + ext + size_bytes + file_bytes

        # Вычисляем размер изображения
        data_len = len(total_bytes)
        n = math.ceil(math.sqrt(data_len / 4))
        image_size = n * n * 4  # RGBA

        # Создаем изображение
        image = QImage(n, n, QImage.Format_RGBA8888)
        buffer = image.bits()
        buffer.setsize(image_size)
        buffer[:data_len] = total_bytes

        # Сохраняем PNG с уникальным именем
        base_png_path = os.path.splitext(file_path)[0] + ".png"
        png_path = self.get_unique_filename(base_png_path)
        image.save(png_path, "PNG")
        self.show_message(f"Файл сохранен как {png_path}")

    def load_png(self, file_path):
        # Загружаем PNG
        image = QImage(file_path)
        if image.isNull():
            self.show_error_message("Не удалось загрузить изображение")
            return

        # Преобразуем в RGBA8888
        if image.format() != QImage.Format_RGBA8888:
            image = image.convertToFormat(QImage.Format_RGBA8888)

        # Получаем данные изображения
        buffer = image.bits()
        buffer.setsize(image.byteCount())
        data = bytes(buffer)

        # Извлекаем расширение и размер
        ext_len = data[0]
        if len(data) < 1 + ext_len + 4:
            self.show_error_message("Недостаточно данных для извлечения расширения и размера")
            return

        ext = data[1:1 + ext_len].decode('utf-8')
        size = int.from_bytes(data[1 + ext_len:1 + ext_len + 4], 'little')

        # Проверяем, достаточно ли данных
        if len(data) < 1 + ext_len + 4 + size:
            self.show_error_message("Недостаточно данных для извлечения файла")
            return

        # Извлекаем файл
        file_bytes = data[1 + ext_len + 4:1 + ext_len + 4 + size]

        # Сохраняем восстановленный файл с уникальным именем
        base_save_path = os.path.splitext(file_path)[0] + ext
        save_path = self.get_unique_filename(base_save_path)
        with open(save_path, 'wb') as f:
            f.write(file_bytes)
        self.show_message(f"Файл восстановлен как {save_path}")

    def show_message(self, message):
        # Показываем информационное сообщение
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("Информация")
        msg_box.setText(message)
        msg_box.exec_()

    def show_error_message(self, message):
        # Показываем сообщение об ошибке
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Ошибка")
        msg_box.setText(message)
        msg_box.exec_()


# Запуск приложения
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())