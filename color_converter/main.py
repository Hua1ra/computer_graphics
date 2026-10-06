import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

from color_map import ColorMapWidget
from color_input_panels import RGBColorRow, CMYKColorRow, HSVColorRow
from color_converter import ColorConverter


class ColorConverterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.converter = ColorConverter()
        self._sync_in_progress = False
        self._build_ui()
        self._connect_signals()
        self._set_initial_color(0, 0, 0)

    def _build_ui(self):
        self.setWindowTitle("Color converter")
        self.setMinimumSize(1180, 700)
        self.resize(1280, 760)

        central = QWidget()
        self.setCentralWidget(central)
        main = QHBoxLayout(central)
        main.setContentsMargins(14, 14, 14, 14)
        main.setSpacing(18)

        left = QVBoxLayout()
        label = QLabel("HSV Palette")
        label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left.addWidget(label)
        self.color_map = ColorMapWidget()
        left.addWidget(self.color_map, 1, Qt.AlignCenter)

        right = QVBoxLayout()
        title = QLabel("Color Models: CMYK, RGB, HSV")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        right.addWidget(title)
        self.rgb_row = RGBColorRow()
        right.addWidget(self.rgb_row)
        self.cmyk_row = CMYKColorRow()
        right.addWidget(self.cmyk_row)
        self.hsv_row = HSVColorRow()
        right.addWidget(self.hsv_row)
        right.addStretch()

        main.addLayout(left, 5)
        main.addLayout(right, 5)

        self.setStyleSheet("""
            QMainWindow { background: #f5f5f5; }
            QFrame { background: white; border: 1px solid #d0d0d0; border-radius: 6px; }
            QSlider::groove:horizontal { height: 5px; background: #d5d5d5; border-radius: 2px; }
            QSlider::handle:horizontal { width: 14px; margin: -5px 0; border-radius: 7px; background: #555; }
            QSpinBox { padding: 3px; }
        """)

    def _connect_signals(self):
        self.rgb_row.rgb_changed.connect(self.on_rgb_changed)
        self.cmyk_row.cmyk_changed.connect(self.on_cmyk_changed)
        self.hsv_row.hsv_changed.connect(self.on_hsv_changed)
        self.color_map.color_selected.connect(self.on_color_map_changed)

    def _set_initial_color(self, r, g, b):
        self._sync_in_progress = True
        self.rgb_row.set_rgb(r, g, b)
        self.cmyk_row.set_cmyk(*self.converter.rgb_to_cmyk(r, g, b))
        self.hsv_row.set_hsv(*self.converter.rgb_to_hsv(r, g, b))
        self.color_map.set_rgb_color(r, g, b)
        self._sync_in_progress = False

    def _update_from_rgb(self, r, g, b):
        self._sync_in_progress = True
        self.rgb_row.set_rgb(r, g, b)
        self.cmyk_row.set_cmyk(*self.converter.rgb_to_cmyk(r, g, b))
        self.hsv_row.set_hsv(*self.converter.rgb_to_hsv(r, g, b))
        self.color_map.set_rgb_color(r, g, b)
        self._sync_in_progress = False

    def on_rgb_changed(self, r, g, b):
        if self._sync_in_progress: return
        self._update_from_rgb(r, g, b)

    def on_cmyk_changed(self, c, m, y, k):
        if self._sync_in_progress: return
        self._update_from_rgb(*self.converter.cmyk_to_rgb(c, m, y, k))

    def on_hsv_changed(self, h, s, v):
        if self._sync_in_progress: return
        self._update_from_rgb(*self.converter.hsv_to_rgb(h, s, v))

    def on_color_map_changed(self, r, g, b):
        if self._sync_in_progress: return
        self._update_from_rgb(r, g, b)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ColorConverterApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
