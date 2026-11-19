"""Тесты вычисления констант и константных выражений."""

import pytest

from confjson.errors import ConfigEvalError
from confjson.evaluator import Evaluator
from confjson.grammar import parse

ERROR_POSITION = (2, 4)


def run(text):
    """Транслирует программу и возвращает словарь результата."""
    return Evaluator().run(parse(text))


def test_number_constant():
    """Объявление числовой константы."""
    assert run("0b1010 -> A;") == {"A": 10}


def test_array_constant():
    """Объявление массива, в том числе вложенного."""
    assert run("[0b1; [0b10; []]] -> A;") == {"A": [1, [2, []]]}


def test_declaration_order_is_kept():
    """Порядок ключей совпадает с порядком объявлений."""
    assert list(run("0b1 -> B;\n0b1 -> A;")) == ["B", "A"]


def test_reference_to_number():
    """``^{ИМЯ}`` подставляет значение константы."""
    assert run("0b111 -> A;\n^{A} -> B;") == {"A": 7, "B": 7}


def test_reference_to_array():
    """Константа-массив подставляется целиком."""
    result = run("[0b1; 0b10] -> A;\n[^{A}; 0b0] -> B;")
    assert result["B"] == [[1, 2], 0]


@pytest.mark.parametrize(
    "expr, expected",
    [
        ("A + 1", 6),
        ("A - 0b111", -2),
        ("A * 3", 15),
        ("1 + 2 * 3", 7),
        ("(1 + 2) * 3", 9),
        ("10 - 3 - 2", 5),
        ("2 * 3 * 4", 24),
    ],
)
def test_arithmetic(expr, expected):
    """Сложение, вычитание, умножение и приоритеты (A = 5)."""
    assert run(f"0b101 -> A;\n^{{{expr}}} -> R;")["R"] == expected


@pytest.mark.parametrize(
    "expr, expected",
    [
        ("mod(10, 3)", 1),
        ("mod(0b1000, 0b11)", 2),
        ("mod(A * 2, 4)", 2),
        ("max(1, 7, 3)", 7),
        ("max(A)", 5),
        ("max(L)", 9),
        ("max(L, [0b1010; [0b1011]], 2)", 11),
        ("max(mod(A, 3), 1) + 1", 3),
        ("mod(max(L), A)", 4),
    ],
)
def test_functions(expr, expected):
    """Функции mod() и max(), их вложенность (A = 5, L = [1, 9, 4])."""
    text = (
        "0b101 -> A;\n[0b1; 0b1001; 0b100] -> L;\n"
        f"^{{{expr}}} -> R;"
    )
    assert run(text)["R"] == expected


def test_chain_of_constants():
    """Константа может использовать предыдущие вычисленные константы."""
    text = "0b10 -> A;\n^{A * 2} -> B;\n^{A + B} -> C;"
    assert run(text) == {"A": 2, "B": 4, "C": 6}


def test_private_constants_are_hidden():
    """Имена с префиксом ``_`` используются, но не выводятся."""
    result = run("0b11 -> _K;\n^{_K * 2} -> A;")
    assert result == {"A": 6}


def test_expression_in_nested_array():
    """Выражения внутри вложенных массивов вычисляются."""
    text = "0b10 -> A;\n[[^{A + 1}; [^{max(A, 9)}]]] -> B;"
    assert run(text)["B"] == [[3, [9]]]


@pytest.mark.parametrize(
    "text, fragment",
    [
        ("^{X + 1} -> A;", "неизвестная константа X"),
        ("^{A} -> A;", "неизвестная константа A"),
        ("0b1 -> A;\n0b10 -> A;", "уже объявлена"),
        ("^{mod(1, 0)} -> A;", "деление на ноль"),
        ("^{mod(1)} -> A;", "mod() принимает 2"),
        ("^{mod(1, 2, 3)} -> A;", "mod() принимает 2"),
        ("^{mod([0b1], 2)} -> A;", "mod() ожидает число"),
        ("^{max([])} -> A;", "max() вызвана без чисел"),
        ("[0b1] -> L;\n^{L + 1} -> A;", "ожидает число"),
        ("[0b1] -> L;\n^{2 * L} -> A;", "ожидает число"),
    ],
)
def test_eval_errors(text, fragment):
    """Семантические ошибки сообщаются с понятным текстом."""
    with pytest.raises(ConfigEvalError) as info:
        run(text)
    assert fragment in str(info.value)


def test_eval_error_position():
    """Ошибка вычисления указывает на место во входном тексте."""
    with pytest.raises(ConfigEvalError) as info:
        run("0b1 -> A;\n[^{B}] -> C;")
    assert (info.value.line, info.value.col) == ERROR_POSITION
