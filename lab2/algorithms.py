import numpy as np


def to_grayscale(img):
    if img.ndim == 2:
        return img.copy()
    g = 0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2]
    return np.clip(np.rint(g), 0, 255).astype(np.uint8)


def histogram(channel):
    # Гистограмма 8-битного канала (256 ячеек)
    return np.bincount(channel.ravel(), minlength=256)[:256]


def _stretch(a):
    # out = (in - min) * 255 / (max - min) для одного массива
    a = a.astype(np.float32)
    lo, hi = a.min(), a.max()
    if hi == lo:
        return None
    return np.clip(np.rint((a - lo) * 255.0 / (hi - lo)), 0, 255).astype(np.uint8)


def linear_contrast(img, per_channel=False):
    # Линейное контрастирование: out = (in - min) * 255 / (max - min).

    # Для цветного изображения по умолчанию min и max берутся по всем каналам сразу
    # (соотношение между каналами, а значит и цветовой оттенок, сохраняется)
    # При per_channel=True каждый канал растягивается независимо
    if per_channel and img.ndim == 3:
        chans = []
        for c in range(img.shape[2]):
            out = _stretch(img[..., c])
            chans.append(img[..., c].copy() if out is None else out)
        return np.dstack(chans)
    out = _stretch(img)
    return img.copy() if out is None else out


def equalize_channel(ch):
    # Эквализация гистограммы одного канала: T(k) = (cdf(k) - cdf_min) / (N - cdf_min) * 255
    cdf = histogram(ch).cumsum()
    cdf_min = cdf[cdf > 0][0]
    if ch.size == cdf_min:
        return ch.copy()
    lut = np.rint((cdf - cdf_min) * 255.0 / (ch.size - cdf_min))
    return np.clip(lut, 0, 255).astype(np.uint8)[ch]


def equalize_gray(img):
    return equalize_channel(to_grayscale(img))


def equalize_rgb(img):
    # Эквализация каждого из каналов R, G, B
    return np.dstack([equalize_channel(img[..., c]) for c in range(3)])


def rgb_to_hsv(img):
    # RGB uint8 -> H, S, V в диапазоне [0, 1]
    a = img.astype(np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(axis=-1), a.min(axis=-1)
    d = mx - mn
    safe = np.where(d == 0, 1.0, d)
    h = np.zeros_like(mx)
    mr = (d > 0) & (mx == r)
    mg = (d > 0) & (mx == g) & ~mr
    mb = (d > 0) & ~mr & ~mg
    h[mr] = ((g - b) / safe)[mr] % 6.0
    h[mg] = ((b - r) / safe)[mg] + 2.0
    h[mb] = ((r - g) / safe)[mb] + 4.0
    s = np.where(mx > 0, d / np.where(mx == 0, 1.0, mx), 0.0)
    return h / 6.0, s, mx


def hsv_to_rgb(h, s, v):
    h6 = (h % 1.0) * 6.0
    i = np.floor(h6).astype(np.int32) % 6
    f = h6 - np.floor(h6)
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.clip(np.rint(np.stack([r, g, b], -1) * 255.0), 0, 255).astype(np.uint8)


def equalize_hsv_v(img):
    # Подход 2: эквализация только компоненты яркости V в HSV
    h, s, v = rgb_to_hsv(img)
    v8 = np.clip(np.rint(v * 255.0), 0, 255).astype(np.uint8)
    return hsv_to_rgb(h, s, equalize_channel(v8) / 255.0)


def image_stats(img):
    # Числовые характеристики яркости: диапазон, среднее, контраст, энтропия
    g = to_grayscale(img)
    h = histogram(g).astype(np.float64)
    p = h / h.sum()
    p = p[p > 0]
    return {'min': int(g.min()), 'max': int(g.max()), 'mean': float(g.mean()),
            'std': float(g.std()), 'entropy': float(-(p * np.log2(p)).sum())}


def mean_hue_shift(a, b, min_saturation=0.05):
    # Средний сдвиг оттенка H (в градусах) между двумя цветными изображениями
    ha, sa, _ = rgb_to_hsv(a)
    hb, _, _ = rgb_to_hsv(b)
    d = np.abs(((ha - hb + 0.5) % 1.0) - 0.5)
    m = sa > min_saturation
    return float(d[m].mean() * 360.0) if m.any() else 0.0


def convolve2d(image, kernel):
    kh, kw = kernel.shape
    ph, pw = kh // 2, kw // 2
    padded = np.pad(image.astype(np.float32), ((ph, ph), (pw, pw)), mode='reflect')
    h, w = image.shape
    out = np.zeros((h, w), np.float32)
    for i in range(kh):
        for j in range(kw):
            out += padded[i:i + h, j:j + w] * kernel[i, j]
    return out


def gaussian_blur(image, sigma):
    # Гауссово сглаживание (два одномерных прохода)
    if sigma <= 0:
        return image.astype(np.float32)
    r = max(1, int(3.0 * sigma + 0.5))
    x = np.arange(-r, r + 1, dtype=np.float32)
    k = np.exp(-x * x / (2.0 * sigma * sigma))
    k /= k.sum()
    tmp = convolve2d(image, k[None, :])
    return convolve2d(tmp, k[:, None])


POINT_KERNEL = np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]], np.float32)

LINE_KERNELS = {
    'horiz': np.array([[-1, -1, -1], [2, 2, 2], [-1, -1, -1]], np.float32),
    'vert':  np.array([[-1, 2, -1], [-1, 2, -1], [-1, 2, -1]], np.float32),
    'p45':   np.array([[-1, -1, 2], [-1, 2, -1], [2, -1, -1]], np.float32),
    'm45':   np.array([[2, -1, -1], [-1, 2, -1], [-1, -1, 2]], np.float32),
}


def detect_points(gray, threshold=0.4):
    resp = np.abs(convolve2d(gray, POINT_KERNEL))
    return np.where(resp >= threshold * 8 * 255, 255, 0).astype(np.uint8)


def detect_lines(gray, direction='all', threshold=0.3, polarity='bright'):
    keys = list(LINE_KERNELS) if direction == 'all' else [direction]
    sign = -1.0 if polarity == 'dark' else 1.0
    resp = np.maximum.reduce([sign * convolve2d(gray, LINE_KERNELS[k]) for k in keys])
    return np.where(resp >= threshold * 6 * 255, 255, 0).astype(np.uint8)


def detect_edges(gray, operator='sobel', threshold=0.0, sigma=0.0):
    src = gaussian_blur(gray, sigma) if sigma > 0 else gray
    f = lambda a: np.array(a, np.float32)
    if operator == 'sobel':
        gx = convolve2d(src, f([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]))
        gy = convolve2d(src, f([[-1, -2, -1], [0, 0, 0], [1, 2, 1]]))
        mag = np.hypot(gx, gy)
    elif operator == 'prewitt':
        gx = convolve2d(src, f([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]]))
        gy = convolve2d(src, f([[-1, -1, -1], [0, 0, 0], [1, 1, 1]]))
        mag = np.hypot(gx, gy)
    else:
        mag = np.abs(convolve2d(src, f([[0, 1, 0], [1, -4, 1], [0, 1, 0]])))
    if mag.max() > 0:
        mag = mag / mag.max() * 255.0
    out = np.clip(np.rint(mag), 0, 255).astype(np.uint8)
    if threshold > 0:
        out = np.where(out >= threshold * 255.0, 255, 0).astype(np.uint8)
    return out


def dilate_mask(mask, radius=1):
    # Расширение бинарной маски квадратным элементом (2*radius+1)^2
    m = mask > 0
    if radius <= 0:
        return m
    p = np.pad(m, radius)
    h, w = m.shape
    out = np.zeros_like(m)
    for dy in range(2 * radius + 1):
        for dx in range(2 * radius + 1):
            out |= p[dy:dy + h, dx:dx + w]
    return out


def overlay_mask(img, mask, color=(255, 40, 40), radius=1, dim=0.55):
    base = img.astype(np.float32)
    if base.ndim == 2:
        base = np.dstack([base] * 3)
    out = np.clip(np.rint(base * dim), 0, 255).astype(np.uint8)
    out[dilate_mask(mask, radius)] = color
    return out


def count_components(mask, max_pixels=20000):
    # Число 8-связных областей в бинарной маске (None, если пикселей слишком много)
    m = mask > 0
    if int(m.sum()) > max_pixels:
        return None
    h, w = m.shape
    seen = np.zeros_like(m)
    n = 0
    ys, xs = np.nonzero(m)
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if seen[y0, x0]:
            continue
        n += 1
        seen[y0, x0] = True
        stack = [(y0, x0)]
        while stack:
            y, x = stack.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and m[yy, xx] and not seen[yy, xx]:
                        seen[yy, xx] = True
                        stack.append((yy, xx))
    return n