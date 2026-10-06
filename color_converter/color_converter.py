from typing import Tuple


class ColorConverter:
    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    @staticmethod
    def rgb_to_hsv(r: int, g: int, b: int) -> Tuple[int, int, int]:
        """RGB (0..255) -> HSV (H: 0..360, S/V: 0..100)."""
        import colorsys
        r, g, b = (ColorConverter._clamp(x, 0, 255) / 255.0 for x in (r, g, b))
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        return round(h * 360), round(s * 100), round(v * 100)

    @staticmethod
    def hsv_to_rgb(h: int, s: int, v: int) -> Tuple[int, int, int]:
        """HSV (H: 0..360, S/V: 0..100) -> RGB (0..255)."""
        import colorsys
        h = ColorConverter._clamp(h, 0, 360) / 360.0
        s = ColorConverter._clamp(s, 0, 100) / 100.0
        v = ColorConverter._clamp(v, 0, 100) / 100.0
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return round(r * 255), round(g * 255), round(b * 255)

    @staticmethod
    def rgb_to_cmyk(r: int, g: int, b: int) -> Tuple[int, int, int, int]:
        """RGB (0..255) -> CMYK (0..100)."""
        r, g, b = (ColorConverter._clamp(x, 0, 255) / 255.0 for x in (r, g, b))
        k = 1.0 - max(r, g, b)
        if k >= 1.0 - 1e-12:
            return 0, 0, 0, 100

        denominator = 1.0 - k
        c = (1.0 - r - k) / denominator
        m = (1.0 - g - k) / denominator
        y = (1.0 - b - k) / denominator
        return round(c * 100), round(m * 100), round(y * 100), round(k * 100)

    @staticmethod
    def cmyk_to_rgb(c: int, m: int, y: int, k: int) -> Tuple[int, int, int]:
        """CMYK (0..100) -> RGB (0..255)."""
        c, m, y, k = (ColorConverter._clamp(x, 0, 100) / 100.0 for x in (c, m, y, k))
        r = 255.0 * (1.0 - c) * (1.0 - k)
        g = 255.0 * (1.0 - m) * (1.0 - k)
        b = 255.0 * (1.0 - y) * (1.0 - k)
        return round(r), round(g), round(b)
