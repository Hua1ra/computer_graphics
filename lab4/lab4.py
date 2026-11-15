import math
import os
import sys
import traceback
from typing import List, Optional, Tuple

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

Point = Tuple[float, float]
Segment = Tuple[float, float, float, float]

EPS = 1e-9

# Коды областей для алгоритма Сазерленда-Коэна
INSIDE = 0  # 0000
LEFT = 1    # 0001
RIGHT = 2   # 0010
BOTTOM = 4  # 0100
TOP = 8     # 1000


def compute_outcode(x: float, y: float, xmin: float, ymin: float, xmax: float, ymax: float) -> int:
    code = INSIDE
    if x < xmin - EPS:
        code |= LEFT
    elif x > xmax + EPS:
        code |= RIGHT
    if y < ymin - EPS:
        code |= BOTTOM
    elif y > ymax + EPS:
        code |= TOP
    return code


def cohen_sutherland_clip(
    seg: Segment, xmin: float, ymin: float, xmax: float, ymax: float
) -> Optional[Segment]:
    """
    Алгоритм Сазерленда-Коэна с явным заданием прямой y = k*x + b
    (и обработкой вертикальных прямых x = const).
    """
    x1, y1, x2, y2 = seg
    xmin, xmax = min(xmin, xmax), max(xmin, xmax)
    ymin, ymax = min(ymin, ymax), max(ymin, ymax)

    is_vertical = abs(x2 - x1) < EPS
    if not is_vertical:
        k = (y2 - y1) / (x2 - x1)
        b = y1 - k * x1
    else:
        k = None
        b = None

    code1 = compute_outcode(x1, y1, xmin, ymin, xmax, ymax)
    code2 = compute_outcode(x2, y2, xmin, ymin, xmax, ymax)

    for _ in range(16):
        if (code1 | code2) == 0:
            return (x1, y1, x2, y2)
        if (code1 & code2) != 0:
            return None

        code_out = code1 if code1 != 0 else code2
        x, y = 0.0, 0.0

        if code_out & TOP:
            y = ymax
            x = x1 if is_vertical else ((ymax - b) / k if abs(k) > EPS else x1)
        elif code_out & BOTTOM:
            y = ymin
            x = x1 if is_vertical else ((ymin - b) / k if abs(k) > EPS else x1)
        elif code_out & RIGHT:
            x = xmax
            y = y1 if is_vertical else (k * xmax + b)
        elif code_out & LEFT:
            x = xmin
            y = y1 if is_vertical else (k * xmin + b)

        if code_out == code1:
            x1, y1 = x, y
            code1 = compute_outcode(x1, y1, xmin, ymin, xmax, ymax)
        else:
            x2, y2 = x, y
            code2 = compute_outcode(x2, y2, xmin, ymin, xmax, ymax)

    return None


def polygon_signed_area(poly: List[Point]) -> float:
    area = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return 0.5 * area


def is_convex_polygon(poly: List[Point]) -> bool:
    n = len(poly)
    if n < 3:
        return False
    sign = 0
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        x3, y3 = poly[(i + 2) % n]
        cross = (x2 - x1) * (y3 - y2) - (y2 - y1) * (x3 - x2)
        if abs(cross) > EPS:
            cur_sign = 1 if cross > 0 else -1
            if sign == 0:
                sign = cur_sign
            elif sign != cur_sign:
                return False
    return sign != 0


def cyrus_beck_clip(seg: Segment, polygon: List[Point]) -> Optional[Segment]:
    """
    Алгоритм Кируса-Бека: отсечение отрезка выпуклым многоугольником.
    """
    if len(polygon) < 3:
        return None

    poly = list(polygon)
    if polygon_signed_area(poly) < 0:
        poly.reverse()

    x1, y1, x2, y2 = seg
    dx = x2 - x1
    dy = y2 - y1

    if abs(dx) < EPS and abs(dy) < EPS:
        for i in range(len(poly)):
            px, py = poly[i]
            qx, qy = poly[(i + 1) % len(poly)]
            nx, ny = -(qy - py), (qx - px)
            if (x1 - px) * nx + (y1 - py) * ny < -EPS:
                return None
        return seg

    t_enter = 0.0
    t_exit = 1.0

    m = len(poly)
    for i in range(m):
        px, py = poly[i]
        qx, qy = poly[(i + 1) % m]
        ex, ey = qx - px, qy - py

        # Внутренняя нормаль при CCW-обходе
        nx, ny = -ey, ex

        wx, wy = x1 - px, y1 - py
        denom = dx * nx + dy * ny
        numer = wx * nx + wy * ny

        if abs(denom) < EPS:
            if numer < -EPS:
                return None
            continue

        t = -numer / denom
        if denom > 0:
            t_enter = max(t_enter, t)
        else:
            t_exit = min(t_exit, t)

        if t_enter - t_exit > EPS:
            return None

    cx1 = x1 + t_enter * dx
    cy1 = y1 + t_enter * dy
    cx2 = x1 + t_exit * dx
    cy2 = y1 + t_exit * dy
    return (cx1, cy1, cx2, cy2)


class ClippingCanvas(QWidget):
    """Холст для отрисовки системы координат, окна/многоугольника и отрезков."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(520, 480)
        self.setMouseTracking(True)

        self.segments: List[Segment] = []
        self.clipped_segments: List[Optional[Segment]] = []
        self.clip_rect: Optional[Tuple[float, float, float, float]] = None
        self.clip_poly: Optional[List[Point]] = None

        self.center_x = 0.0
        self.center_y = 0.0
        self.scale = 30.0
        self._dragging = False
        self._last_mouse_pos = None

    def set_scene(
        self,
        segments: List[Segment],
        clipped_segments: List[Optional[Segment]],
        clip_rect: Optional[Tuple[float, float, float, float]] = None,
        clip_poly: Optional[List[Point]] = None,
        auto_fit: bool = True,
    ):
        self.segments = segments
        self.clipped_segments = clipped_segments
        self.clip_rect = clip_rect
        self.clip_poly = clip_poly
        if auto_fit:
            self.fit_to_view()
        else:
            self.update()

    def fit_to_view(self):
        xs: List[float] = []
        ys: List[float] = []

        for x1, y1, x2, y2 in self.segments:
            xs.extend([x1, x2])
            ys.extend([y1, y2])

        if self.clip_rect is not None:
            xmin, ymin, xmax, ymax = self.clip_rect
            xs.extend([xmin, xmax])
            ys.extend([ymin, ymax])

        if self.clip_poly:
            for x, y in self.clip_poly:
                xs.append(x)
                ys.append(y)

        if not xs or not ys:
            self.center_x = 0.0
            self.center_y = 0.0
            self.scale = 30.0
            self.update()
            return

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        span_x = max(max_x - min_x, 2.0)
        span_y = max(max_y - min_y, 2.0)

        self.center_x = 0.5 * (min_x + max_x)
        self.center_y = 0.5 * (min_y + max_y)

        w = max(self.width(), 100)
        h = max(self.height(), 100)
        padding = 0.78
        self.scale = min((w * padding) / span_x, (h * padding) / span_y)
        self.scale = max(1e-3, min(self.scale, 1000.0))
        self.update()

    def world_to_screen(self, x: float, y: float) -> QPointF:
        sx = self.width() / 2.0 + (x - self.center_x) * self.scale
        sy = self.height() / 2.0 - (y - self.center_y) * self.scale
        return QPointF(sx, sy)

    def screen_to_world(self, sx: float, sy: float) -> Point:
        wx = self.center_x + (sx - self.width() / 2.0) / self.scale
        wy = self.center_y - (sy - self.height() / 2.0) / self.scale
        return wx, wy

    @staticmethod
    def _nice_step(raw_step: float) -> float:
        if raw_step <= 0:
            return 1.0
        exp = math.floor(math.log10(raw_step))
        base = raw_step / (10 ** exp)
        if base < 1.5:
            nice = 1.0
        elif base < 3.5:
            nice = 2.0
        elif base < 7.5:
            nice = 5.0
        else:
            nice = 10.0
        return nice * (10 ** exp)

    @staticmethod
    def _format_tick(val: float) -> str:
        if abs(val) < 1e-9:
            return "0"
        if abs(val - round(val)) < 1e-7:
            return str(int(round(val)))
        return f"{val:.2f}".rstrip("0").rstrip(".")

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            painter.fillRect(self.rect(), QColor("#FFFFFF"))

            self._draw_coordinate_system(painter)
            self._draw_clip_region(painter)
            self._draw_segments(painter)
            self._draw_legend(painter)
        finally:
            painter.end()

    def _draw_coordinate_system(self, painter: QPainter):
        w, h = float(self.width()), float(self.height())
        left_w, top_w = self.screen_to_world(0.0, 0.0)
        right_w, bottom_w = self.screen_to_world(w, h)

        step = self._nice_step(65.0 / self.scale)

        grid_pen = QPen(QColor("#ECEFF4"), 1.0)
        painter.setPen(grid_pen)

        start_x = math.floor(left_w / step) * step
        x = start_x
        count = 0
        while x <= right_w + step and count < 300:
            p1 = self.world_to_screen(x, bottom_w)
            p2 = self.world_to_screen(x, top_w)
            painter.drawLine(p1, p2)
            x += step
            count += 1

        start_y = math.floor(bottom_w / step) * step
        y = start_y
        count = 0
        while y <= top_w + step and count < 300:
            p1 = self.world_to_screen(left_w, y)
            p2 = self.world_to_screen(right_w, y)
            painter.drawLine(p1, p2)
            y += step
            count += 1

        axis_pen = QPen(QColor("#334155"), 1.6)
        painter.setPen(axis_pen)

        origin = self.world_to_screen(0.0, 0.0)
        if 0.0 <= origin.y() <= h:
            painter.drawLine(QPointF(0.0, origin.y()), QPointF(w, origin.y()))
            painter.drawLine(QPointF(w - 10.0, origin.y() - 4.0), QPointF(w - 2.0, origin.y()))
            painter.drawLine(QPointF(w - 10.0, origin.y() + 4.0), QPointF(w - 2.0, origin.y()))
            painter.drawText(QPointF(w - 18.0, origin.y() - 8.0), "X")

        if 0.0 <= origin.x() <= w:
            painter.drawLine(QPointF(origin.x(), 0.0), QPointF(origin.x(), h))
            painter.drawLine(QPointF(origin.x() - 4.0, 10.0), QPointF(origin.x(), 2.0))
            painter.drawLine(QPointF(origin.x() + 4.0, 10.0), QPointF(origin.x(), 2.0))
            painter.drawText(QPointF(origin.x() + 8.0, 14.0), "Y")

        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QColor("#475569"))

        x_axis_y = max(14.0, min(h - 14.0, origin.y()))
        y_axis_x = max(8.0, min(w - 36.0, origin.x()))

        x = start_x
        count = 0
        while x <= right_w + step and count < 300:
            if abs(x) > 1e-9:
                pt = self.world_to_screen(x, 0.0)
                painter.drawLine(QPointF(pt.x(), x_axis_y - 3.0), QPointF(pt.x(), x_axis_y + 3.0))
                painter.drawText(QPointF(pt.x() + 2.0, x_axis_y + 13.0), self._format_tick(x))
            x += step
            count += 1

        y = start_y
        count = 0
        while y <= top_w + step and count < 300:
            if abs(y) > 1e-9:
                pt = self.world_to_screen(0.0, y)
                painter.drawLine(QPointF(y_axis_x - 3.0, pt.y()), QPointF(y_axis_x + 3.0, pt.y()))
                painter.drawText(QPointF(y_axis_x + 5.0, pt.y() + 4.0), self._format_tick(y))
            y += step
            count += 1

        if 0.0 <= origin.x() <= w and 0.0 <= origin.y() <= h:
            painter.drawText(QPointF(origin.x() + 4.0, origin.y() + 13.0), "0")

    def _draw_clip_region(self, painter: QPainter):
        pen = QPen(QColor("#2563EB"), 2.2)
        brush = QBrush(QColor(37, 99, 235, 32))
        painter.setPen(pen)
        painter.setBrush(brush)

        if self.clip_rect is not None:
            xmin, ymin, xmax, ymax = self.clip_rect
            xmin, xmax = min(xmin, xmax), max(xmin, xmax)
            ymin, ymax = min(ymin, ymax), max(ymin, ymax)
            p1 = self.world_to_screen(xmin, ymax)
            p2 = self.world_to_screen(xmax, ymin)
            # ВАЖНО: QRectF вместо четырёх float
            rect = QRectF(p1.x(), p1.y(), p2.x() - p1.x(), p2.y() - p1.y())
            painter.drawRect(rect)

        if self.clip_poly and len(self.clip_poly) >= 3:
            poly_f = QPolygonF([self.world_to_screen(x, y) for x, y in self.clip_poly])
            painter.drawPolygon(poly_f)

    def _draw_segments(self, painter: QPainter):
        orig_pen = QPen(QColor("#EF4444"), 1.6, Qt.DashLine)
        painter.setPen(orig_pen)
        for x1, y1, x2, y2 in self.segments:
            painter.drawLine(self.world_to_screen(x1, y1), self.world_to_screen(x2, y2))

        vis_pen = QPen(QColor("#16A34A"), 3.2, Qt.SolidLine)
        vis_pen.setCapStyle(Qt.RoundCap)
        painter.setBrush(QBrush(QColor("#15803D")))

        for seg in self.clipped_segments:
            if seg is None:
                continue
            x1, y1, x2, y2 = seg
            p1 = self.world_to_screen(x1, y1)
            p2 = self.world_to_screen(x2, y2)
            painter.setPen(vis_pen)
            painter.drawLine(p1, p2)

            painter.setPen(Qt.NoPen)
            painter.drawEllipse(p1, 3.8, 3.8)
            painter.drawEllipse(p2, 3.8, 3.8)

    def _draw_legend(self, painter: QPainter):
        painter.save()
        x0, y0, box_w, box_h = 12.0, 12.0, 235.0, 78.0
        painter.setPen(QPen(QColor("#CBD5E1"), 1.0))
        painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
        painter.drawRoundedRect(QRectF(x0, y0, box_w, box_h), 6.0, 6.0)

        painter.setFont(QFont("Segoe UI", 8))

        painter.setPen(QPen(QColor("#2563EB"), 2.2))
        painter.drawLine(QPointF(x0 + 10.0, y0 + 20.0), QPointF(x0 + 38.0, y0 + 20.0))
        painter.setPen(QColor("#1E293B"))
        painter.drawText(QPointF(x0 + 46.0, y0 + 24.0), "Отсекающее окно / многоуг.")

        painter.setPen(QPen(QColor("#EF4444"), 1.6, Qt.DashLine))
        painter.drawLine(QPointF(x0 + 10.0, y0 + 42.0), QPointF(x0 + 38.0, y0 + 42.0))
        painter.setPen(QColor("#1E293B"))
        painter.drawText(QPointF(x0 + 46.0, y0 + 46.0), "Исходные отрезки")

        painter.setPen(QPen(QColor("#16A34A"), 3.2))
        painter.drawLine(QPointF(x0 + 10.0, y0 + 64.0), QPointF(x0 + 38.0, y0 + 64.0))
        painter.setPen(QColor("#1E293B"))
        painter.drawText(QPointF(x0 + 46.0, y0 + 68.0), "Видимые части (результат)")

        painter.restore()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.15 if delta > 0 else 1.0 / 1.15
        wx, wy = self.screen_to_world(float(event.x()), float(event.y()))
        self.scale = max(1e-3, min(self.scale * factor, 2000.0))
        new_wx, new_wy = self.screen_to_world(float(event.x()), float(event.y()))
        self.center_x += wx - new_wx
        self.center_y += wy - new_wy
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._last_mouse_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self._dragging and self._last_mouse_pos is not None:
            dx = event.x() - self._last_mouse_pos.x()
            dy = event.y() - self._last_mouse_pos.y()
            self.center_x -= dx / self.scale
            self.center_y += dy / self.scale
            self._last_mouse_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self.setCursor(Qt.ArrowCursor)


SAMPLE_PART1 = """6
-8 -4 12 8
-6 7 10 -3
2 -6 2 10
-9 3 13 3
1 1 7 5
-9 -1 -4 9
-2 -2 8 6"""

SAMPLE_PART2 = """6
-8 -3 11 7
-4 9 9 -4
0 -7 0 11
-9 2 12 2
1 1 5 4
-8 6 -3 9
5
-2 -2
7 -3
10 3
4 8
-4 5"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Лабораторная работа 4 (Вариант 4) — Алгоритмы отсечения")
        self.resize(1180, 740)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        control_panel = QWidget()
        control_panel.setMaximumWidth(450)
        control_layout = QVBoxLayout(control_panel)

        # Общий блок быстрого выбора входного файла (удобно для .exe)
        file_box = QGroupBox("Входной файл")
        file_layout = QVBoxLayout(file_box)
        self.open_file_btn = QPushButton("Выбрать входной файл (.txt)...")
        self.open_file_btn.setStyleSheet("padding: 6px; font-weight: bold;")
        self.open_file_btn.clicked.connect(self._open_file_for_active_tab)
        self.file_path_label = QLabel("Файл не выбран (загружен встроенный пример)")
        self.file_path_label.setWordWrap(True)
        self.file_path_label.setStyleSheet("color: #475569; font-size: 11px;")
        file_layout.addWidget(self.open_file_btn)
        file_layout.addWidget(self.file_path_label)
        control_layout.addWidget(file_box)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_tab_part1(), "Часть 1: Сазерленд-Коэн")
        self.tabs.addTab(self._create_tab_part2(), "Часть 2: Выпуклый многоуг.")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        control_layout.addWidget(self.tabs)

        canvas_container = QWidget()
        canvas_layout = QVBoxLayout(canvas_container)
        self.canvas = ClippingCanvas()
        canvas_layout.addWidget(self.canvas)

        bottom_bar = QHBoxLayout()
        hint_lbl = QLabel("Управление: колесо мыши — масштаб, ЛКМ — перемещение.")
        hint_lbl.setStyleSheet("color: #475569;")
        fit_btn = QPushButton("Вписать в экран")
        fit_btn.clicked.connect(self.canvas.fit_to_view)
        bottom_bar.addWidget(hint_lbl)
        bottom_bar.addStretch()
        bottom_bar.addWidget(fit_btn)
        canvas_layout.addLayout(bottom_bar)

        splitter.addWidget(control_panel)
        splitter.addWidget(canvas_container)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self._run_part1(auto_fit=True)

    def _create_tab_part1(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        info = QLabel(
            "<b>Алгоритм Сазерленда-Коэна</b> (y = kx + b)<br>"
            "<i>Формат:</i> n строк <code>X1 Y1 X2 Y2</code>, затем <code>Xmin Ymin Xmax Ymax</code>."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        btn_row = QHBoxLayout()
        load_btn = QPushButton("Открыть файл...")
        load_btn.clicked.connect(lambda: self._load_from_file(self.editor1, 1))
        sample_btn = QPushButton("Сбросить на пример")
        sample_btn.clicked.connect(lambda: self._load_sample(1))
        btn_row.addWidget(load_btn)
        btn_row.addWidget(sample_btn)
        layout.addLayout(btn_row)

        self.editor1 = QPlainTextEdit(SAMPLE_PART1)
        self.editor1.setFont(QFont("Consolas", 10))
        layout.addWidget(self.editor1, stretch=2)

        run_btn = QPushButton("Выполнить отсечение")
        run_btn.setStyleSheet("font-weight: bold; padding: 6px;")
        run_btn.clicked.connect(lambda: self._run_part1(auto_fit=True))
        layout.addWidget(run_btn)

        res_group = QGroupBox("Результаты отсечения")
        res_layout = QVBoxLayout(res_group)
        self.result1 = QPlainTextEdit()
        self.result1.setReadOnly(True)
        self.result1.setFont(QFont("Consolas", 9))
        res_layout.addWidget(self.result1)
        layout.addWidget(res_group, stretch=2)

        return w

    def _create_tab_part2(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        info = QLabel(
            "<b>Алгоритм Кируса-Бека</b> (отсечение выпуклым многоугольником)<br>"
            "<i>Формат:</i> n строк <code>X1 Y1 X2 Y2</code>, затем <code>m</code> и m строк <code>Px Py</code>."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        btn_row = QHBoxLayout()
        load_btn = QPushButton("Открыть файл...")
        load_btn.clicked.connect(lambda: self._load_from_file(self.editor2, 2))
        sample_btn = QPushButton("Сбросить на пример")
        sample_btn.clicked.connect(lambda: self._load_sample(2))
        btn_row.addWidget(load_btn)
        btn_row.addWidget(sample_btn)
        layout.addLayout(btn_row)

        self.editor2 = QPlainTextEdit(SAMPLE_PART2)
        self.editor2.setFont(QFont("Consolas", 10))
        layout.addWidget(self.editor2, stretch=2)

        run_btn = QPushButton("Выполнить отсечение")
        run_btn.setStyleSheet("font-weight: bold; padding: 6px;")
        run_btn.clicked.connect(lambda: self._run_part2(auto_fit=True))
        layout.addWidget(run_btn)

        res_group = QGroupBox("Результаты отсечения")
        res_layout = QVBoxLayout(res_group)
        self.result2 = QPlainTextEdit()
        self.result2.setReadOnly(True)
        self.result2.setFont(QFont("Consolas", 9))
        res_layout.addWidget(self.result2)
        layout.addWidget(res_group, stretch=2)

        return w

    def _open_file_for_active_tab(self):
        if self.tabs.currentIndex() == 0:
            self._load_from_file(self.editor1, 1)
        else:
            self._load_from_file(self.editor2, 2)

    def _on_tab_changed(self, idx: int):
        if idx == 0:
            self._run_part1(auto_fit=True)
        else:
            self._run_part2(auto_fit=True)

    def _load_sample(self, part: int):
        self.file_path_label.setText("Файл не выбран (загружен встроенный пример)")
        if part == 1:
            self.editor1.setPlainText(SAMPLE_PART1)
            self._run_part1(auto_fit=True)
        else:
            self.editor2.setPlainText(SAMPLE_PART2)
            self._run_part2(auto_fit=True)

    def _load_from_file(self, editor: QPlainTextEdit, part: int):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл с исходными данными", "", "Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                editor.setPlainText(f.read())
            self.file_path_label.setText(f"Выбран файл: {os.path.basename(path)} ({path})")
            if part == 1:
                self._run_part1(auto_fit=True)
            else:
                self._run_part2(auto_fit=True)
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка чтения файла", str(exc))

    @staticmethod
    def _clean_lines(text: str) -> List[str]:
        lines = []
        for raw in text.splitlines():
            line = raw.split("#")[0].split("//")[0].strip()
            if line:
                lines.append(line)
        return lines

    def _parse_part1(self, text: str) -> Tuple[List[Segment], Tuple[float, float, float, float]]:
        lines = self._clean_lines(text)
        if not lines:
            raise ValueError("Пустые входные данные.")

        n = int(lines[0])
        if n < 0:
            raise ValueError("Число отрезков не может быть отрицательным.")
        if len(lines) < n + 2:
            raise ValueError(f"Ожидалось {n + 2} строк(и), получено {len(lines)}.")

        segments: List[Segment] = []
        for i in range(1, n + 1):
            parts = list(map(float, lines[i].split()))
            if len(parts) != 4:
                raise ValueError(f"Строка {i + 1}: ожидалось 4 числа (X1 Y1 X2 Y2).")
            segments.append((parts[0], parts[1], parts[2], parts[3]))

        win_parts = list(map(float, lines[n + 1].split()))
        if len(win_parts) != 4:
            raise ValueError("Последняя строка должна содержать 4 числа: Xmin Ymin Xmax Ymax.")

        return segments, (win_parts[0], win_parts[1], win_parts[2], win_parts[3])

    def _parse_part2(self, text: str) -> Tuple[List[Segment], List[Point]]:
        lines = self._clean_lines(text)
        if not lines:
            raise ValueError("Пустые входные данные.")

        n = int(lines[0])
        if n < 0:
            raise ValueError("Число отрезков не может быть отрицательным.")
        if len(lines) <= n + 1:
            raise ValueError("Не указаны вершины отсекающего многоугольника.")

        segments: List[Segment] = []
        for i in range(1, n + 1):
            parts = list(map(float, lines[i].split()))
            if len(parts) != 4:
                raise ValueError(f"Строка {i + 1}: ожидалось 4 числа (X1 Y1 X2 Y2).")
            segments.append((parts[0], parts[1], parts[2], parts[3]))

        m = int(lines[n + 1])
        if m < 3:
            raise ValueError("Многоугольник должен иметь не менее 3 вершин.")
        if len(lines) < n + 2 + m:
            raise ValueError(f"Ожидалось {m} вершин многоугольника, получено меньше.")

        poly: List[Point] = []
        for i in range(n + 2, n + 2 + m):
            parts = list(map(float, lines[i].split()))
            if len(parts) != 2:
                raise ValueError("Вершина многоугольника: ожидалось 2 числа (Px Py).")
            poly.append((parts[0], parts[1]))

        return segments, poly

    def _run_part1(self, auto_fit: bool = True):
        try:
            segments, rect = self._parse_part1(self.editor1.toPlainText())
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка входных данных (Часть 1)", str(exc))
            return

        xmin, ymin, xmax, ymax = rect
        clipped: List[Optional[Segment]] = []
        log_lines = [
            f"Окно: [{min(xmin, xmax):.2f}, {min(ymin, ymax):.2f}] -> "
            f"[{max(xmin, xmax):.2f}, {max(ymin, ymax):.2f}]",
            "",
        ]

        for idx, seg in enumerate(segments, start=1):
            res = cohen_sutherland_clip(seg, xmin, ymin, xmax, ymax)
            clipped.append(res)
            if res is None:
                log_lines.append(
                    f"#{idx}: ({seg[0]:.2f}, {seg[1]:.2f}) -> ({seg[2]:.2f}, {seg[3]:.2f}) | НЕВИДИМ"
                )
            else:
                log_lines.append(
                    f"#{idx}: ({res[0]:.2f}, {res[1]:.2f}) -> ({res[2]:.2f}, {res[3]:.2f})"
                )

        self.result1.setPlainText("\n".join(log_lines))
        self.canvas.set_scene(
            segments=segments,
            clipped_segments=clipped,
            clip_rect=rect,
            clip_poly=None,
            auto_fit=auto_fit,
        )

    def _run_part2(self, auto_fit: bool = True):
        try:
            segments, poly = self._parse_part2(self.editor2.toPlainText())
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка входных данных (Часть 2)", str(exc))
            return

        if not is_convex_polygon(poly):
            QMessageBox.warning(
                self,
                "Невыпуклый многоугольник",
                "Введённый многоугольник не является выпуклым. "
                "Алгоритм Кируса-Бека требует выпуклый многоугольник.",
            )
            self.canvas.set_scene(
                segments=segments,
                clipped_segments=[],
                clip_rect=None,
                clip_poly=poly,
                auto_fit=auto_fit,
            )
            self.result2.setPlainText("Ошибка: многоугольник не выпуклый.")
            return

        clipped: List[Optional[Segment]] = []
        log_lines = [f"Вершин многоугольника: {len(poly)}", ""]

        for idx, seg in enumerate(segments, start=1):
            res = cyrus_beck_clip(seg, poly)
            clipped.append(res)
            if res is None:
                log_lines.append(
                    f"#{idx}: ({seg[0]:.2f}, {seg[1]:.2f}) -> ({seg[2]:.2f}, {seg[3]:.2f}) | НЕВИДИМ"
                )
            else:
                log_lines.append(
                    f"#{idx}: ({res[0]:.2f}, {res[1]:.2f}) -> ({res[2]:.2f}, {res[3]:.2f})"
                )

        self.result2.setPlainText("\n".join(log_lines))
        self.canvas.set_scene(
            segments=segments,
            clipped_segments=clipped,
            clip_rect=None,
            clip_poly=poly,
            auto_fit=auto_fit,
        )


def install_excepthook():
    def handle_exception(exc_type, exc_value, exc_traceback):
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        sys.stderr.write(msg)
        if QApplication.instance() is not None:
            QMessageBox.critical(None, "Непредвиденная ошибка", msg)

    sys.excepthook = handle_exception


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    install_excepthook()
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()