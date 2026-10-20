import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_images")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(42)
W, H = 640, 480


def save(name, arr):
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(os.path.join(OUT, name))


y = np.linspace(0, 1, H)[:, None, None]
sky = np.array([70, 130, 220]) * (1 - y) + np.array([200, 225, 250]) * y
img = Image.fromarray(np.broadcast_to(sky, (H, W, 3)).astype(np.uint8))
d = ImageDraw.Draw(img)
d.ellipse((500, 40, 580, 120), fill=(255, 220, 80))
d.polygon([(0, 330), (150, 230), (320, 320), (470, 220), (640, 310), (640, 480), (0, 480)], fill=(60, 140, 70))
d.rectangle((220, 300, 360, 400), fill=(170, 80, 60))
d.polygon([(205, 300), (290, 240), (375, 300)], fill=(90, 40, 30))
d.rectangle((270, 340, 310, 400), fill=(240, 220, 160))
d.polygon([(0, 480), (250, 400), (390, 400), (640, 480)], fill=(110, 110, 115))
s = np.array(img.filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32)

save("01_low_contrast.png", 110 + (s - 128) * 0.2)
save("02_dark.png", s * 0.22)
save("03_bright.png", 255 - (255 - s) * 0.25)
save("04_low_contrast_noisy.png", 110 + (s - 128) * 0.25 + rng.normal(0, 3, s.shape))
tint = s.copy()
tint[..., 0] = tint[..., 0] * 0.9 + 40
tint[..., 2] = tint[..., 2] * 0.35
save("05_color_cast_low_contrast.png", 100 + (tint - 128) * 0.3)

pts = np.full((H, W), 120.0) + rng.normal(0, 2, (H, W))
for _ in range(25):
    pts[rng.integers(5, H - 5), rng.integers(5, W - 5)] = 255
for _ in range(15):
    pts[rng.integers(5, H - 5), rng.integers(5, W - 5)] = 0
save("10_points.png", pts)

ln = Image.new("L", (W, H), 30)
d = ImageDraw.Draw(ln)
d.line((40, 60, 600, 60), fill=230)
d.line((100, 100, 100, 440), fill=230)
d.line((160, 440, 440, 160), fill=230)
d.line((200, 120, 520, 440), fill=230)
ln_arr = np.array(ln)
save("11_lines.png", ln_arr)

ed = np.full((H, W), 60.0)
ed[:, 320:] = 150
ed[100:260, 60:260] = 220
yy, xx = np.mgrid[0:H, 0:W]
ed[((xx - 470) ** 2 + (yy - 330) ** 2) < 70 ** 2] = 20
ed_sharp = ed.astype(np.uint8)
ed = np.array(Image.fromarray(ed_sharp).filter(ImageFilter.GaussianBlur(1.2)))
save("12_edges.png", ed)
save("13_edges_noisy.png", ed + rng.normal(0, 14, (H, W)))

rng2 = np.random.default_rng(7)

night = Image.fromarray(np.clip(s * 0.22, 0, 255).astype(np.uint8))
dn = ImageDraw.Draw(night)
dn.ellipse((20, 20, 44, 44), fill=(255, 255, 255))
dn.rectangle((600, 440, 639, 479), fill=(0, 0, 0))
save("06_dark_with_outliers.png", np.array(night))

flat = Image.new("RGB", (W, H), (90, 90, 90))
df = ImageDraw.Draw(flat)
df.ellipse((250, 170, 390, 310), fill=(200, 60, 60))
df.rectangle((290, 210, 350, 270), fill=(50, 160, 200))
df.ellipse((315, 225, 335, 245), fill=(230, 230, 60))
flat = np.array(flat.filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32)
save("07_flat_background.png", flat + rng2.normal(0, 1.5, flat.shape))

blur = np.array(Image.fromarray(s.astype(np.uint8)).filter(ImageFilter.GaussianBlur(4))).astype(np.float32)
save("08_blurred_low_contrast.png", 110 + (blur - 128) * 0.3)

ed_blur = np.array(Image.fromarray(ed_sharp).filter(ImageFilter.GaussianBlur(4)))
save("14_edges_blurred.png", ed_blur)

save("15_lines_noisy.png", ln_arr + rng2.normal(0, 20, (H, W)))

save("16_dark_lines.png", 255 - ln_arr)

pn = np.full((H, W), 120.0) + rng2.normal(0, 12, (H, W))
for _ in range(25):
    pn[rng2.integers(5, H - 5), rng2.integers(5, W - 5)] = 255
for _ in range(15):
    pn[rng2.integers(5, H - 5), rng2.integers(5, W - 5)] = 0
save("17_points_noisy.png", pn)

try:
    from skimage import data
    save("09_photo_moon.png", data.moon())
    save("09_photo_astronaut_dark.png", data.astronaut().astype(np.float32) * 0.3)
    save("18_edges_photo.png", data.camera())
except Exception as e:
    pass