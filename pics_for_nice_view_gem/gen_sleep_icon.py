#!/usr/bin/env python3
"""Regenerate the nice_view_gem sleep-screen artwork.

    uv run --with "rembg[cpu]" --with pillow --with numpy --with scipy \
        pics_for_nice_view_gem/gen_sleep_icon.py [--write]

Produces two LV_IMG_CF_INDEXED_1BIT arrays for widgets/sleep.c:

  sleep_icon_map   136x76  Franklin curled up asleep, from franklin_sleeping.jpeg
  dream_cloud_map  100x56  a thought cloud with a baseball in it, drawn procedurally

The display is black ink on a white field, so the photo maps directly:
a dark pixel becomes palette index 1 (ink), a light one index 0 (paper).
"""
import math
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

HERE = Path(__file__).parent
SRC = HERE / 'franklin_sleeping.jpeg'
CUTOUT = HERE / 'renders' / 'franklin_sleeping_cutout.png'
SLEEP_C = HERE.parent / 'boards/shields/nice_view_gem/widgets/sleep.c'

DOG_W, DOG_H = 136, 76
CLOUD_W, CLOUD_H = 100, 56

PAD = 0.04          # margin around the subject, as a fraction of its long side
FF_RADIUS = 50      # flat-field blur radius, in source pixels
FF_GAIN = 1.2
THRESHOLD = 165     # candidate "D"
DESPECKLE = 3
MAX_HOLE = 12       # fill interior white specks up to this many pixels

SS = 8              # supersampling for the procedural cloud

PALETTE = bytes([0x00, 0x00, 0x00, 0xff,      # index 0 -> the display's white field
                 0xff, 0xff, 0xff, 0xff])     # index 1 -> black ink


# --------------------------------------------------------------------- photo

def cutout():
    """Background-removed source, cached on disk (the model is a 1GB download)."""
    if CUTOUT.exists():
        return Image.open(CUTOUT)
    from rembg import remove
    CUTOUT.parent.mkdir(parents=True, exist_ok=True)
    out = remove(Image.open(SRC).convert('RGBA'))
    out.save(CUTOUT)
    return out


def framed(im, W, H):
    """Crop to W:H around the subject, background forced to white."""
    gray = im.convert('L')
    mask = im.split()[3].point(lambda p: 255 if p > 128 else 0)
    flat = Image.new('L', im.size, 255)
    flat.paste(gray, (0, 0), mask)

    x0, y0, x1, y1 = mask.getbbox()
    scale = min(W / (x1 - x0), H / (y1 - y0)) / (1 + PAD)
    bw, bh = int(W / scale), int(H / scale)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    box = (cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2)

    g = Image.new('L', (bw, bh), 255)
    g.paste(flat.crop(box), (0, 0))
    m = Image.new('L', (bw, bh), 0)
    m.paste(mask.crop(box), (0, 0))
    return g, m


def flatfield(g, mask):
    """Normalise the lighting gradient inside the mask only."""
    a = np.asarray(g, np.float32)
    mk = np.asarray(mask, np.float32) / 255.0
    lit = np.asarray(Image.fromarray((a * mk).astype('uint8'))
                     .filter(ImageFilter.GaussianBlur(FF_RADIUS)), np.float32)
    cov = np.asarray(mask.filter(ImageFilter.GaussianBlur(FF_RADIUS)), np.float32) / 255.0
    local = lit / np.clip(cov, 1e-3, None)
    out = np.where(mk > 0.5, np.clip(128.0 + FF_GAIN * (a - local), 0, 255), 255)
    return Image.fromarray(out.astype('uint8'))


def fill_specks(ink):
    """Fill enclosed white holes of at most MAX_HOLE pixels."""
    holes, n = ndimage.label(~ink)
    if n:
        border = set(holes[0, :]) | set(holes[-1, :]) | set(holes[:, 0]) | set(holes[:, -1])
        for lbl, size in zip(*np.unique(holes, return_counts=True)):
            if lbl and lbl not in border and size <= MAX_HOLE:
                ink |= holes == lbl
    return ink


def dog():
    g, m = framed(cutout(), DOG_W, DOG_H)
    ff = flatfield(g, m)
    ink = np.asarray(ff.resize((DOG_W, DOG_H), Image.LANCZOS), np.float32) < THRESHOLD
    ink &= np.asarray(m.resize((DOG_W, DOG_H), Image.LANCZOS), np.float32) > 127
    img = Image.fromarray((ink * 255).astype('uint8')).convert('L')
    if DESPECKLE:
        img = img.filter(ImageFilter.MedianFilter(DESPECKLE))
    ink = np.asarray(img, np.uint8) > 127
    return Image.fromarray((fill_specks(ink) * 255).astype('uint8')).point(
        lambda p: 255 if p > 127 else 0, mode='1')


# ------------------------------------------------------------ dream cloud

CLOUD_BUMPS = [(30, 27, 13), (47, 17, 16), (67, 20, 14), (83, 28, 11), (55, 32, 15)]
CLOUD_BUBBLES = [(18, 45, 5), (9, 52, 3)]
BALL = (53, 23, 13)
STROKE = 2
SEAM_STROKE = 1.6
SEAM_TICKS = 3
SEAM_BOW = (0.76, 0.32, 0.86)   # (offset, bow, height) as fractions of the radius
TICK_STYLE = 'none'             # 'white' ticks on the caps, 'black' in the band, or 'none'


def _circ(d, cx, cy, r, fill=255):
    d.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=fill)


def cloud():
    big = Image.new('L', (CLOUD_W * SS, CLOUD_H * SS), 0)
    d = ImageDraw.Draw(big)
    for cx, cy, r in CLOUD_BUMPS:
        _circ(d, cx, cy, r)

    # scalloped outline = filled union minus an eroded copy
    er = big.filter(ImageFilter.MinFilter(2 * int(STROKE * SS / 2) + 1))
    out = Image.fromarray(((np.asarray(big) > 127) & ~(np.asarray(er) > 127))
                          .astype('uint8') * 255)
    od = ImageDraw.Draw(out)

    for cx, cy, r in CLOUD_BUBBLES:
        _circ(od, cx, cy, r, 255)
        _circ(od, cx, cy, max(r - STROKE, 1), 0)

    out = _baseball(out)
    return out.resize((CLOUD_W, CLOUD_H), Image.LANCZOS).point(
        lambda p: 255 if p > 110 else 0, mode='1')


def _seam_x(ys, bx, br, sign):
    """Horizontal position of a seam at each y, as an array; NaN where absent."""
    off, bow, hgt = SEAM_BOW
    s = (ys - BALL[1]) / (hgt * br)
    cos_t = np.sqrt(np.clip(1.0 - s * s, 0.0, None))
    x = bx + sign * (off * br - bow * br * cos_t)
    return np.where(np.abs(s) <= 1.0, x, np.nan)


def _baseball(out):
    """Ball with solid ink caps either side of the seams and a white centre band."""
    bx, by, br = BALL
    a = np.asarray(out).astype(bool)
    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w]
    X, Y = xx / SS, yy / SS

    disc = (X - bx) ** 2 + (Y - by) ** 2 <= br ** 2
    rim = disc & ~((X - bx) ** 2 + (Y - by) ** 2 <= (br - STROKE) ** 2)

    xl = _seam_x(Y, bx, br, -1)
    xr = _seam_x(Y, bx, br, +1)
    # rows past the seams' vertical extent are all band, so the ball's top and
    # bottom stay white and the caps close against the rim
    left_cap = disc & ~np.isnan(xl) & (X <= xl)
    right_cap = disc & ~np.isnan(xr) & (X >= xr)

    a &= ~disc                      # clear whatever the cloud drew underneath
    a |= rim | left_cap | right_cap

    if TICK_STYLE != 'none':
        off, bow, hgt = SEAM_BOW
        tick = np.zeros_like(a)
        for sign in (-1, 1):
            for i in range(SEAM_TICKS):
                t = math.radians(-72 + 144 * (i + 1) / (SEAM_TICKS + 1))
                sx = bx + sign * (off * br - bow * br * math.cos(t))
                sy = by + hgt * br * math.sin(t)
                near = (np.abs(Y - sy) <= SEAM_STROKE * 0.45)
                if TICK_STYLE == 'white':       # reach outward into the ink cap
                    span = (X >= min(sx, sx + sign * 2.6)) & (X <= max(sx, sx + sign * 2.6))
                else:                           # reach inward into the white band
                    span = (X >= min(sx, sx - sign * 2.6)) & (X <= max(sx, sx - sign * 2.6))
                tick |= near & span & disc
        a = a & ~tick if TICK_STYLE == 'white' else a | tick

    return Image.fromarray((a * 255).astype('uint8'))


# ------------------------------------------------------------------- codec

def encode(img):
    w, h = img.size
    stride = (w + 7) // 8
    px = img.load()
    out = bytearray(PALETTE)
    for y in range(h):
        row = bytearray(stride)
        for x in range(w):
            if px[x, y]:
                row[x >> 3] |= 1 << (7 - (x & 7))
        out += row
    return bytes(out)


def decode(data, w, h):
    stride = (w + 7) // 8
    img = Image.new('1', (w, h), 0)
    px = img.load()
    for y in range(h):
        row = data[8 + y * stride: 8 + (y + 1) * stride]
        for x in range(w):
            px[x, y] = (row[x >> 3] >> (7 - (x & 7))) & 1
    return img


def to_c_array(data, name, per_line=12):
    body = '\n'.join(
        '    ' + ' '.join(f'0x{b:02x},' for b in data[i:i + per_line])
        for i in range(0, len(data), per_line))
    return f'static const uint8_t {name}[] = {{\n{body}\n}};'


def main():
    assets = [('sleep_icon_map', dog(), DOG_W, DOG_H),
              ('dream_cloud_map', cloud(), CLOUD_W, CLOUD_H)]

    src = SLEEP_C.read_text() if '--write' in sys.argv else None
    for name, img, w, h in assets:
        data = encode(img)
        assert decode(data, w, h).tobytes() == img.tobytes(), f'{name}: round-trip mismatch'
        assert len(data) == 8 + ((w + 7) // 8) * h, f'{name}: bad length {len(data)}'
        print(f'// {name}: {w}x{h}, data_size = {len(data)}', file=sys.stderr)
        if src is None:
            print(to_c_array(data, name))
        else:
            src, n = re.subn(rf'static const uint8_t {name}\[\] = \{{.*?\}};',
                             lambda _m: to_c_array(data, name), src, flags=re.S)
            if n != 1:
                sys.exit(f'{name}: expected 1 array in sleep.c, found {n}')

    if src is not None:
        SLEEP_C.write_text(src)
        print(f'patched {SLEEP_C}')


if __name__ == '__main__':
    main()
