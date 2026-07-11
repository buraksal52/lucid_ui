#!/usr/bin/env python3
"""
Design Signals — metric comparison engine.
Compares two UI screenshots (variants of the SAME screen) and outputs
raw + normalized metrics as JSON. No verdicts, no LLM calls — pure
deterministic measurement.
"""

import sys
import json
import cv2
import numpy as np
import pytesseract


# ---------- 5.1 Contrast (WCAG 2.1) ----------
def relative_luminance(rgb):
    srgb = [c / 255.0 for c in rgb]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast_ratio(rgb1, rgb2):
    l1, l2 = relative_luminance(rgb1), relative_luminance(rgb2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def analyze_contrast(img, ocr_data):
    ratios = []
    h, w = img.shape[:2]
    n_boxes = len(ocr_data['text'])
    for i in range(n_boxes):
        if int(ocr_data['conf'][i]) < 60 or not ocr_data['text'][i].strip():
            continue
        x, y, bw, bh = (ocr_data['left'][i], ocr_data['top'][i],
                         ocr_data['width'][i], ocr_data['height'][i])
        region = img[max(0, y):min(h, y + bh), max(0, x):min(w, x + bw)]
        if region.size == 0:
            continue
        text_color = region.reshape(-1, 3).mean(axis=0)[::-1]

        pad = 6
        by0, by1 = max(0, y - pad), min(h, y + bh + pad)
        bx0, bx1 = max(0, x - pad), min(w, x + bw + pad)
        bg_region = img[by0:by1, bx0:bx1]
        bg_color = bg_region.reshape(-1, 3).mean(axis=0)[::-1]

        ratio = contrast_ratio(text_color.tolist(), bg_color.tolist())
        ratios.append(round(ratio, 2))

    avg_ratio = round(float(np.mean(ratios)), 2) if ratios else None
    below_aa = sum(1 for r in ratios if r < 4.5)
    return {
        "averageContrastRatio": avg_ratio,
        "regionsAnalyzed": len(ratios),
        "regionsBelowAAThreshold": below_aa,
        "source": "WCAG 2.1 AA (4.5:1 normal text)",
    }


# ---------- 5.2 Visual Complexity (Edge Density) ----------
def analyze_clutter(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    edge_density = float(np.count_nonzero(edges)) / edges.size
    return {
        "edgeDensity": round(edge_density, 4),
        "source": "Rosenholtz, Li & Nakano (2007) - Edge Density proxy",
    }


# ---------- 5.3 Element Detection (Hick's / Fitts's threshold) ----------
def analyze_elements(img, ocr_data):
    """
    Element count combines two sources:
    1. Contour-based detection (visual/interactive elements: buttons, inputs, icons)
    2. OCR-based text blocks (metin blokları da arayüz elementi olarak sayılır)
    Hick's Law is computed over the combined count.
    Source: Hick (1952), Fitts (1954), WCAG touch target 44x44px.
    """
    h, w = img.shape[:2]
    img_area = h * w
    elements = []
    small_targets = 0

    # --- Kaynak 1: Kontur tabanlı elementler ---
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        area = cw * ch
        if area < 20 * 20 or area > 0.30 * img_area:
            continue
        elements.append({"x": x, "y": y, "w": cw, "h": ch, "source": "contour"})
        if cw < 44 or ch < 44:
            small_targets += 1

    contour_count = len(elements)

    # --- Kaynak 2: OCR tabanlı metin blokları ---
    # Her kelime kutusu bir arayüz elementi olarak sayılır.
    # Kontur filtreleriyle aynı boyut kısıtları uygulanır (20x20px min, %30 max).
    ocr_element_count = 0
    n_boxes = len(ocr_data['text'])
    for i in range(n_boxes):
        if int(ocr_data['conf'][i]) < 60 or not ocr_data['text'][i].strip():
            continue
        bw = ocr_data['width'][i]
        bh = ocr_data['height'][i]
        bx = ocr_data['left'][i]
        by = ocr_data['top'][i]
        area = bw * bh
        if area < 20 * 20 or area > 0.30 * img_area:
            continue
        elements.append({"x": bx, "y": by, "w": bw, "h": bh, "source": "ocr"})
        ocr_element_count += 1
        if bw < 44 or bh < 44:
            small_targets += 1

    n = len(elements)
    b_ms = 150
    # Hick's Law: T = b * log2(n+1)
    # n = combined element count (contour + OCR text blocks)
    hicks_estimate_ms = round(b_ms * np.log2(n + 1), 1)

    elements_meta = {
        "detectedElementCount": n,
        "contourBasedCount": contour_count,
        "ocrBasedCount": ocr_element_count,
        "hicksLawEstimateMs": hicks_estimate_ms,
        "isProxyMetric": True,
        "smallTargetsBelow44px": small_targets,
        "source": "Hick's Law (T = b * log2(n+1), b=150ms); Fitts threshold 44x44px; element count = contour + OCR text blocks",
    }
    return elements_meta, elements


# ---------- Fitts's Law - full Index of Difficulty ----------
def analyze_fitts_full(elements):
    if len(elements) < 2:
        return {
            "averageIndexOfDifficulty": None,
            "elementsConsidered": 0,
            "isProxyMetric": True,
            "source": "Fitts's Law (ID = log2(2D/W)), Fitts (1954)",
        }

    centroids = [(e["x"] + e["w"] / 2, e["y"] + e["h"] / 2) for e in elements]
    ids = []
    for i, (cx, cy) in enumerate(centroids):
        dists = [
            np.hypot(cx - ox, cy - oy)
            for j, (ox, oy) in enumerate(centroids) if j != i
        ]
        nearest_d = min(dists)
        w = max(1, min(elements[i]["w"], elements[i]["h"]))
        if nearest_d <= 0:
            continue
        ids.append(np.log2((2 * nearest_d) / w))

    avg_id = round(float(np.mean(ids)), 2) if ids else None
    return {
        "averageIndexOfDifficulty": avg_id,
        "elementsConsidered": len(ids),
        "isProxyMetric": True,
        "source": "Fitts's Law (ID = log2(2D/W)), Fitts (1954)",
    }


# ---------- 5.4 Miller's Law (Grouping) ----------
def analyze_groups(elements, img_shape):
    if not elements:
        return {"estimatedGroupCount": 0, "isProxyMetric": True,
                "source": "Miller's Law (7+-2), Miller (1956)"}

    h, w = img_shape[:2]
    img_diag = np.hypot(h, w)
    centroids = [(e["x"] + e["w"] / 2, e["y"] + e["h"] / 2) for e in elements]
    n = len(centroids)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    threshold = img_diag * 0.08
    for i in range(n):
        for j in range(i + 1, n):
            d = np.hypot(centroids[i][0] - centroids[j][0], centroids[i][1] - centroids[j][1])
            if d < threshold:
                union(i, j)

    group_count = len(set(find(i) for i in range(n)))
    return {
        "estimatedGroupCount": group_count,
        "isProxyMetric": True,
        "source": "Miller's Law (7+-2), Miller (1956)",
    }


# ---------- 5.5 Text Density ----------
def analyze_text_density(img, ocr_data):
    h, w = img.shape[:2]
    total_area = h * w
    text_area = 0
    heights = []
    n_boxes = len(ocr_data['text'])
    for i in range(n_boxes):
        if int(ocr_data['conf'][i]) < 60 or not ocr_data['text'][i].strip():
            continue
        text_area += ocr_data['width'][i] * ocr_data['height'][i]
        heights.append(ocr_data['height'][i])

    density = text_area / total_area if total_area else 0
    font_diversity = round(float(np.std(heights)), 2) if len(heights) > 1 else 0.0

    return {
        "textDensityRatio": round(density, 4),
        "fontSizeDiversityProxy": font_diversity,
        "wordsDetected": len(heights),
    }


# ---------- 5.6 Whitespace & Alignment ----------
def analyze_whitespace_alignment(img, elements):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    block = 20
    low_variance_blocks = 0
    total_blocks = 0

    for y in range(0, h - block, block):
        for x in range(0, w - block, block):
            cell = gray[y:y + block, x:x + block]
            total_blocks += 1
            if np.var(cell) < 100:
                low_variance_blocks += 1

    whitespace_ratio = low_variance_blocks / total_blocks if total_blocks else 0

    if len(elements) >= 2:
        xs = [e["x"] for e in elements]
        ys = [e["y"] for e in elements]
        x_align = np.std(xs) / w
        y_align = np.std(ys) / h
        alignment_variance = round(float((x_align + y_align) / 2), 4)
    else:
        alignment_variance = None

    return {
        "whitespaceRatio": round(whitespace_ratio, 4),
        "alignmentVariance": alignment_variance,
        "source": "Whitespace/Alignment proxy (low-variance block ratio; element position variance)",
    }


# ---------- Colorfulness (Hasler & Suesstrunk, 2003) ----------
def analyze_colorfulness(img):
    b, g, r = cv2.split(img.astype("float"))
    rg = r - g
    yb = 0.5 * (r + g) - b
    std_rg, std_yb = np.std(rg), np.std(yb)
    mean_rg, mean_yb = np.mean(rg), np.mean(yb)
    colorfulness = np.sqrt(std_rg ** 2 + std_yb ** 2) + 0.3 * np.sqrt(mean_rg ** 2 + mean_yb ** 2)
    return {
        "colorfulnessScore": round(float(colorfulness), 2),
        "source": "Hasler & Suesstrunk (2003) - Measuring Colourfulness in Natural Images",
    }


# ---------- Visual Balance / Symmetry ----------
def analyze_visual_balance(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype("float")
    h, w = gray.shape
    left, right = gray[:, :w // 2], gray[:, w // 2:]
    top, bottom = gray[:h // 2, :], gray[h // 2:, :]

    lr_diff = abs(float(np.mean(left)) - float(np.mean(right))) / 255.0
    tb_diff = abs(float(np.mean(top)) - float(np.mean(bottom))) / 255.0
    asymmetry_score = round((lr_diff + tb_diff) / 2, 4)

    return {
        "asymmetryScore": asymmetry_score,
        "source": "Visual balance proxy (left/right, top/bottom luminance difference)",
    }


# ---------- Normalization (0-100, documented bounds) ----------
def normalize(value, low, high, invert=False):
    if value is None:
        return None
    score = (value - low) / (high - low) * 100
    score = max(0, min(100, score))
    return round(100 - score if invert else score, 1)


def normalize_group_count(n):
    if n is None:
        return None
    score = max(0, 100 - abs(n - 7) * 15)
    return round(float(score), 1)


def normalize_metrics(raw):
    return {
        "contrast": normalize(raw["contrast"]["averageContrastRatio"] or 1, 1, 7),
        "clutter": normalize(raw["clutter"]["edgeDensity"], 0.02, 0.25, invert=True),
        "textDensity": normalize(raw["textDensity"]["textDensityRatio"], 0.02, 0.30, invert=True),
        "elementSize": normalize(raw["elements"]["smallTargetsBelow44px"], 0, 10, invert=True),
        "groupCount": normalize_group_count(raw["groups"]["estimatedGroupCount"]),
    }


WEIGHTS = {
    "general": {"clutter": 0.30, "contrast": 0.25, "textDensity": 0.20, "elementSize": 0.25},
    "expert":  {"clutter": 0.15, "contrast": 0.25, "textDensity": 0.10, "elementSize": 0.20, "groupCount": 0.30},
}


def weighted_score(normalized, context):
    weights = WEIGHTS.get(context, WEIGHTS["general"])
    total = sum((normalized.get(k) or 0) * w for k, w in weights.items())
    return round(total, 1)


# ---------- Per-image pipeline ----------
def analyze_image(path):
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"Could not read image: {path}")

    ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    elements_meta, elements = analyze_elements(img, ocr_data)

    raw = {
        "contrast": analyze_contrast(img, ocr_data),
        "clutter": analyze_clutter(img),
        "elements": elements_meta,
        "groups": analyze_groups(elements, img.shape),
        "textDensity": analyze_text_density(img, ocr_data),
        "whitespaceAlignment": analyze_whitespace_alignment(img, elements),
    }

    additional = {
        "colorfulness": analyze_colorfulness(img),
        "fittsFullIndexOfDifficulty": analyze_fitts_full(elements),
        "visualBalance": analyze_visual_balance(img),
    }

    normalized = normalize_metrics(raw)
    return {"raw": raw, "normalized": normalized, "additionalSignals": additional}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: design_metrics.py <imageA> [imageB] [context]"}))
        sys.exit(1)

    args = sys.argv[1:]
    context = "general"
    if args and args[-1] in WEIGHTS:
        context = args[-1]
        args = args[:-1]

    if len(args) == 1:
        result = analyze_image(args[0])
        output = {
            "mode": "single",
            "context": context,
            "design": {**result, "weightedScore": weighted_score(result["normalized"], context)},
            "note": "This is a single-design signal report compared against reference thresholds, not a verdict.",
        }
    elif len(args) == 2:
        result_a = analyze_image(args[0])
        result_b = analyze_image(args[1])
        output = {
            "mode": "comparison",
            "context": context,
            "designA": {**result_a, "weightedScore": weighted_score(result_a["normalized"], context)},
            "designB": {**result_b, "weightedScore": weighted_score(result_b["normalized"], context)},
            "note": "These are signals for review, not verdicts. Compare relative differences only.",
        }
    else:
        print(json.dumps({"error": "Usage: design_metrics.py <imageA> [imageB] [context]"}))
        sys.exit(1)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
