"""Исключения транслятора с указанием места ошибки во входном тексте."""


class ConfigError(Exception):
    """Базовая ошибка транслятора.

    Хранит текст сообщения и, если известно, позицию (строка, столбец),
    в которой обнаружена ошибка.
    """

    kind = "Ошибка"

    def __init__(self, message, line=None, col=None):
        """Создаёт ошибку с сообщением и необязательной позицией."""
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col

    def __str__(self):
        """Возвращает сообщение в формате «Вид (строка N, столбец M): …»."""
        if self.line is None:
            return f"{self.kind}: {self.message}"
        return (
            f"{self.kind} (строка {self.line}, столбец {self.col}): "
            f"{self.message}"
        )


class ConfigSyntaxError(ConfigError):
    """Синтаксическая ошибка во входном тексте."""

    kind = "Синтаксическая ошибка"


class ConfigEvalError(ConfigError):
    """Ошибка вычисления константы или константного выражения."""

    kind = "Ошибка вычисления"
