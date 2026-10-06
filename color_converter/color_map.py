import colorsys
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QImage


class ColorMapWidget(QWidget):
    color_selected = pyqtSignal(int, int, int)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(360, 360)
        self.setMouseTracking(True)
        self.selected_hue = 0.0
        self.selected_sat = 1.0
        self.selected_value = 1.0
        self.current_color = QColor(0, 0, 0)
        self._image = QImage()
        self._dragging = False
        self._last_rgb = None

    def _rebuild_image(self):
        width, height = self.width(), self.height()
        if width <= 0 or height <= 0:
            return
        image = QImage(width, height, QImage.Format_RGB32)
        for x in range(width):
            hue = x / max(1, width - 1)
            for y in range(height):
                saturation = 1.0 - y / max(1, height - 1)
                r, g, b = colorsys.hsv_to_rgb(hue, saturation, 1.0)
                image.setPixel(x, y, QColor(round(r * 255), round(g * 255), round(b * 255)).rgb())
        self._image = image

    def resizeEvent(self, event):
        self._rebuild_image()
        self.update()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._image.isNull() or self._image.size() != self.size():
            self._rebuild_image()
        painter.drawImage(0, 0, self._image)
        painter.setPen(QPen(QColor(90, 90, 90), 2))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        x = round(self.selected_hue * max(1, self.width() - 1))
        y = round((1.0 - self.selected_sat) * max(1, self.height() - 1))
        painter.setPen(QPen(Qt.white, 3))
        painter.drawEllipse(x - 6, y - 6, 12, 12)
        painter.setPen(QPen(Qt.black, 1))
        painter.drawEllipse(x - 7, y - 7, 14, 14)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._select_from_position(event.pos(), emit_signal=True)

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._select_from_position(event.pos(), emit_signal=True)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self._select_from_position(event.pos(), emit_signal=True)

    def _select_from_position(self, pos, emit_signal):
        width, height = self.width(), self.height()
        x = max(0, min(pos.x(), width - 1))
        y = max(0, min(pos.y(), height - 1))
        self.selected_hue = x / max(1, width - 1)
        self.selected_sat = 1.0 - y / max(1, height - 1)
        self.selected_value = 1.0
        r, g, b = colorsys.hsv_to_rgb(self.selected_hue, self.selected_sat, self.selected_value)
        rgb = (round(r * 255), round(g * 255), round(b * 255))
        self.current_color = QColor(*rgb)
        self.update()
        if emit_signal and rgb != self._last_rgb:
            self._last_rgb = rgb
            self.color_selected.emit(*rgb)

    def set_rgb_color(self, r, g, b):
        r = max(0, min(255, int(r))); g = max(0, min(255, int(g))); b = max(0, min(255, int(b)))
        h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        self.selected_hue, self.selected_sat, self.selected_value = h, s, v
        self.current_color = QColor(r, g, b)
        self._last_rgb = (r, g, b)
        self.update()
