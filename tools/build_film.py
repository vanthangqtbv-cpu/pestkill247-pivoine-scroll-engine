#!/usr/bin/env python3
"""
build_film.py — RIFE-Style Photorealistic Optical Displacement & Layer Warp Engine (v3.3 Clean)
Modeled after Ascenta Studio's `galatea/tools/build_film_rife.py` for PEST KILL 247 — BIOGOLD PRO.
"""

import io
import json
import math
import os
import struct
import time
import numpy as np
from PIL import Image, ImageDraw

OUT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYFRAMES_DIR = os.path.join(OUT_DIR, "assets", "keyframes")
PACKS_DIR = os.path.join(OUT_DIR, "packs", "frames")
PREVIEW_DIR = os.path.join(OUT_DIR, "assets", "preview_frames")

W, H = 1280, 720
N_FRAMES = 160


def smoothstep(edge0, edge1, x):
    """Standard ascending smoothstep where edge0 < edge1."""
    t = np.clip((x - edge0) / max(1e-6, (edge1 - edge0)), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def smoothstep_down(edge_inner, edge_outer, x):
    """1.0 when x <= edge_inner, smoothly 0.0 when x >= edge_outer."""
    return 1.0 - smoothstep(edge_inner, edge_outer, x)


Y_GRID, X_GRID = np.mgrid[0:H, 0:W].astype(np.float32)


def bilinear_sample(img_arr, map_x, map_y):
    x0 = np.floor(map_x).astype(np.int32)
    y0 = np.floor(map_y).astype(np.int32)
    x1 = x0 + 1
    y1 = y0 + 1

    wx = (map_x - x0)[..., np.newaxis]
    wy = (map_y - y0)[..., np.newaxis]

    x0 = np.clip(x0, 0, W - 1)
    x1 = np.clip(x1, 0, W - 1)
    y0 = np.clip(y0, 0, H - 1)
    y1 = np.clip(y1, 0, H - 1)

    Ia = img_arr[y0, x0]
    Ib = img_arr[y1, x0]
    Ic = img_arr[y0, x1]
    Id = img_arr[y1, x1]

    top = Ia * (1.0 - wx) + Ic * wx
    bot = Ib * (1.0 - wx) + Id * wx
    return top * (1.0 - wy) + bot * wy


def warp_act1_bloom(kf1, p_act1, morph_out=0.0):
    """
    Act I (Frames 0..48):
    - Cánh hoa Cúc Trừ Sâu bung nở hướng tâm từ trong ra ngoài quanh tâm (cx=0.726*W, cy=0.495*H).
    - Hũ pha lê ở giữa nổi khối nhẹ kèm vệt sáng khúc xạ chạy qua mặt kính.
    """
    cx, cy = W * 0.726, H * 0.495
    dx = X_GRID - cx
    dy = Y_GRID - cy
    r = np.sqrt(dx * dx + dy * dy) + 1e-5
    ux = dx / r
    uy = dy / r

    petal_band = np.exp(-((r - 195.0) ** 2) / (2.0 * 90.0**2))
    theta = np.arctan2(dy, dx)
    petal_flutter = 1.0 + 0.14 * np.sin(theta * 12.0 + p_act1 * 3.0)

    bloom_expand = (p_act1 - 0.30) * 26.0 * petal_band * petal_flutter
    jar_band = np.exp(-(r**2) / (2.0 * 92.0**2))
    jar_scale = 1.0 - (p_act1 - 0.15) * 0.08 * jar_band

    # During transition out to Act II (morph_out > 0), petals gently press downward toward Act II's flower base
    right_mask = smoothstep(W * 0.45, W * 0.58, X_GRID)
    morph_shift_y = -morph_out * 42.0 * right_mask * smoothstep(H * 0.25, H * 0.55, Y_GRID)

    src_x = cx + dx * jar_scale - ux * bloom_expand
    src_y = cy + dy * jar_scale - uy * bloom_expand + morph_shift_y

    warped = bilinear_sample(kf1, src_x, src_y)

    # Travelling studio glass light-sweep across the faceted crystal jar
    sweep_pos = -100.0 + p_act1 * 200.0
    sweep = np.exp(-(((dx - sweep_pos) + dy * 0.35) ** 2) / (2.0 * 22.0**2)) * jar_band
    warped = warped + sweep[..., np.newaxis] * np.array([20.0, 16.0, 10.0], dtype=np.float32)
    return warped


def warp_act2_levitate(kf2, p_act2, morph_in=0.0):
    """
    Act II (Frames 48..105):
    - Nắp vặn Obsidian-Vàng (y < 0.28*H) bay tách lên cao theo nhịp cuộn (Exploded View).
    - Lõi Gel Hổ Phách bên trong hũ pha lê mở nắp dâng nhẹ và phát sáng.
    - Đài hoa phía dưới mở rộng tạo chiều sâu.
    """
    cx = W * 0.725
    dx = X_GRID - cx
    dy_jar = Y_GRID - H * 0.46

    x_mask = np.exp(-(dx**2) / (2.0 * 240.0**2))
    cap_x_mask = np.exp(-(dx**2) / (2.0 * 115.0**2))

    # 1. Isolated Cap Zone (`Y < 0.275*H`): smoothly levitates higher as p_act2 progresses
    cap_zone = smoothstep_down(H * 0.23, H * 0.285, Y_GRID) * cap_x_mask
    # Positive offset in src_y pulls cap UP on screen; negative pushes cap DOWN on screen
    cap_lift_px = -26.0 * (1.0 - p_act2) + 18.0 * p_act2 - morph_in * 18.0

    # 2. Open Amber Gel Meniscus ripple (centered at x=0.725*W, y=0.345*H)
    gel_dist2 = (dx / 64.0) ** 2 + ((Y_GRID - H * 0.345) / 32.0) ** 2
    gel_mask = np.exp(-gel_dist2 * 1.8)
    gel_swirl_x = np.sin(Y_GRID * 0.16 - p_act2 * 6.5) * 4.5 * gel_mask
    gel_lift_y = p_act2 * 7.0 * gel_mask

    # 3. Flower base (y > 0.56*H) breathes outward as jar levitates
    base_zone = smoothstep(H * 0.54, H * 0.68, Y_GRID) * x_mask
    base_spread_x = -dx * 0.055 * p_act2 * base_zone
    base_drop_y = -16.0 * p_act2 * base_zone

    src_x = X_GRID + gel_swirl_x + base_spread_x
    src_y = Y_GRID + cap_lift_px * cap_zone + gel_lift_y + base_drop_y

    warped = bilinear_sample(kf2, src_x, src_y)

    # Subtle warm golden glow confined strictly inside the open jar mouth
    mouth_glow = np.exp(-((dx / 72.0) ** 2 + ((Y_GRID - H * 0.34) / 44.0) ** 2))
    pulse = (0.35 + 0.65 * math.sin(p_act2 * math.pi)) * mouth_glow
    warped = warped + pulse[..., np.newaxis] * np.array([22.0, 14.0, 3.0], dtype=np.float32)
    return warped


def warp_act3_topdown(kf3, p_act3):
    """
    Act III (Frames 105..159):
    - Góc nhìn từ đỉnh (Top-Down Ritual View) nhìn thẳng vào lõi Gel Hổ Phách đang xoáy tròn (Swirling Vortex)
      bên trong miệng hũ pha lê (r < 92px quanh tâm cx=0.721*W, cy=0.496*H).
    - Các lớp cánh hoa Cúc Trừ Sâu xung quanh (120px < r < 310px) xoay nhẹ ngược chiều.
    """
    cx, cy = W * 0.721, H * 0.496
    dx = X_GRID - cx
    dy = Y_GRID - cy
    r = np.sqrt(dx * dx + dy * dy) + 1e-5
    theta = np.arctan2(dy, dx)

    # 1. Inner Swirling Golden-Amber Bio-Gel Vortex strictly inside the jar rim (r <= 92px)
    gel_core = smoothstep_down(20.0, 92.0, r)
    swirl_angle = (p_act3 - 0.25) * 1.15 * gel_core

    # 2. Outer Flower Petals strictly within the flower radius (120px <= r <= 315px)
    petal_ring = smoothstep(115.0, 155.0, r) * smoothstep_down(250.0, 325.0, r)
    petal_angle = -(p_act3 - 0.25) * 0.15 * petal_ring
    radial_scale = 1.0 - (p_act3 - 0.25) * 0.048 * petal_ring

    total_ang = theta - (swirl_angle + petal_angle)
    r_src = r * radial_scale

    src_x = cx + r_src * np.cos(total_ang)
    src_y = cy + r_src * np.sin(total_ang)

    warped = bilinear_sample(kf3, src_x, src_y)

    # Subtle golden caustic shimmer strictly inside the gel core (r <= 88px)
    shimmer = (np.sin(theta * 3.0 + p_act3 * 7.0 - r * 0.06) * 0.5 + 0.5) * gel_core
    warped = warped + shimmer[..., np.newaxis] * np.array([18.0, 12.0, 3.0], dtype=np.float32)
    return warped


def draw_particles_and_shield_hud(img_pil, p):
    canvas = img_pil.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")

    # 1. Floating Golden Bio-Active Micro-Droplets in Act II
    part_intensity = smoothstep(0.30, 0.40, p) * smoothstep_down(0.60, 0.68, p)
    if part_intensity > 0.02:
        cx_p = W * 0.725
        cy_p = H * 0.31
        for i in range(18):
            seed = i * 1.6180339
            ang = seed * 6.283 + p * 4.0 * (1 if i % 2 == 0 else -1)
            rx = 42.0 + (i % 6) * 22.0
            ry = 16.0 + (i % 5) * 14.0
            drift_y = -((p * 170.0 + i * 15.0) % 75.0) + 18.0
            px = cx_p + math.cos(ang) * rx
            py = cy_p + math.sin(ang) * ry + drift_y
            rad = 1.8 + (i % 3) * 1.2
            alpha = int(165 * part_intensity * (0.45 + 0.55 * math.sin(p * 12.0 + i)))
            if alpha > 8:
                draw.ellipse([px - rad * 2.0, py - rad * 2.0, px + rad * 2.0, py + rad * 2.0], fill=(238, 182, 68, alpha // 4))
                draw.ellipse([px - rad, py - rad, px + rad, py + rad], fill=(255, 232, 158, alpha))

    # 2. Act III 360° Bio-Shield Geometric Rings around Top-Down Flower
    shield_int = smoothstep(0.68, 0.76, p) * smoothstep_down(0.92, 0.99, p)
    if shield_int > 0.02:
        cx_s, cy_s = W * 0.721, H * 0.496
        base_alpha = int(145 * shield_int)
        for ring_i, r_ring in enumerate([148, 236, 306]):
            a_ring = max(18, base_alpha - ring_i * 36)
            draw.ellipse(
                [cx_s - r_ring, cy_s - r_ring, cx_s + r_ring, cy_s + r_ring],
                outline=(184, 138, 64, a_ring),
                width=2 if ring_i == 0 else 1,
            )
            ang_n = p * 5.2 * (1 if ring_i % 2 == 0 else -1) + ring_i * 2.09
            nx = cx_s + math.cos(ang_n) * r_ring
            ny = cy_s + math.sin(ang_n) * r_ring
            draw.ellipse([nx - 4, ny - 4, nx + 4, ny + 4], fill=(208, 158, 68, min(255, a_ring + 40)))
            draw.ellipse([nx - 9, ny - 9, nx + 9, ny + 9], outline=(208, 158, 68, a_ring // 2), width=1)

    canvas.alpha_composite(overlay)
    return canvas.convert("RGB")


def main():
    t0 = time.time()
    os.makedirs(PACKS_DIR, exist_ok=True)
    os.makedirs(PREVIEW_DIR, exist_ok=True)

    kf1_img = Image.open(os.path.join(KEYFRAMES_DIR, "keyframe_1_bloom.jpg")).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    kf2_img = Image.open(os.path.join(KEYFRAMES_DIR, "keyframe_2_levitate.jpg")).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    kf3_img = Image.open(os.path.join(KEYFRAMES_DIR, "keyframe_3_topdown.jpg")).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)

    kf1 = np.array(kf1_img, dtype=np.float32)
    kf2 = np.array(kf2_img, dtype=np.float32)
    kf3 = np.array(kf3_img, dtype=np.float32)

    bg_ref = np.median(kf1[:, : int(W * 0.35), :], axis=(0, 1))
    for arr in (kf2, kf3):
        bg_cur = np.median(arr[:, : int(W * 0.35), :], axis=(0, 1))
        diff = bg_ref - bg_cur
        arr += diff * 0.88
        np.clip(arr, 0, 255, out=arr)

    print(f"[build_film] Synthesizing {N_FRAMES} clean photorealistic frames ({W}x{H})...")
    webp_blobs = []
    startup_blobs = []
    startup_indices = []

    for idx in range(N_FRAMES):
        p = idx / float(N_FRAMES - 1)

        p1 = np.clip(p / 0.34, 0.0, 1.0)
        p2 = np.clip((p - 0.28) / 0.40, 0.0, 1.0)
        p3 = np.clip((p - 0.62) / 0.38, 0.0, 1.0)

        # Crisp 8% scroll transition windows so Acts I, II, and III are 100% ghost-free
        w_1_to_2 = smoothstep(0.27, 0.35, p)
        w_2_to_3 = smoothstep(0.62, 0.70, p)

        if w_1_to_2 <= 0.001:
            frame_arr = warp_act1_bloom(kf1, p1, 0.0)
        elif w_1_to_2 < 0.999 and w_2_to_3 <= 0.001:
            f1 = warp_act1_bloom(kf1, p1, w_1_to_2)
            f2 = warp_act2_levitate(kf2, p2, 1.0 - w_1_to_2)
            frame_arr = f1 * (1.0 - w_1_to_2) + f2 * w_1_to_2
        elif w_2_to_3 <= 0.001:
            frame_arr = warp_act2_levitate(kf2, p2, 0.0)
        elif w_2_to_3 < 0.999:
            f2 = warp_act2_levitate(kf2, p2, 0.0)
            f3 = warp_act3_topdown(kf3, p3)
            frame_arr = f2 * (1.0 - w_2_to_3) + f3 * w_2_to_3
        else:
            frame_arr = warp_act3_topdown(kf3, p3)

        pil_img = Image.fromarray(np.clip(frame_arr, 0, 255).astype(np.uint8))
        pil_img = draw_particles_and_shield_hud(pil_img, p)

        buf = io.BytesIO()
        pil_img.save(buf, format="WEBP", quality=86, method=4)
        blob = buf.getvalue()
        webp_blobs.append(blob)

        if idx % 4 == 0 or idx == N_FRAMES - 1:
            s_buf = io.BytesIO()
            pil_img.resize((960, 540), resample=Image.Resampling.BILINEAR).save(s_buf, format="WEBP", quality=78)
            startup_blobs.append(s_buf.getvalue())
            startup_indices.append(idx)

        if idx in (0, 20, 68, 85, 125, 150):
            pil_img.save(os.path.join(PREVIEW_DIR, f"frame_{idx:03d}.png"))

        if (idx + 1) % 40 == 0 or idx == N_FRAMES - 1:
            print(f"  -> Synthesized {idx + 1}/{N_FRAMES} frames ({time.time() - t0:.1f}s)")

    s00_path = os.path.join(PACKS_DIR, "s_00.bin")
    s00_offsets = []
    curr = 0
    with open(s00_path, "wb") as f:
        for idx, blob in zip(startup_indices, startup_blobs):
            f.write(blob)
            s00_offsets.append({"i": idx, "o": curr, "l": len(blob)})
            curr += len(blob)

    half = N_FRAMES // 2
    chunks = [
        ("c_0000.bin", 0, half),
        ("c_0001.bin", half, N_FRAMES),
    ]
    chunk_manifest = []
    for fname, start_i, end_i in chunks:
        c_path = os.path.join(PACKS_DIR, fname)
        c_offsets = []
        curr = 0
        with open(c_path, "wb") as f:
            for idx in range(start_i, end_i):
                blob = webp_blobs[idx]
                f.write(blob)
                c_offsets.append({"i": idx, "o": curr, "l": len(blob)})
                curr += len(blob)
        chunk_manifest.append({"file": f"packs/frames/{fname}", "frames": c_offsets, "bytes": curr})

    header_path = os.path.join(PACKS_DIR, "h.bin")
    with open(header_path, "wb") as f:
        f.write(struct.pack("<4sIIII", b"PK24", 3, W, H, N_FRAMES))

    lut = [max(0, min(N_FRAMES - 1, int(round((step / 1000.0) * (N_FRAMES - 1))))) for step in range(1001)]
    fmap_data = {
        "engine": "galatea-rife-pk247-v3.3",
        "width": W,
        "height": H,
        "desktop_n": N_FRAMES,
        "startup": {"file": "packs/frames/s_00.bin", "frames": s00_offsets},
        "chunks": chunk_manifest,
        "lut": lut,
    }

    with open(os.path.join(OUT_DIR, "framemap.js"), "w", encoding="utf-8") as f:
        f.write("// Generated by tools/build_film.py — RIFE motion-equalized ImageBitmap frame pack\n")
        f.write(f"window.__FMAP = {json.dumps(fmap_data, separators=(',', ':'))};\n")

    total_kb = (os.path.getsize(s00_path) + sum(c["bytes"] for c in chunk_manifest)) / 1024.0
    print(f"[build_film] Completed in {time.time() - t0:.1f}s! Total binary packs: {total_kb:.1f} KB")


if __name__ == "__main__":
    main()
