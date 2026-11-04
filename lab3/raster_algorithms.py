import math
import time
from typing import List, Tuple

class RasterAlgorithms:
    @staticmethod
    def step_by_step(x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
        pixels = []
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return [(x1, y1)]

        if abs(dx) >= abs(dy):
            step = 1 if dx > 0 else -1
            k = dy / dx
            b = y1 - k * x1
            x = x1
            while True:
                y = round(k * x + b)
                pixels.append((x, y))
                if x == x2:
                    break
                x += step
        else:
            step = 1 if dy > 0 else -1
            k_inv = dx / dy
            b_inv = x1 - k_inv * y1
            y = y1
            while True:
                x = round(k_inv * y + b_inv)
                pixels.append((x, y))
                if y == y2:
                    break
                y += step
        return pixels

    @staticmethod
    def dda(x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
        pixels = []
        dx = x2 - x1
        dy = y2 - y1
        steps = max(abs(dx), abs(dy))
        if steps == 0:
            return [(x1, y1)]

        x_inc = dx / steps
        y_inc = dy / steps
        x, y = float(x1), float(y1)
        for _ in range(steps + 1):
            pixels.append((round(x), round(y)))
            x += x_inc
            y += y_inc
        return pixels

    @staticmethod
    def bresenham_line(x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
        pixels = []
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        x, y = x1, y1

        while True:
            pixels.append((x, y))
            if x == x2 and y == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        return pixels

    @staticmethod
    def bresenham_circle(xc: int, yc: int, r: int) -> List[Tuple[int, int]]:
        pixels = set()
        r = abs(r)
        x = 0
        y = r
        d = 3 - 2 * r

        def add_symmetric(cx, cy, px, py):
            pts = [
                (cx + px, cy + py), (cx - px, cy + py),
                (cx + px, cy - py), (cx - px, cy - py),
                (cx + py, cy + px), (cx - py, cy + px),
                (cx + py, cy - px), (cx - py, cy - px)
            ]
            for p in pts:
                pixels.add(p)

        add_symmetric(xc, yc, x, y)
        while y >= x:
            x += 1
            if d > 0:
                y -= 1
                d = d + 4 * (x - y) + 10
            else:
                d = d + 4 * x + 6
            add_symmetric(xc, yc, x, y)
        return list(pixels)

    @staticmethod
    def castle_pitteway_line(x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
        """
        Алгоритм Кастла-Питвея (Castle-Pitteway) для прямолинейных отрезков.
        Разложение шага по ортогональным векторам u и v с отслеживанием знака дискриминанта.
        """
        pixels = []
        x, y = x1, y1
        dx = x2 - x1
        dy = y2 - y1

        sx = 1 if dx >= 0 else -1
        sy = 1 if dy >= 0 else -1
        dx, dy = abs(dx), abs(dy)

        if dx == 0 and dy == 0:
            return [(x, y)]

        # Определяем прямое и диагональное направление
        if dx >= dy:
            u_x, u_y = sx, 0       # Прямой шаг
            v_x, v_y = sx, sy      # Диагональный шаг
            d = 2 * dy - dx
            d_u = 2 * dy
            d_v = 2 * (dy - dx)
            steps = dx
        else:
            u_x, u_y = 0, sy
            v_x, v_y = sx, sy
            d = 2 * dx - dy
            d_u = 2 * dx
            d_v = 2 * (dx - dy)
            steps = dy

        for _ in range(steps + 1):
            pixels.append((x, y))
            if d < 0:
                x += u_x
                y += u_y
                d += d_u
            else:
                x += v_x
                y += v_y
                d += d_v
        return pixels

    @staticmethod
    def wu_line(x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int, float]]:
        """
        Алгоритм сглаживания Ву (Xiaolin Wu's algorithm).
        Возвращает список (x, y, alpha), где alpha - интенсивность (прозрачность).
        """
        pixels = []

        def fpart(x):
            return x - math.floor(x)

        def rfpart(x):
            return 1.0 - fpart(x)

        steep = abs(y2 - y1) > abs(x2 - x1)
        if steep:
            x1, y1 = y1, x1
            x2, y2 = y2, x2
        if x1 > x2:
            x1, x2 = x2, x1
            y1, y2 = y2, y1

        dx = x2 - x1
        dy = y2 - y1
        gradient = 1.0 if dx == 0 else dy / dx

        # Первая конечная точка
        xend = round(x1)
        yend = y1 + gradient * (xend - x1)
        xgap = rfpart(x1 + 0.5)
        xpxl1 = xend
        ypxl1 = int(math.floor(yend))

        if steep:
            pixels.append((ypxl1, xpxl1, rfpart(yend) * xgap))
            pixels.append((ypxl1 + 1, xpxl1, fpart(yend) * xgap))
        else:
            pixels.append((xpxl1, ypxl1, rfpart(yend) * xgap))
            pixels.append((xpxl1, ypxl1 + 1, fpart(yend) * xgap))

        intery = yend + gradient

        # Вторая конечная точка
        xend = round(x2)
        yend = y2 + gradient * (xend - x2)
        xgap = fpart(x2 + 0.5)
        xpxl2 = xend
        ypxl2 = int(math.floor(yend))

        if steep:
            pixels.append((ypxl2, xpxl2, rfpart(yend) * xgap))
            pixels.append((ypxl2 + 1, xpxl2, fpart(yend) * xgap))
        else:
            pixels.append((xpxl2, ypxl2, rfpart(yend) * xgap))
            pixels.append((xpxl2, ypxl2 + 1, fpart(yend) * xgap))

        # Основной цикл
        if steep:
            for x in range(xpxl1 + 1, xpxl2):
                pixels.append((int(math.floor(intery)), x, rfpart(intery)))
                pixels.append((int(math.floor(intery)) + 1, x, fpart(intery)))
                intery += gradient
        else:
            for x in range(xpxl1 + 1, xpxl2):
                pixels.append((x, int(math.floor(intery)), rfpart(intery)))
                pixels.append((x, int(math.floor(intery)) + 1, fpart(intery)))
                intery += gradient

        return pixels

    @staticmethod
    def measure_time(func, *args, repeat=1000) -> float:
        """Измеряет среднее время выполнения в микросекундах."""
        t0 = time.perf_counter()
        for _ in range(repeat):
            func(*args)
        t1 = time.perf_counter()
        return ((t1 - t0) / repeat) * 1e6