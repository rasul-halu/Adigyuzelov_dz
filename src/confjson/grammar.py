"""Грамматика учебного конфигурационного языка на основе pyparsing.

Модуль строит парсер, который превращает исходный текст в дерево узлов
из :mod:`confjson.ast_nodes`. Синтаксические ошибки pyparsing
преобразуются в :class:`confjson.errors.ConfigSyntaxError`.
"""

import pyparsing as pp

from confjson import ast_nodes as ast
from confjson.errors import ConfigSyntaxError

BIN_RADIX = 2
DEC_RADIX = 10
BIN_PREFIX_LEN = 2
WORD_TAIL = r"(?![_a-zA-Z0-9])"


def _position(text, loc):
    """Переводит смещение ``loc`` в объект :class:`Position`."""
    return ast.Position(pp.lineno(loc, text), pp.col(loc, text))


def _make_bin_number(text, loc, toks):
    """Создаёт узел числа из двоичного литерала ``0b...``."""
    digits = toks[0][BIN_PREFIX_LEN:]
    return ast.Number(int(digits, BIN_RADIX), _position(text, loc))


def _make_dec_number(text, loc, toks):
    """Создаёт узел числа из десятичного литерала внутри выражения."""
    return ast.Number(int(toks[0], DEC_RADIX), _position(text, loc))


def _make_array(text, loc, toks):
    """Создаёт узел массива из разобранных элементов."""
    return ast.Array(list(toks), _position(text, loc))


def _make_ref(text, loc, toks):
    """Создаёт узел обращения к константе."""
    return ast.ConstRef(toks[0], _position(text, loc))


def _make_call(text, loc, toks):
    """Создаёт узел вызова функции ``mod``/``max``."""
    return ast.Call(toks[0], list(toks[1:]), _position(text, loc))


def _make_binop(text, loc, toks):
    """Сворачивает цепочку ``a op b op c`` в левоассоциативное дерево."""
    items = toks[0]
    node = items[0]
    for index in range(1, len(items), 2):
        node = ast.BinOp(
            items[index], node, items[index + 1], _position(text, loc)
        )
    return node


def _make_const_expr(text, loc, toks):
    """Создаёт узел константного выражения ``^{...}``."""
    return ast.ConstExpr(toks[0], _position(text, loc))


def _make_declaration(text, loc, toks):
    """Создаёт узел объявления константы ``значение -> ИМЯ;``."""
    return ast.Declaration(toks[0], toks[1], _position(text, loc))


def _build_expression(value):
    """Строит правило инфиксного выражения внутри ``^{...}``.

    Операнды: числа, имена констант, массивы, вызовы ``mod``/``max``
    и выражения в скобках. Приоритет: ``*`` выше, чем ``+`` и ``-``.
    """
    expr = pp.Forward()
    dec_number = pp.Regex(r"\d+" + WORD_TAIL).set_name("десятичное число")
    dec_number.set_parse_action(_make_dec_number)
    func_name = pp.Keyword("mod") | pp.Keyword("max")
    args = pp.DelimitedList(expr, delim=",")
    call = func_name + pp.Suppress("(") - args - pp.Suppress(")")
    call.set_parse_action(_make_call).set_name("вызов функции")
    name_ref = _name_rule().copy().set_parse_action(_make_ref)
    operand = call | _bin_number_rule() | dec_number | name_ref | value
    operand.set_name("операнд")
    expr <<= pp.infix_notation(
        operand,
        [
            (pp.Literal("*"), 2, pp.OpAssoc.LEFT, _make_binop),
            (pp.one_of("+ -"), 2, pp.OpAssoc.LEFT, _make_binop),
        ],
    )
    return expr


def _name_rule():
    """Правило имени константы ``[_A-Z][_a-zA-Z0-9]*``."""
    return pp.Regex(r"[_A-Z][_a-zA-Z0-9]*").set_name("имя")


def _bin_number_rule():
    """Правило двоичного числа ``0[bB][01]+``."""
    rule = pp.Regex(r"0[bB][01]+" + WORD_TAIL).set_name("число 0b...")
    return rule.set_parse_action(_make_bin_number)


def build_parser():
    """Собирает и возвращает парсер всей программы."""
    value = pp.Forward().set_name("значение")
    items = pp.Optional(pp.DelimitedList(value, delim=";"))
    array = pp.Suppress("[") - items - pp.Suppress("]")
    array.set_parse_action(_make_array)
    const_expr = (
        pp.Suppress("^{") - _build_expression(value) - pp.Suppress("}")
    )
    const_expr.set_parse_action(_make_const_expr)
    value <<= _bin_number_rule() | array | const_expr
    declaration = (
        value - pp.Suppress("->") - _name_rule() - pp.Suppress(";")
    )
    declaration.set_parse_action(_make_declaration)
    program = pp.ZeroOrMore(declaration)
    program.ignore(pp.c_style_comment)
    return program


_PARSER = build_parser()


def parse(text):
    """Разбирает текст программы и возвращает узел :class:`Program`.

    :raises ConfigSyntaxError: при нарушении синтаксиса.
    """
    try:
        result = _PARSER.parse_string(text, parse_all=True)
    except pp.ParseBaseException as exc:
        raise ConfigSyntaxError(
            _describe(exc), exc.lineno, exc.col
        ) from None
    return ast.Program(list(result))


def _describe(exc):
    """Формирует понятное сообщение по исключению pyparsing."""
    found = exc.line[exc.col - 1:].split()
    fragment = found[0] if found else "конец текста"
    if exc.loc >= len(exc.pstr):
        fragment = "конец текста"
    expected = str(exc.msg).replace("Expected ", "")
    expected = expected.replace("end of text", "объявление константы")
    return f"ожидалось {expected}, найдено «{fragment}»"
