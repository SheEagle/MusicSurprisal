from __future__ import annotations

import re


def simplify_chord(chord: object, mode: str = "function") -> str:
    """Map DCML Roman-numeral labels to compact harmony labels."""
    if mode == "raw":
        return str(chord) if chord not in (None, "") else "NA"
    label = normalize_chord_label(chord)
    if label == "NA":
        return "other" if mode == "function" else "NA"

    if is_augmented_sixth(label):
        return "D" if mode == "function" else "AUG6:aug"

    root = roman_root(label)
    if root is None:
        return "other" if mode == "function" else "other"
    degree, quality = root
    if mode == "function":
        return roman_function(degree)
    if mode == "degree_quality":
        return f"{degree}:{quality}"
    raise ValueError(f"Unknown chord mode: {mode}")


def normalize_chord_label(chord: object) -> str:
    label = str(chord or "").strip()
    if not label or label.upper() in {"NA", "NAN", "NONE", "@NONE"}:
        return "NA"
    label = label.split("|", 1)[0]
    label = label.split("/", 1)[0]
    for marker in ("{", "}", "[", "]", "\\"):
        label = label.replace(marker, "")
    label = label.strip()
    return label or "NA"


def is_augmented_sixth(label: str) -> bool:
    return label.lower().startswith(("ger", "it", "fr"))


def roman_root(label: str) -> tuple[str, str] | None:
    match = re.match(r"^[#b]*(vii|VII|vi|VI|iv|IV|iii|III|ii|II|v|V|i|I)", label)
    if not match:
        return None
    raw = match.group(1)
    degree = raw.upper()
    suffix = label[match.end() :].lower()
    if "o" in suffix or "%" in suffix:
        quality = "dim"
    elif raw[0].isupper():
        quality = "maj"
    else:
        quality = "min"
    return degree, quality


def roman_function(degree: str) -> str:
    if degree in {"I", "III", "VI"}:
        return "T"
    if degree in {"II", "IV"}:
        return "S"
    if degree in {"V", "VII"}:
        return "D"
    return "other"
