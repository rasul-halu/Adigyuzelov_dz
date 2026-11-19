"""Тесты синтаксического разбора всех конструкций учебного языка."""

import pytest

from confjson import ast_nodes as ast
from confjson.errors import ConfigSyntaxError
from confjson.grammar import parse

ERROR_POSITION = (2, 9)


def first_value(text):
    """Возвращает значение первого объявления в программе."""
    return parse(text).declarations[0].value


def test_empty_program():
    """Пустой текст — корректная программа без объявлений."""
    assert parse("").declarations == []


def test_only_comment():
    """Программа может состоять только из комментария."""
    assert parse("/* только комментарий */").declarations == []


def test_multiline_comment_is_ignored():
    """Многострочный комментарий пропускается в любом месте."""
    text = "/*\nЭто многострочный\nкомментарий\n*/\n0b1 /* x */ -> A;"
    program = parse(text)
    assert program.declarations[0].name == "A"


@pytest.mark.parametrize(
    "literal, expected",
    [("0b0", 0), ("0b1", 1), ("0B101", 5), ("0b11111111", 255)],
)
def test_binary_numbers(literal, expected):
    """Двоичные числа в обоих регистрах префикса."""
    node = first_value(f"{literal} -> A;")
    assert isinstance(node, ast.Number)
    assert node.value == expected


def test_empty_array():
    """Пустой массив ``[]``."""
    node = first_value("[] -> A;")
    assert isinstance(node, ast.Array)
    assert node.items == []


def test_array_of_numbers():
    """Массив чисел с разделителем ``;``."""
    node = first_value("[ 0b1; 0b10; 0b11 ] -> A;")
    assert [item.value for item in node.items] == [1, 2, 3]


def test_nested_arrays():
    """Массивы могут быть вложены друг в друга."""
    node = first_value("[[0b1; [0b10]]; []] -> A;")
    inner = node.items[0]
    assert isinstance(inner.items[1], ast.Array)
    assert node.items[1].items == []


@pytest.mark.parametrize(
    "name", ["A", "_A", "MAX_SIZE", "Port8080", "_", "Aa_9"]
)
def test_valid_names(name):
    """Имена вида ``[_A-Z][_a-zA-Z0-9]*``."""
    assert parse(f"0b1 -> {name};").declarations[0].name == name


def test_several_declarations():
    """Программа — последовательность объявлений."""
    program = parse("0b1 -> A;\n0b10 -> B;\n[0b1] -> C;")
    assert [d.name for d in program.declarations] == ["A", "B", "C"]


def test_const_expr_structure():
    """``^{A + 1}`` разбирается в BinOp над ConstRef и Number."""
    node = first_value("^{A + 1} -> B;")
    assert isinstance(node, ast.ConstExpr)
    assert isinstance(node.expr, ast.BinOp)
    assert node.expr.op == "+"
    assert isinstance(node.expr.left, ast.ConstRef)


def test_operator_precedence():
    """Умножение имеет приоритет над сложением."""
    expr = first_value("^{1 + 2 * 3} -> A;").expr
    assert expr.op == "+"
    assert expr.right.op == "*"


def test_parentheses_override_precedence():
    """Скобки меняют порядок вычисления."""
    expr = first_value("^{(1 + 2) * 3} -> A;").expr
    assert expr.op == "*"
    assert expr.left.op == "+"


def test_function_calls():
    """Вызовы ``mod`` и ``max`` с вложенными выражениями."""
    expr = first_value("^{max(A, mod(0b111, 2) + 1)} -> B;").expr
    assert isinstance(expr, ast.Call)
    assert expr.func == "max"
    assert expr.args[1].left.func == "mod"


def test_const_expr_inside_array():
    """Константное выражение может быть элементом массива."""
    node = first_value("[0b1; ^{A}; [^{A * 2}]] -> B;")
    assert isinstance(node.items[1], ast.ConstExpr)
    assert isinstance(node.items[2].items[0], ast.ConstExpr)


def test_array_inside_expression():
    """Массив может быть аргументом функции внутри выражения."""
    expr = first_value("^{max([0b1; 0b10])} -> A;").expr
    assert isinstance(expr.args[0], ast.Array)


@pytest.mark.parametrize(
    "text",
    [
        "0b1 -> a;",
        "0b1 -> 1A;",
        "0b1 -> A",
        "0b1 A;",
        "0b12 -> A;",
        "5 -> A;",
        "0x1F -> A;",
        "[0b1, 0b10] -> A;",
        "[0b1; 0b10 -> A;",
        "[0b1;] -> A;",
        "^{A + } -> B;",
        "^{A + 1 -> B;",
        "^{min(A)} -> B;",
        "^{max(A} -> B;",
        "/* незакрытый комментарий",
        "-> A;",
    ],
)
def test_syntax_errors(text):
    """Некорректные конструкции дают ConfigSyntaxError."""
    with pytest.raises(ConfigSyntaxError):
        parse(text)


def test_syntax_error_position():
    """Сообщение об ошибке содержит строку и столбец."""
    with pytest.raises(ConfigSyntaxError) as info:
        parse("0b1 -> A;\n0b10 -> b;")
    assert (info.value.line, info.value.col) == ERROR_POSITION
    assert "строка 2" in str(info.value)
