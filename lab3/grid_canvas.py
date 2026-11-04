import math
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont

class GridCanvasWidget(QWidget):
    point_clicked = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.cell_size = 24.0      # Размер клетки сетки
        self.offset_x = 0.0        # Смещение центра по X
        self.offset_y = 0.0        # Смещение центра по Y
        self._dragging_pan = False
        self._last_mouse_pos = None

        self.pixels = []           # Список (x, y) или (x, y, alpha)
        self.is_wu = False
        self.key_points = []       # [(x, y), ...] Опорные точки кликов

    def set_pixels(self, pixels, is_wu=False):
        self.pixels = pixels
        self.is_wu = is_wu
        self.update()

    def set_key_points(self, pts):
        self.key_points = pts
        self.update()

    def clear_all(self):
        self.pixels = []
        self.key_points = []
        self.update()

    def screen_to_grid(self, sx: float, sy: float):
        origin_x = self.width() / 2.0 + self.offset_x
        origin_y = self.height() / 2.0 + self.offset_y
        gx = round((sx - origin_x) / self.cell_size)
        gy = round((origin_y - sy) / self.cell_size)
        return int(gx), int(gy)

    def grid_to_screen(self, gx: float, gy: float):
        origin_x = self.width() / 2.0 + self.offset_x
        origin_y = self.height() / 2.0 + self.offset_y
        sx = origin_x + gx * self.cell_size
        sy = origin_y - gy * self.cell_size
        return sx, sy

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        zoom = 1.15 if delta > 0 else 0.85
        new_size = max(6.0, min(80.0, self.cell_size * zoom))
        self.cell_size = new_size
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._dragging_pan = True
            self._last_mouse_pos = event.pos()
        elif event.button() == Qt.LeftButton:
            gx, gy = self.screen_to_grid(event.x(), event.y())
            self.point_clicked.emit(gx, gy)

    def mouseMoveEvent(self, event):
        if self._dragging_pan and self._last_mouse_pos is not None:
            delta = event.pos() - self._last_mouse_pos
            self.offset_x += delta.x()
            self.offset_y += delta.y()
            self._last_mouse_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self._dragging_pan = False
            self._last_mouse_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        w, h = self.width(), self.height()

        # Заливка фона
        painter.fillRect(0, 0, w, h, QColor("#FDFDFD"))

        origin_x = w / 2.0 + self.offset_x
        origin_y = h / 2.0 + self.offset_y

        # Рисуем растровые пиксели
        painter.setPen(Qt.NoPen)
        for item in self.pixels:
            if self.is_wu:
                gx, gy, alpha = item
                color = QColor(41, 128, 185, int(max(0.0, min(1.0, alpha)) * 255))
            else:
                gx, gy = item[0], item[1]
                color = QColor(52, 152, 219)

            sx, sy = self.grid_to_screen(gx, gy)
            rx = sx - self.cell_size / 2.0
            ry = sy - self.cell_size / 2.0
            painter.fillRect(int(rx), int(ry), int(self.cell_size) + 1, int(self.cell_size) + 1, color)

        # Рисуем сетку
        pen_grid = QPen(QColor("#E2E8F0"), 1)
        painter.setPen(pen_grid)

        start_col = math.floor((0 - origin_x) / self.cell_size) - 1
        end_col = math.ceil((w - origin_x) / self.cell_size) + 1
        for col in range(start_col, end_col):
            x = origin_x + col * self.cell_size
            painter.drawLine(int(x), 0, int(x), h)

        start_row = math.floor((origin_y - h) / self.cell_size) - 1
        end_row = math.ceil((origin_y - 0) / self.cell_size) + 1
        for row in range(start_row, end_row):
            y = origin_y - row * self.cell_size
            painter.drawLine(0, int(y), w, int(y))

        # Оси координат
        pen_axis = QPen(QColor("#2C3E50"), 2)
        painter.setPen(pen_axis)
        painter.drawLine(0, int(origin_y), w, int(origin_y))
        painter.drawLine(int(origin_x), 0, int(origin_x), h)

        # Числовые метки
        font = QFont("Helvetica", 8)
        painter.setFont(font)
        painter.setPen(QColor("#7F8C8D"))

        step_label = 1 if self.cell_size >= 22 else (5 if self.cell_size >= 10 else 10)
        for col in range(start_col, end_col):
            if col != 0 and col % step_label == 0:
                x = origin_x + col * self.cell_size
                painter.drawText(int(x - 12), int(origin_y + 14), 24, 12, Qt.AlignCenter, str(col))

        for row in range(start_row, end_row):
            if row != 0 and row % step_label == 0:
                y = origin_y - row * self.cell_size
                painter.drawText(int(origin_x + 5), int(y - 6), 30, 12, Qt.AlignLeft, str(row))

        # Опорные точки клика
        painter.setRenderHint(QPainter.Antialiasing, True)
        for i, (gx, gy) in enumerate(self.key_points):
            sx, sy = self.grid_to_screen(gx, gy)
            painter.setBrush(QBrush(QColor("#E74C3C")))
            painter.setPen(QPen(Qt.black, 1.5))
            painter.drawEllipse(QPointF(sx, sy), 5, 5)
            painter.setPen(QColor("#C0392B"))
            painter.drawText(int(sx + 8), int(sy - 8), f"P{i+1}({gx}, {gy})")