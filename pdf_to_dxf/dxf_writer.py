"""Small ASCII DXF writer for simple 2D geometry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


INSUNITS = {
    "unitless": 0,
    "inch": 1,
    "mm": 4,
    "pt": 0,
}

TEXT_REPLACEMENTS = {
    "\u00b0": "deg",
    "\u00b5": "u",
    "\u03bc": "u",
    "\u03a9": "Ohm",
    "\u03c9": "ohm",
    "\u2265": ">=",
    "\u2264": "<=",
    "\u00b1": "+/-",
    "\u00d7": "x",
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
}


@dataclass(frozen=True)
class Layer:
    name: str
    color: int = 7


def clean_layer_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value.strip())
    return cleaned[:255] or "0"


def clean_text(value: str) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").replace("\\", "\\\\")
    parts: list[str] = []
    for char in text:
        if char in TEXT_REPLACEMENTS:
            parts.append(TEXT_REPLACEMENTS[char])
            continue
        codepoint = ord(char)
        if 32 <= codepoint <= 126:
            parts.append(char)
        elif char == "\t":
            parts.append(" ")
        else:
            parts.append("?")
    return "".join(parts)


def fmt(value: float) -> str:
    rounded = round(float(value), 6)
    text = f"{rounded:.6f}".rstrip("0").rstrip(".")
    return text if text and text != "-0" else "0"


class DxfWriter:
    """Write a conservative ASCII DXF R12 with LINE, POLYLINE, and TEXT."""

    def __init__(self, unit: str = "mm") -> None:
        self.unit = unit if unit in INSUNITS else "unitless"
        self.layers: dict[str, Layer] = {"0": Layer("0", 7)}
        self.entities: list[list[str]] = []

    def ensure_layer(self, name: str, color: int = 7) -> str:
        layer_name = clean_layer_name(name)
        if layer_name not in self.layers:
            self.layers[layer_name] = Layer(layer_name, color)
        return layer_name

    def add_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        layer: str = "PDF_VECTOR",
        color: int | None = None,
    ) -> None:
        layer_name = self.ensure_layer(layer)
        codes = [
            "0",
            "LINE",
            "8",
            layer_name,
            "10",
            fmt(start[0]),
            "20",
            fmt(start[1]),
            "30",
            "0",
            "11",
            fmt(end[0]),
            "21",
            fmt(end[1]),
            "31",
            "0",
        ]
        if color is not None:
            codes.extend(["62", str(int(color))])
        self.entities.append(codes)

    def add_lwpolyline(
        self,
        points: Iterable[tuple[float, float]],
        layer: str = "PDF_VECTOR",
        closed: bool = False,
        color: int | None = None,
    ) -> None:
        clean_points = list(points)
        if len(clean_points) < 2:
            return
        layer_name = self.ensure_layer(layer)
        codes = [
            "0",
            "POLYLINE",
            "8",
            layer_name,
            "66",
            "1",
            "70",
            "1" if closed else "0",
            "10",
            "0",
            "20",
            "0",
            "30",
            "0",
        ]
        if color is not None:
            codes.extend(["62", str(int(color))])
        for x, y in clean_points:
            codes.extend(
                [
                    "0",
                    "VERTEX",
                    "8",
                    layer_name,
                    "10",
                    fmt(x),
                    "20",
                    fmt(y),
                    "30",
                    "0",
                ]
            )
        codes.extend(["0", "SEQEND", "8", layer_name])
        self.entities.append(codes)

    def add_text(
        self,
        text: str,
        insert: tuple[float, float],
        height: float,
        layer: str = "PDF_TEXT",
        rotation: float = 0,
        color: int | None = None,
    ) -> None:
        cleaned = clean_text(text)
        if not cleaned.strip() or height <= 0:
            return
        layer_name = self.ensure_layer(layer)
        codes = [
            "0",
            "TEXT",
            "8",
            layer_name,
            "10",
            fmt(insert[0]),
            "20",
            fmt(insert[1]),
            "30",
            "0",
            "40",
            fmt(height),
            "1",
            cleaned,
            "50",
            fmt(rotation),
            "7",
            "Standard",
        ]
        if color is not None:
            codes.extend(["62", str(int(color))])
        self.entities.append(codes)

    def dumps(self) -> str:
        parts: list[str] = []
        parts.extend(self._section("HEADER", self._header()))
        parts.extend(self._section("TABLES", self._tables()))
        parts.extend(self._section("BLOCKS", []))
        parts.extend(self._section("ENTITIES", self._entities()))
        parts.extend(["0", "EOF"])
        return "\n".join(parts) + "\n"

    def to_bytes(self) -> bytes:
        return self.dumps().encode("utf-8")

    def _section(self, name: str, body: list[str]) -> list[str]:
        return ["0", "SECTION", "2", name, *body, "0", "ENDSEC"]

    def _header(self) -> list[str]:
        return [
            "9",
            "$ACADVER",
            "1",
            "AC1009",
        ]

    def _tables(self) -> list[str]:
        return [
            *self._ltype_table(),
            *self._layer_table(),
            *self._style_table(),
        ]

    def _ltype_table(self) -> list[str]:
        return [
            "0",
            "TABLE",
            "2",
            "LTYPE",
            "70",
            "1",
            "0",
            "LTYPE",
            "2",
            "CONTINUOUS",
            "70",
            "0",
            "3",
            "Solid line",
            "72",
            "65",
            "73",
            "0",
            "40",
            "0",
            "0",
            "ENDTAB",
        ]

    def _layer_table(self) -> list[str]:
        codes = ["0", "TABLE", "2", "LAYER", "70", str(len(self.layers))]
        for layer in self.layers.values():
            codes.extend(
                [
                    "0",
                    "LAYER",
                    "2",
                    layer.name,
                    "70",
                    "0",
                    "62",
                    str(layer.color),
                    "6",
                    "CONTINUOUS",
                ]
            )
        codes.extend(["0", "ENDTAB"])
        return codes

    def _style_table(self) -> list[str]:
        return [
            "0",
            "TABLE",
            "2",
            "STYLE",
            "70",
            "1",
            "0",
            "STYLE",
            "2",
            "Standard",
            "70",
            "0",
            "40",
            "0",
            "41",
            "1",
            "50",
            "0",
            "71",
            "0",
            "42",
            "2.5",
            "3",
            "txt",
            "4",
            "",
            "0",
            "ENDTAB",
        ]

    def _entities(self) -> list[str]:
        codes: list[str] = []
        for entity in self.entities:
            codes.extend(entity)
        return codes
