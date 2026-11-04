import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QComboBox, QSpinBox, QPushButton, QTextEdit, QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt
from raster_algorithms import RasterAlgorithms
from grid_canvas import GridCanvasWidget

class RasterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Базовые растровые алгоритмы")
        self.resize(1200, 750)
        self.setMinimumSize(950, 600)
        self.points_buffer = []
        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # Холст
        self.canvas = GridCanvasWidget()
        self.canvas.point_clicked.connect(self.on_canvas_clicked)
        main_layout.addWidget(self.canvas, 7)

        # Боковая панель
        side_panel = QVBoxLayout()
        side_panel.setSpacing(12)

        # Группа алгоритма
        algo_group = QGroupBox("Выбор алгоритма")
        algo_layout = QVBoxLayout(algo_group)
        self.algo_combo = QComboBox()
        self.algo_combo.addItems([
            "Пошаговый алгоритм",
            "Алгоритм ЦДА (DDA)",
            "Алгоритм Брезенхема (отрезок)",
            "Алгоритм Кастла-Питвея (отрезок)",
            "Алгоритм Брезенхема (окружность)",
            "Сглаживание Ву (Xiaolin Wu)"
        ])
        self.algo_combo.currentIndexChanged.connect(self.on_algorithm_changed)
        algo_layout.addWidget(self.algo_combo)
        side_panel.addWidget(algo_group)

        # Координаты точек
        self.coords_group = QGroupBox("Параметры фигуры")
        self.coords_layout = QGridLayout(self.coords_group)

        self.lbl_x1 = QLabel("X1 / Xc:")
        self.spin_x1 = QSpinBox()
        self.spin_x1.setRange(-200, 200)
        self.spin_x1.setValue(1)

        self.lbl_y1 = QLabel("Y1 / Yc:")
        self.spin_y1 = QSpinBox()
        self.spin_y1.setRange(-200, 200)
        self.spin_y1.setValue(1)

        self.lbl_x2 = QLabel("X2 / R:")
        self.spin_x2 = QSpinBox()
        self.spin_x2.setRange(-200, 200)
        self.spin_x2.setValue(14)

        self.lbl_y2 = QLabel("Y2:")
        self.spin_y2 = QSpinBox()
        self.spin_y2.setRange(-200, 200)
        self.spin_y2.setValue(9)

        self.coords_layout.addWidget(self.lbl_x1, 0, 0)
        self.coords_layout.addWidget(self.spin_x1, 0, 1)
        self.coords_layout.addWidget(self.lbl_y1, 0, 2)
        self.coords_layout.addWidget(self.spin_y1, 0, 3)

        self.coords_layout.addWidget(self.lbl_x2, 1, 0)
        self.coords_layout.addWidget(self.spin_x2, 1, 1)
        self.coords_layout.addWidget(self.lbl_y2, 1, 2)
        self.coords_layout.addWidget(self.spin_y2, 1, 3)

        side_panel.addWidget(self.coords_group)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_draw = QPushButton("Растеризовать")
        self.btn_draw.setStyleSheet("background-color: #2ECC71; color: white; font-weight: bold; padding: 6px;")
        self.btn_draw.clicked.connect(self.draw_selected)

        self.btn_clear = QPushButton("Очистить")
        self.btn_clear.clicked.connect(self.clear_canvas)
        btn_layout.addWidget(self.btn_draw)
        btn_layout.addWidget(self.btn_clear)
        side_panel.addLayout(btn_layout)

        # Бенчмарк
        self.btn_bench = QPushButton("Сравнить время всех алгоритмов")
        self.btn_bench.setStyleSheet("background-color: #34495E; color: white; padding: 6px;")
        self.btn_bench.clicked.connect(self.run_benchmark)
        side_panel.addWidget(self.btn_bench)

        # Информационный блок
        self.info_label = QLabel("ЛКМ: точка на сетке. ПКМ: перемещение. Колёсико: зум.")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #555; font-size: 11px;")
        side_panel.addWidget(self.info_label)

        # Лог пикселей
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        side_panel.addWidget(self.log_text)

        main_layout.addLayout(side_panel, 3)
        self.on_algorithm_changed()

    def on_algorithm_changed(self):
        is_circle = self.algo_combo.currentText() == "Алгоритм Брезенхема (окружность)"
        self.lbl_x1.setText("Xc:" if is_circle else "X1:")
        self.lbl_y1.setText("Yc:" if is_circle else "Y1:")
        self.lbl_x2.setText("Радиус R:" if is_circle else "X2:")
        self.lbl_y2.setVisible(not is_circle)
        self.spin_y2.setVisible(not is_circle)

    def on_canvas_clicked(self, gx, gy):
        is_circle = self.algo_combo.currentText() == "Алгоритм Брезенхема (окружность)"
        if is_circle:
            if not self.points_buffer:
                self.points_buffer.append((gx, gy))
                self.spin_x1.setValue(gx)
                self.spin_y1.setValue(gy)
                self.canvas.set_key_points(self.points_buffer)
            else:
                xc, yc = self.points_buffer[0]
                radius = round(((gx - xc)**2 + (gy - yc)**2)**0.5)
                self.spin_x2.setValue(radius)
                self.points_buffer.append((gx, gy))
                self.draw_selected()
                self.points_buffer = []
        else:
            if len(self.points_buffer) == 0:
                self.points_buffer.append((gx, gy))
                self.spin_x1.setValue(gx)
                self.spin_y1.setValue(gy)
                self.canvas.set_key_points(self.points_buffer)
            else:
                self.points_buffer.append((gx, gy))
                self.spin_x2.setValue(gx)
                self.spin_y2.setValue(gy)
                self.draw_selected()
                self.points_buffer = []

    def draw_selected(self):
        algo = self.algo_combo.currentText()
        x1 = self.spin_x1.value()
        y1 = self.spin_y1.value()
        x2 = self.spin_x2.value()
        y2 = self.spin_y2.value()

        is_wu = False
        t_micro = 0.0

        if algo == "Пошаговый алгоритм":
            pixels = RasterAlgorithms.step_by_step(x1, y1, x2, y2)
            t_micro = RasterAlgorithms.measure_time(RasterAlgorithms.step_by_step, x1, y1, x2, y2)
        elif algo == "Алгоритм ЦДА (DDA)":
            pixels = RasterAlgorithms.dda(x1, y1, x2, y2)
            t_micro = RasterAlgorithms.measure_time(RasterAlgorithms.dda, x1, y1, x2, y2)
        elif algo == "Алгоритм Брезенхема (отрезок)":
            pixels = RasterAlgorithms.bresenham_line(x1, y1, x2, y2)
            t_micro = RasterAlgorithms.measure_time(RasterAlgorithms.bresenham_line, x1, y1, x2, y2)
        elif algo == "Алгоритм Кастла-Питвея (отрезок)":
            pixels = RasterAlgorithms.castle_pitteway_line(x1, y1, x2, y2)
            t_micro = RasterAlgorithms.measure_time(RasterAlgorithms.castle_pitteway_line, x1, y1, x2, y2)
        elif algo == "Алгоритм Брезенхема (окружность)":
            pixels = RasterAlgorithms.bresenham_circle(x1, y1, x2)
            t_micro = RasterAlgorithms.measure_time(RasterAlgorithms.bresenham_circle, x1, y1, x2)
        elif algo == "Сглаживание Ву (Xiaolin Wu)":
            pixels = RasterAlgorithms.wu_line(x1, y1, x2, y2)
            t_micro = RasterAlgorithms.measure_time(RasterAlgorithms.wu_line, x1, y1, x2, y2)
            is_wu = True

        self.canvas.set_pixels(pixels, is_wu=is_wu)
        if algo == "Алгоритм Брезенхема (окружность)":
            self.canvas.set_key_points([(x1, y1)])
        else:
            self.canvas.set_key_points([(x1, y1), (x2, y2)])

        # Логирование
        self.log_text.clear()
        self.log_text.append(f"<b>{algo}</b>")
        self.log_text.append(f"Количество пикселей: <b>{len(pixels)}</b>")
        self.log_text.append(f"Время расчёта: <b>{t_micro:.2f} мкс</b>\n")
        self.log_text.append("Координаты пикселей:")
        if is_wu:
            for p in pixels:
                self.log_text.append(f"({p[0]}, {p[1]}) [alpha = {p[2]:.2f}]")
        else:
            for p in pixels:
                self.log_text.append(f"({p[0]}, {p[1]})")

    def run_benchmark(self):
        x1, y1, x2, y2 = 0, 0, 100, 60
        r = 60
        t_step = RasterAlgorithms.measure_time(RasterAlgorithms.step_by_step, x1, y1, x2, y2, repeat=3000)
        t_dda = RasterAlgorithms.measure_time(RasterAlgorithms.dda, x1, y1, x2, y2, repeat=3000)
        t_bres = RasterAlgorithms.measure_time(RasterAlgorithms.bresenham_line, x1, y1, x2, y2, repeat=3000)
        t_cp = RasterAlgorithms.measure_time(RasterAlgorithms.castle_pitteway_line, x1, y1, x2, y2, repeat=3000)
        t_circ = RasterAlgorithms.measure_time(RasterAlgorithms.bresenham_circle, 0, 0, r, repeat=3000)
        t_wu = RasterAlgorithms.measure_time(RasterAlgorithms.wu_line, x1, y1, x2, y2, repeat=3000)

        self.log_text.clear()
        self.log_text.append("=== СРАВНЕНИЕ ВРЕМЕНИ (3000 итераций) ===")
        self.log_text.append(f"1. Пошаговый: {t_step:.2f} мкс")
        self.log_text.append(f"2. ЦДА (DDA): {t_dda:.2f} мкс")
        self.log_text.append(f"3. Брезенхем (отрезок): {t_bres:.2f} мкс")
        self.log_text.append(f"4. Кастл-Питвей: {t_cp:.2f} мкс")
        self.log_text.append(f"5. Брезенхем (окружность): {t_circ:.2f} мкс")
        self.log_text.append(f"6. Сглаживание Ву: {t_wu:.2f} мкс")

    def clear_canvas(self):
        self.points_buffer = []
        self.canvas.clear_all()
        self.log_text.clear()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = RasterApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()