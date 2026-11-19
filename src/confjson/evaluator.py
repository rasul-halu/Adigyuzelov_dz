"""Вычисление констант и константных выражений на этапе трансляции.

Вычислитель обходит дерево программы, вычисляет значения объявленных
констант и возвращает словарь, пригодный для сериализации в JSON.
Имена, начинающиеся с ``_``, считаются вспомогательными и в результат
не попадают.
"""

from confjson import ast_nodes as ast
from confjson.errors import ConfigEvalError

PRIVATE_PREFIX = "_"
MOD_ARITY = 2


def _require_number(value, pos, what):
    """Проверяет, что ``value`` — число, иначе выбрасывает ошибку."""
    if not isinstance(value, int):
        raise ConfigEvalError(
            f"{what} ожидает число, получен массив", pos.line, pos.col
        )
    return value


def _flatten(values):
    """Раскрывает вложенные массивы в плоский список чисел."""
    flat = []
    for item in values:
        if isinstance(item, list):
            flat.extend(_flatten(item))
        else:
            flat.append(item)
    return flat


def _func_mod(args, pos):
    """Остаток от деления: ``mod(a, b)``."""
    if len(args) != MOD_ARITY:
        raise ConfigEvalError(
            f"mod() принимает {MOD_ARITY} аргумента, передано {len(args)}",
            pos.line,
            pos.col,
        )
    left = _require_number(args[0], pos, "mod()")
    right = _require_number(args[1], pos, "mod()")
    if not right:
        raise ConfigEvalError("деление на ноль в mod()", pos.line, pos.col)
    return left % right


def _func_max(args, pos):
    """Максимум из чисел; массивы-аргументы раскрываются."""
    numbers = _flatten(args)
    if not numbers:
        raise ConfigEvalError(
            "max() вызвана без чисел (пустой массив)", pos.line, pos.col
        )
    return max(numbers)


FUNCTIONS = {"mod": _func_mod, "max": _func_max}

OPERATIONS = {
    "+": lambda left, right: left + right,
    "-": lambda left, right: left - right,
    "*": lambda left, right: left * right,
}


class Evaluator:
    """Вычисляет значения узлов AST с учётом объявленных констант."""

    def __init__(self):
        """Создаёт вычислитель с пустой таблицей констант."""
        self.constants = {}
        self._handlers = {
            ast.Number: self._eval_number,
            ast.Array: self._eval_array,
            ast.ConstRef: self._eval_ref,
            ast.BinOp: self._eval_binop,
            ast.Call: self._eval_call,
            ast.ConstExpr: self._eval_const_expr,
        }

    def run(self, program):
        """Вычисляет все объявления программы.

        :returns: словарь «имя → значение» без вспомогательных имён.
        """
        for decl in program.declarations:
            self._declare(decl)
        return {
            name: value
            for name, value in self.constants.items()
            if not name.startswith(PRIVATE_PREFIX)
        }

    def evaluate(self, node):
        """Вычисляет значение произвольного узла выражения."""
        return self._handlers[type(node)](node)

    def _declare(self, decl):
        """Регистрирует константу, запрещая повторное объявление."""
        if decl.name in self.constants:
            raise ConfigEvalError(
                f"константа {decl.name} уже объявлена",
                decl.pos.line,
                decl.pos.col,
            )
        self.constants[decl.name] = self.evaluate(decl.value)

    def _eval_number(self, node):
        """Возвращает значение числового литерала."""
        return node.value

    def _eval_array(self, node):
        """Вычисляет все элементы массива."""
        return [self.evaluate(item) for item in node.items]

    def _eval_ref(self, node):
        """Возвращает значение ранее объявленной константы."""
        if node.name not in self.constants:
            raise ConfigEvalError(
                f"неизвестная константа {node.name}",
                node.pos.line,
                node.pos.col,
            )
        return self.constants[node.name]

    def _eval_binop(self, node):
        """Вычисляет бинарную операцию над числами."""
        what = f"операция «{node.op}»"
        left = _require_number(self.evaluate(node.left), node.pos, what)
        right = _require_number(self.evaluate(node.right), node.pos, what)
        return OPERATIONS[node.op](left, right)

    def _eval_call(self, node):
        """Вычисляет вызов встроенной функции."""
        args = [self.evaluate(arg) for arg in node.args]
        return FUNCTIONS[node.func](args, node.pos)

    def _eval_const_expr(self, node):
        """Вычисляет константное выражение ``^{...}``."""
        return self.evaluate(node.expr)
