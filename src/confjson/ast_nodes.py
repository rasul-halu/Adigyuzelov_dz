"""Узлы абстрактного синтаксического дерева учебного языка."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Position:
    """Позиция узла во входном тексте (нумерация с единицы)."""

    line: int = 0
    col: int = 0


@dataclass
class Number:
    """Числовой литерал, например ``0b101``."""

    value: int
    pos: Position = field(default_factory=Position)


@dataclass
class Array:
    """Массив ``[ значение; значение; ... ]``."""

    items: List[object]
    pos: Position = field(default_factory=Position)


@dataclass
class ConstRef:
    """Обращение к константе по имени внутри выражения."""

    name: str
    pos: Position = field(default_factory=Position)


@dataclass
class BinOp:
    """Бинарная операция ``+``, ``-`` или ``*``."""

    op: str
    left: object
    right: object
    pos: Position = field(default_factory=Position)


@dataclass
class Call:
    """Вызов встроенной функции ``mod()`` или ``max()``."""

    func: str
    args: List[object]
    pos: Position = field(default_factory=Position)


@dataclass
class ConstExpr:
    """Константное выражение ``^{ ... }``, вычисляемое при трансляции."""

    expr: object
    pos: Position = field(default_factory=Position)


@dataclass
class Declaration:
    """Объявление константы ``значение -> ИМЯ;``."""

    value: object
    name: str
    pos: Position = field(default_factory=Position)


@dataclass
class Program:
    """Вся программа — последовательность объявлений констант."""

    declarations: List[Declaration]
