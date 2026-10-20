import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
from PIL import Image
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import algorithms as alg

EXPLAIN = {
    'intro':
        "Загрузите изображение (папка test_images) и выберите метод. Здесь появятся пояснение к методу "
        "и числовые характеристики: диапазон яркости, σ (среднеквадратичное отклонение яркости — мера "
        "контраста), энтропия гистограммы и, для цветных изображений, средний сдвиг оттенка.",
    'linear':
        "Линейное контрастирование: out = (in − min)·255/(max − min). Диапазон яркостей растягивается на "
        "0…255, форма гистограммы не меняется. Метод бессилен, если в кадре есть выбросы 0 и 255 "
        "(06_dark_with_outliers, 09_photo_moon), и усиливает шум вместе с сигналом. У цветного изображения "
        "min и max берутся по всем каналам сразу — оттенок сохраняется; режим «по каналам» растягивает "
        "каждый канал отдельно, что убирает цветовой оттенок, но сдвигает цвета.",
    'eq_gray':
        "Эквализация гистограммы: яркости заменяются по T(k) = (cdf(k) − cdf_min)/(N − cdf_min)·255, "
        "гистограмма становится близкой к равномерной. В отличие от линейного растяжения работает и при "
        "выбросах в диапазоне, но сильно растягивает узкие пики гистограммы: шум больших плоских областей "
        "превращается в пятна (07_flat_background). Результат — изображение в градациях серого.",
    'eq_rgb':
        "Эквализация каналов R, G, B по отдельности: у каждого канала своё преобразование, поэтому "
        "соотношение каналов, а с ним оттенок и цвет, меняется. Контраст максимальный, но цвета "
        "искажаются — сдвиг оттенка показан в метриках (на 09_photo_astronaut_dark это десятки градусов).",
    'eq_hsv':
        "Эквализация только компоненты яркости V в HSV: оттенок H и насыщенность S не изменяются, поэтому "
        "цвета сохраняются (сдвиг оттенка около 0°). Контраст по яркости получается близким к "
        "эквализации RGB, но без цветовых искажений.",
    'points':
        "Обнаружение точек: маска 3×3 (+8 в центре, −1 вокруг; сумма 0, на однородном фоне отклик нулевой). "
        "Пиксель отмечается, если |R| ≥ T·8·255; модуль позволяет находить и светлые, и тёмные точки. "
        "Малый T — шум принимается за точки, большой T — теряются точки с малым контрастом (при T = 0,5 "
        "тёмные точки на фоне 120 пропадают). Красным показаны найденные пиксели поверх исходного "
        "изображения; для наглядности они расширены до 5×5.",
    'lines':
        "Обнаружение линий: четыре маски 3×3 (горизонталь, вертикаль, ±45°) с весом 2 вдоль линии и −1 вне "
        "неё; отклик R сравнивается с порогом T·6·255. Берётся положительный отклик (R ≥ T), а не модуль: "
        "по обе стороны от линии отклик отрицательный, и при |R| линия утолщалась бы до 3 пикселей. "
        "Полярность задаёт тип линий (светлые на тёмном или тёмные на светлом); при неверной полярности и "
        "низком T вдоль линий появляются «ореолы». Маски рассчитаны на линии толщиной 1 пиксель.",
    'edges':
        "Перепады яркости. Собель и Превитт — первая производная (градиент √(Gx² + Gy²)); Собель придаёт "
        "больший вес центральной строке и столбцу маски, Превитт — равномерный, результаты близки. "
        "Лапласиан — вторая производная, к шуму чувствителен сильнее всего (13_edges_noisy). Сглаживание σ "
        "подавляет шум (Лапласиан + сглаживание = LoG), но размывает перепады. Результат нормирован по "
        "максимальному отклику; порог > 0 даёт бинарную карту (отклик ≥ порог · максимум).",
}

OVERLAY_RADIUS = {'points': 2, 'lines': 1, 'edges': 1}
OPERATOR_NAMES = {'sobel': 'Собель', 'prewitt': 'Превитт', 'laplacian': 'Лапласиан'}


def is_binary(img):
    return img.ndim == 2 and bool(np.isin(np.unique(img), (0, 255)).all())


def _stats_line(title, img):
    s = alg.image_stats(img)
    return (f"{title}: диапазон [{s['min']}, {s['max']}], среднее {s['mean']:.1f}, "
            f"σ = {s['std']:.1f}, энтропия {s['entropy']:.2f} бит")


def contrast_report(orig, res, name):
    text = _stats_line("Исходное", orig) + "\n" + _stats_line(name, res)
    if res.ndim == 3 and orig.ndim == 3:
        text += f"\nСредний сдвиг оттенка: {alg.mean_hue_shift(orig, res):.1f}°"
    return text


def seg_report(mask, key, params):
    n_px = int((mask > 0).sum())
    share = 100.0 * n_px / mask.size
    if key == 'points':
        n = alg.count_components(mask)
        body = (f"Найдено точек: {n}" if n is not None else f"Найдено пикселей: {n_px}")
        body += f" (пикселей: {n_px}, {share:.3f}% изображения)"
    elif key == 'lines':
        body = f"Найдено пикселей линий: {n_px} ({share:.2f}% изображения)"
    elif is_binary(mask):
        body = f"Найдено пикселей перепадов: {n_px} ({share:.2f}% изображения)"
    else:
        body = (f"Средний отклик: {mask.mean():.1f} из 255; доля пикселей с откликом ≥ 64: "
                f"{100.0 * (mask >= 64).mean():.2f}%")
    return f"{params}\n{body}"


def draw_hist(ax, img, title):
    ax.clear()
    ax.set_title(title, fontsize=10)
    ax.set_xlim(0, 255)
    if img.ndim == 3:
        for i, col in enumerate(('red', 'green', 'blue')):
            ax.plot(alg.histogram(img[..., i]), color=col, alpha=0.7, lw=1)
    else:
        ax.fill_between(np.arange(256), alg.histogram(img), color='0.3')
    ax.grid(True, ls=':', alpha=0.6)


class App:
    def __init__(self, root):
        self.root = root
        root.title("Лабораторная работа 2 — вариант 4")
        root.geometry("1300x860")
        self.orig = None
        self.result = None
        self.mode = None            # для сегментации, иначе None
        self.pt_thr = tk.DoubleVar(value=0.4)
        self.ln_thr = tk.DoubleVar(value=0.3)
        self.edge_thr = tk.DoubleVar(value=0.0)
        self.edge_sigma = tk.DoubleVar(value=0.0)
        self.per_channel = tk.BooleanVar(value=False)
        self.overlay = tk.BooleanVar(value=True)
        self._build()
        self._set_text(EXPLAIN['intro'])

    def _slider(self, parent, text, var, lo, hi, fmt="{:.2f}"):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X)
        ttk.Label(row, text=text).pack(side=tk.LEFT)
        val = ttk.Label(row, text=fmt.format(var.get()), width=5)
        val.pack(side=tk.RIGHT)
        ttk.Scale(parent, from_=lo, to=hi, variable=var,
                  command=lambda _v: val.config(text=fmt.format(var.get()))).pack(fill=tk.X)

    def _build(self):
        ctrl = ttk.Frame(self.root, padding=8, width=310)
        ctrl.pack(side=tk.LEFT, fill=tk.Y)
        ctrl.pack_propagate(False)
        ttk.Button(ctrl, text="Загрузить изображение", command=self.load).pack(fill=tk.X)

        nb = ttk.Notebook(ctrl)
        nb.pack(fill=tk.X, pady=6)
        t1 = ttk.Frame(nb, padding=6)
        t2 = ttk.Frame(nb, padding=6)
        nb.add(t1, text="Контраст")
        nb.add(t2, text="Сегментация")

        # вкладка Контраст
        ttk.Checkbutton(t1, text="Линейное контрастирование\nпо каналам (иначе общий min/max)",
                        variable=self.per_channel).pack(anchor=tk.W, pady=(0, 4))
        for text, cmd in [("Линейное контрастирование", self.do_linear),
                          ("Эквализация (градации серого)", self.do_eq_gray),
                          ("Эквализация RGB (3 канала)", self.do_eq_rgb),
                          ("Эквализация HSV (яркость V)", self.do_eq_hsv)]:
            ttk.Button(t1, text=text, command=cmd).pack(fill=tk.X, pady=1)
        ttk.Button(t1, text="Сравнить методы", command=self.compare).pack(fill=tk.X, pady=(8, 1))

        # вкладка Сегментация
        ttk.Checkbutton(t2, text="Показывать результат поверх исходного",
                        variable=self.overlay, command=self.refresh).pack(anchor=tk.W, pady=(0, 4))
        ttk.Label(t2, text="Точки").pack(anchor=tk.W)
        self._slider(t2, "Порог T", self.pt_thr, 0.05, 0.6)
        ttk.Button(t2, text="Обнаружить точки", command=self.points).pack(fill=tk.X, pady=1)

        ttk.Separator(t2).pack(fill=tk.X, pady=5)
        ttk.Label(t2, text="Линии").pack(anchor=tk.W)
        self.line_cb = ttk.Combobox(t2, state="readonly", values=[
            "Все направления", "Горизонтальные", "Вертикальные", "+45°", "-45°"])
        self.line_cb.current(0)
        self.line_cb.pack(fill=tk.X)
        self.pol_cb = ttk.Combobox(t2, state="readonly", values=["Светлые линии", "Тёмные линии"])
        self.pol_cb.current(0)
        self.pol_cb.pack(fill=tk.X, pady=2)
        self._slider(t2, "Порог T", self.ln_thr, 0.05, 0.8)
        ttk.Button(t2, text="Обнаружить линии", command=self.lines).pack(fill=tk.X, pady=1)

        ttk.Separator(t2).pack(fill=tk.X, pady=5)
        ttk.Label(t2, text="Перепады яркости").pack(anchor=tk.W)
        self.edge_cb = ttk.Combobox(t2, state="readonly", values=["Собель", "Превитт", "Лапласиан"])
        self.edge_cb.current(0)
        self.edge_cb.pack(fill=tk.X, pady=(0, 2))
        self._slider(t2, "Сглаживание σ", self.edge_sigma, 0.0, 3.0, "{:.1f}")
        self._slider(t2, "Порог (0 — карта)", self.edge_thr, 0.0, 1.0)
        ttk.Button(t2, text="Найти перепады яркости", command=self.edges).pack(fill=tk.X, pady=1)

        ttk.Button(ctrl, text="Сброс", command=self.reset).pack(fill=tk.X, pady=(10, 2))
        ttk.Button(ctrl, text="Сохранить результат", command=self.save).pack(fill=tk.X)

        right = ttk.Frame(self.root)
        right.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
        bottom = ttk.Frame(right)
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        self.text = tk.Text(bottom, height=9, wrap=tk.WORD, padx=6, pady=4)
        sb = ttk.Scrollbar(bottom, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.fig = Figure(figsize=(9, 6), dpi=100)
        self.axes = self.fig.subplots(2, 2)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _set_text(self, s):
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, s)
        self.text.configure(state=tk.DISABLED)

    def load(self):
        init = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_images")
        path = filedialog.askopenfilename(initialdir=init if os.path.isdir(init) else None,
                                          filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp")])
        if not path:
            return
        img = Image.open(path).convert('RGB')
        img.thumbnail((800, 800), Image.Resampling.LANCZOS)
        self.orig = np.array(img)
        self.result = self.orig.copy()
        self.mode = None
        self.refresh()
        self._set_text(f"Загружено: {os.path.basename(path)}\n" + _stats_line("Изображение", self.orig))

    def save(self):
        if self.result is None:
            return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if path:
            Image.fromarray(self.result).save(path)

    def reset(self):
        if self.orig is not None:
            self.result = self.orig.copy()
            self.mode = None
            self.refresh()
            self._set_text(EXPLAIN['intro'])

    def _check(self):
        if self.orig is None:
            messagebox.showinfo("Нет изображения", "Сначала загрузите изображение.")
            return False
        return True

    def _contrast(self, func, key, name):
        if not self._check():
            return
        self.mode = None
        self.result = func(self.orig)
        self.refresh()
        self._set_text(EXPLAIN[key] + "\n\n" + contrast_report(self.orig, self.result, name))

    def do_linear(self):
        pc = self.per_channel.get()
        self._contrast(lambda im: alg.linear_contrast(im, pc), 'linear',
                       "Линейное контрастирование" + (" (по каналам)" if pc else ""))

    def do_eq_gray(self):
        self._contrast(alg.equalize_gray, 'eq_gray', "Эквализация (серый)")

    def do_eq_rgb(self):
        self._contrast(alg.equalize_rgb, 'eq_rgb', "Эквализация RGB")

    def do_eq_hsv(self):
        self._contrast(alg.equalize_hsv_v, 'eq_hsv', "Эквализация HSV (V)")

    def _segment(self, mask, key, params):
        self.mode = key
        self.result = mask
        self.refresh()
        self._set_text(EXPLAIN[key] + "\n\n" + seg_report(mask, key, params))

    def points(self):
        if not self._check():
            return
        t = self.pt_thr.get()
        self._segment(alg.detect_points(alg.to_grayscale(self.orig), t), 'points',
                      f"Параметры: порог T = {t:.2f}")

    def lines(self):
        if not self._check():
            return
        dirs = {"Все направления": 'all', "Горизонтальные": 'horiz', "Вертикальные": 'vert',
                "+45°": 'p45', "-45°": 'm45'}
        pols = {"Светлые линии": 'bright', "Тёмные линии": 'dark'}
        d, p, t = dirs[self.line_cb.get()], pols[self.pol_cb.get()], self.ln_thr.get()
        mask = alg.detect_lines(alg.to_grayscale(self.orig), d, t, p)
        self._segment(mask, 'lines', f"Параметры: {self.line_cb.get()}, {self.pol_cb.get().lower()}, "
                                     f"порог T = {t:.2f}")

    def edges(self):
        if not self._check():
            return
        ops = {"Собель": 'sobel', "Превитт": 'prewitt', "Лапласиан": 'laplacian'}
        op, sg, th = ops[self.edge_cb.get()], self.edge_sigma.get(), self.edge_thr.get()
        res = alg.detect_edges(alg.to_grayscale(self.orig), op, th, sg)
        params = f"Параметры: {self.edge_cb.get()}, сглаживание σ = {sg:.1f}, " + \
                 (f"порог {th:.2f}" if th > 0 else "без порога (карта откликов)")
        self._segment(res, 'edges', params)

    def _display(self):
        r = self.result
        if self.mode and self.overlay.get() and is_binary(r):
            return alg.overlay_mask(self.orig, r, radius=OVERLAY_RADIUS[self.mode]), True
        return r, False

    def refresh(self):
        if self.orig is None:
            return
        shown, overlaid = self._display()
        a = self.axes
        a[0, 0].clear()
        a[0, 0].imshow(self.orig)
        a[0, 0].set_title("Исходное", fontsize=10)
        a[0, 0].axis('off')
        a[0, 1].clear()
        a[0, 1].imshow(shown, cmap='gray' if shown.ndim == 2 else None, vmin=0, vmax=255)
        a[0, 1].set_title("Результат (красным — найденное)" if overlaid else "Результат", fontsize=10)
        a[0, 1].axis('off')
        draw_hist(a[1, 0], self.orig, "Гистограмма исходного")
        draw_hist(a[1, 1], self.result, "Гистограмма результата")
        self.fig.tight_layout(pad=2.0)
        self.canvas.draw()

    def compare(self):
        if not self._check():
            return
        s = self.orig
        pc = self.per_channel.get()
        variants = [("Исходное", s),
                    ("Линейное" + (" (по каналам)" if pc else ""), alg.linear_contrast(s, pc)),
                    ("Эквализация (серый)", alg.equalize_gray(s)),
                    ("Эквализация RGB", alg.equalize_rgb(s)),
                    ("Эквализация HSV (V)", alg.equalize_hsv_v(s))]
        win = tk.Toplevel(self.root)
        win.title("Сравнение методов повышения контраста")
        win.geometry("1500x720")
        fig = Figure(figsize=(15, 6.8), dpi=100)
        axs = fig.subplots(2, len(variants))
        for k, (name, im) in enumerate(variants):
            st = alg.image_stats(im)
            label = f"{name}\nσ = {st['std']:.1f}, диапазон [{st['min']}, {st['max']}]"
            if im.ndim == 3 and k > 0:
                label += f"\nсдвиг оттенка {alg.mean_hue_shift(s, im):.1f}°"
            axs[0, k].imshow(im, cmap='gray' if im.ndim == 2 else None, vmin=0, vmax=255)
            axs[0, k].set_title(label, fontsize=9)
            axs[0, k].axis('off')
            draw_hist(axs[1, k], im, "")
        fig.tight_layout(pad=1.5)
        cv = FigureCanvasTkAgg(fig, master=win)
        cv.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        cv.draw()


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
