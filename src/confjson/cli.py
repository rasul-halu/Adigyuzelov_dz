"""Интерфейс командной строки: стандартный ввод → JSON в стандартный вывод."""

import argparse
import json
import sys

from confjson.errors import ConfigError
from confjson.evaluator import Evaluator
from confjson.grammar import parse

DEFAULT_INDENT = 2
EXIT_OK = 0
EXIT_ERROR = 1


def translate(text, indent=DEFAULT_INDENT):
    """Транслирует текст учебного языка в строку JSON.

    :raises ConfigError: при синтаксической ошибке или ошибке вычисления.
    """
    result = Evaluator().run(parse(text))
    return json.dumps(result, ensure_ascii=False, indent=indent)


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
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args = build_arg_parser().parse_args(argv)
    indent = None if args.compact else args.indent
    try:
        output = translate(stdin.read(), indent)
    except ConfigError as exc:
        print(exc, file=stderr)
        return EXIT_ERROR
    print(output, file=stdout)
    return EXIT_OK
