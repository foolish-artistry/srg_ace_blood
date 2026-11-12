"""
png2paa.py - convert an RGBA PNG to an Arma 3 DXT5 PAA (for *_ca textures).

Why: some converters brighten pixels on alpha edges, which shows in game as
white specks around transparent decals. This encoder keeps color and alpha
separate: color mips are built from the color-bled RGB only, alpha mips from
alpha only, so edge colors can never drift toward white.

Layout matches BI's ImageToPAA output: AVGC, MAXC, FLAG, OFFS tags, no palette,
mips down to 4x4, mips 256px and larger LZO-compressed, 6-byte terminator.

Requires: numpy, Pillow >= 11.2 (DXT5 encoding), python-lzo (or lzokay).

Usage: python png2paa.py input.png output.paa
"""
import io
import struct
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

try:
    import lzo

    def lzo_compress(data):
        return lzo.compress(data, 9, False)       # lzo1x_999, no header
except ImportError:                               # pragma: no cover
    import lzokay

    def lzo_compress(data):
        return lzokay.compress(data)

LZO_MIN_WIDTH = 256


def bleed(rgb, alpha, thresh=1):
    """Fill fully transparent pixels with the color of the nearest visible pixel."""
    known = alpha >= thresh
    if not known.any():
        return rgb
    _, (iy, ix) = distance_transform_edt(~known, return_indices=True)
    return rgb[iy, ix]


def build_mips(rgba):
    rgb = rgba[..., :3].astype(np.float64)
    a = rgba[..., 3].astype(np.float64)
    rgb = bleed(rgb, a)
    # never let any mip leave the color range of the visible texture
    vis = a > 0
    lo = rgb[vis].min(axis=0) if vis.any() else np.zeros(3)
    hi = rgb[vis].max(axis=0) if vis.any() else np.full(3, 255.0)
    mips = []
    while True:
        h, w = a.shape
        c = np.clip(rgb, lo, hi)
        mips.append(np.dstack([np.round(c), np.round(a)]).clip(0, 255).astype(np.uint8))
        if w <= 4 or h <= 4:
            break
        rgb = rgb.reshape(h // 2, 2, w // 2, 2, 3).mean(axis=(1, 3))   # color: plain box filter
        a = a.reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))          # alpha: plain box filter
    return mips


def _palettes(a0, a1):
    """DXT5 alpha palettes, shape (n, 8). a0 > a1: 8-value mode, else 6-value + 0/255."""
    a0 = a0.astype(np.int32)[:, None]; a1 = a1.astype(np.int32)[:, None]
    i = np.arange(1, 7)[None, :]
    p8 = np.hstack([a0, a1, ((7 - i) * a0 + i * a1) // 7])
    j = np.arange(1, 5)[None, :]
    p6 = np.hstack([a0, a1, ((5 - j) * a0 + j * a1) // 5,
                    np.zeros_like(a0), np.full_like(a0, 255)])
    return np.where((a0 > a1), p8, p6)


def encode_alpha_blocks(alpha):
    """Encode alpha (h, w) into DXT5 alpha blocks (n, 8 bytes), trying both modes per block."""
    h, w = alpha.shape
    blk = alpha.reshape(h // 4, 4, w // 4, 4).transpose(0, 2, 1, 3).reshape(-1, 16).astype(np.int32)
    n = len(blk)
    hi, lo = blk.max(1), blk.min(1)
    # candidate 1: 8-value mode spanning min..max
    c1_a0, c1_a1 = hi.copy(), lo.copy()
    same = c1_a0 == c1_a1                      # flat block: any mode, keep a0 > a1 if possible
    c1_a0[same & (c1_a0 < 255)] += 1
    c1_a1[same & (c1_a0 >= 255)] -= 1
    # candidate 2: 6-value mode spanning the values strictly between 0 and 255
    mid = np.where((blk > 0) & (blk < 255), blk, -1)
    mhi = mid.max(1); mlo = np.where(mid >= 0, mid, 999).min(1)
    has_mid = mhi >= 0
    c2_a0 = np.where(has_mid, mlo, 0); c2_a1 = np.where(has_mid, mhi, 255)   # a0 <= a1 selects 6-value mode
    best_err = None
    for a0, a1 in ((c1_a0, c1_a1), (c2_a0, c2_a1)):
        pal = _palettes(a0, a1)
        d = np.abs(blk[:, :, None] - pal[:, None, :])
        idx = d.argmin(2); err = d.min(2).sum(1)
        if best_err is None:
            best_err, best = err, (a0, a1, idx)
        else:
            take = err < best_err
            best_err = np.where(take, err, best_err)
            best = tuple(np.where(take[:, None] if x.ndim == 2 else take, y, x) for x, y in zip(best, (a0, a1, idx)))
    a0, a1, idx = best
    bits = np.zeros(n, dtype=np.uint64)
    for k in range(16):
        bits |= idx[:, k].astype(np.uint64) << np.uint64(3 * k)
    out = np.zeros((n, 8), dtype=np.uint8)
    out[:, 0] = a0; out[:, 1] = a1
    for k in range(6):
        out[:, 2 + k] = ((bits >> np.uint64(8 * k)) & np.uint64(0xFF)).astype(np.uint8)
    return out


def dxt5(mip):
    buf = io.BytesIO()
    Image.fromarray(mip, 'RGBA').save(buf, 'DDS', pixel_format='DXT5')
    d = buf.getvalue()
    assert d[:4] == b'DDS ' and d[84:88] == b'DXT5'
    data = bytearray(d[128:])
    h, w = mip.shape[:2]
    assert len(data) == w * h, (len(data), w, h)
    # Pillow handles the color half of each block; replace its coarse alpha half
    blocks = np.frombuffer(bytes(data), np.uint8).reshape(-1, 16).copy()
    blocks[:, :8] = encode_alpha_blocks(mip[..., 3])
    return blocks.tobytes()


def tag(name, data):
    return b'GGAT' + name[::-1].encode() + struct.pack('<I', len(data)) + data


def encode(png_path, paa_path):
    rgba = np.asarray(Image.open(png_path).convert('RGBA'))
    h, w = rgba.shape[:2]
    if w != h or w & (w - 1) or w < 4:
        raise SystemExit(f'{png_path}: must be square power of two, got {w}x{h}')
    mips = build_mips(rgba)

    # AVGC: visible (alpha-weighted) color, mean alpha; stored as B,G,R,A bytes
    A = rgba[..., 3].astype(np.float64)
    wsum = A.sum()
    avg = (rgba[..., :3] * A[..., None]).sum(axis=(0, 1)) / wsum if wsum else np.zeros(3)
    avgc = bytes([int(round(avg[2])), int(round(avg[1])), int(round(avg[0])), int(round(A.mean()))])

    blocks = []
    for m in mips:
        mh, mw = m.shape[:2]
        raw = dxt5(m)
        if mw >= LZO_MIN_WIDTH:
            blocks.append((mw | 0x8000, mh, lzo_compress(raw)))
        else:
            blocks.append((mw, mh, raw))

    head_len = 2 + (12 + 4) * 3 + (12 + 64) + 2
    offs, pos = [], head_len
    for _, _, d in blocks:
        offs.append(pos)
        pos += 7 + len(d)
    offs += [0] * (16 - len(offs))

    out = bytearray(struct.pack('<H', 0xFF05))
    out += tag('AVGC', avgc)
    out += tag('MAXC', b'\xff\xff\xff\xff')
    out += tag('FLAG', struct.pack('<I', 1))
    out += tag('OFFS', struct.pack('<16I', *offs))
    out += struct.pack('<H', 0)                    # no palette
    assert len(out) == head_len
    for mw, mh, d in blocks:
        out += struct.pack('<HH', mw, mh) + len(d).to_bytes(3, 'little') + d
    out += b'\0' * 6
    open(paa_path, 'wb').write(out)
    return len(mips)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    n = encode(sys.argv[1], sys.argv[2])
    print(f'{sys.argv[2]}: {n} mips')
