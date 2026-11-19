#!/usr/bin/env sh
# Запуск транслятора: конфигурация читается из stdin, JSON — в stdout.
# Пример: ./run.sh < examples/web_server.conf
# Все аргументы передаются транслятору (например, --compact).
set -e
cd "$(dirname "$0")"
PYTHONPATH=src exec python3 -m confjson "$@"
