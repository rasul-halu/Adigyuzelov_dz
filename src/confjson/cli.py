"""Интерфейс командной строки: стандартный ввод → JSON в стандартный вывод."""

import argparse
import json
import sys

from confjson.errors import ConfigError
from confjson.evaluator import Evaluator
from confjson.grammar import parse

DEFAULT_INDENT = 2
INPUT_ENCODING = "utf-8-sig"
BOM = "\ufeff"
EXIT_OK = 0
EXIT_ERROR = 1


def translate(text, indent=DEFAULT_INDENT):
    """Транслирует текст учебного языка в строку JSON.

    :raises ConfigError: при синтаксической ошибке или ошибке вычисления.
    """
    result = Evaluator().run(parse(text))
    return json.dumps(result, ensure_ascii=False, indent=indent)


def read_input(stdin=None):
    """Читает входной текст конфигурации.

    Стандартный ввод читается как байты и декодируется из UTF-8 (в том
    числе с маркером BOM), чтобы результат не зависел от кодировки
    консоли Windows. Переданный текстовый поток читается как есть.

    :raises ConfigError: если байты не являются текстом UTF-8.
    """
    if stdin is not None:
        return stdin.read().lstrip(BOM)
    try:
        return sys.stdin.buffer.read().decode(INPUT_ENCODING)
    except UnicodeDecodeError as exc:
        raise ConfigError(
            f"входные данные не в кодировке UTF-8 (байт {exc.start})"
        ) from None


def build_arg_parser():
    """Создаёт разборщик аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="confjson",
        description=(
            "Читает конфигурацию на учебном языке из стандартного ввода "
            "и выводит JSON в стандартный вывод."
        ),
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=DEFAULT_INDENT,
        help="число пробелов отступа в JSON (по умолчанию 2)",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="вывести JSON в одну строку без отступов",
    )
    return parser


def main(argv=None, stdin=None, stdout=None, stderr=None):
    """Точка входа CLI. Возвращает код завершения процесса."""
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args = build_arg_parser().parse_args(argv)
    indent = None if args.compact else args.indent
    try:
        output = translate(read_input(stdin), indent)
    except ConfigError as exc:
        print(exc, file=stderr)
        return EXIT_ERROR
    print(output, file=stdout)
    return EXIT_OK
