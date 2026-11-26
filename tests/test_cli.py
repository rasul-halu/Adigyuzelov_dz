"""Тесты интерфейса командной строки и примеров конфигураций."""

import io
import json
import pathlib

import pytest

from confjson.cli import EXIT_ERROR, EXIT_OK, main, read_input, translate
from confjson.errors import ConfigError

EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / "examples"


def run_cli(text, argv=None):
    """Запускает CLI с заданным вводом и возвращает (код, stdout, stderr)."""
    stdout, stderr = io.StringIO(), io.StringIO()
    code = main(argv or [], io.StringIO(text), stdout, stderr)
    return code, stdout.getvalue(), stderr.getvalue()


def test_translate_returns_json():
    """translate() возвращает корректную JSON-строку."""
    assert json.loads(translate("0b1 -> A;")) == {"A": 1}


def test_cli_success():
    """Успешная трансляция: код 0 и JSON в stdout."""
    code, out, err = run_cli("[0b1; 0b10] -> A;")
    assert code == EXIT_OK
    assert json.loads(out) == {"A": [1, 2]}
    assert err == ""


def test_cli_compact():
    """Ключ --compact выводит JSON в одну строку."""
    _, out, _ = run_cli("[0b1] -> A;", ["--compact"])
    assert out.strip() == '{"A": [1]}'


def test_cli_indent():
    """Ключ --indent задаёт размер отступа."""
    _, out, _ = run_cli("0b1 -> A;", ["--indent", "4"])
    assert '\n    "A": 1' in out


def test_cli_syntax_error():
    """Синтаксическая ошибка: код 1 и сообщение в stderr."""
    code, out, err = run_cli("0b1 -> a;")
    assert code == EXIT_ERROR
    assert out == ""
    assert "Синтаксическая ошибка (строка 1" in err


def test_cli_eval_error():
    """Ошибка вычисления: код 1 и сообщение в stderr."""
    code, _, err = run_cli("^{Q} -> A;")
    assert code == EXIT_ERROR
    assert "неизвестная константа Q" in err


@pytest.mark.parametrize(
    "name", sorted(path.stem for path in EXAMPLES.glob("*.conf"))
)
def test_examples(name):
    """Каждый пример из examples/ транслируется в эталонный JSON."""
    source = (EXAMPLES / f"{name}.conf").read_text(encoding="utf-8")
    expected = (EXAMPLES / f"{name}.json").read_text(encoding="utf-8")
    assert json.loads(translate(source)) == json.loads(expected)


def test_bom_is_skipped():
    """Маркер BOM в начале файла (Блокнот Windows) не мешает разбору."""
    code, out, _ = run_cli("\ufeff0b1 -> A;", ["--compact"])
    assert code == EXIT_OK
    assert out.strip() == '{"A": 1}'


def test_stdin_bytes_decoded_as_utf8(monkeypatch):
    """Стандартный ввод декодируется из UTF-8 независимо от консоли."""
    data = "\ufeff/* Имя */ 0b10 -> A;".encode("utf-8")
    fake = io.TextIOWrapper(io.BytesIO(data), encoding="cp1251")
    monkeypatch.setattr("sys.stdin", fake)
    assert json.loads(translate(read_input())) == {"A": 2}


def test_stdin_not_utf8(monkeypatch):
    """Ввод не в UTF-8 даёт понятную ошибку."""
    fake = io.TextIOWrapper(io.BytesIO(b"\xff\xfe"), encoding="cp1251")
    monkeypatch.setattr("sys.stdin", fake)
    with pytest.raises(ConfigError, match="не в кодировке UTF-8"):
        read_input()
