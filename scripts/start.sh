#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ -x .venv/bin/python ]; then
    exec .venv/bin/python -m pfa.service start "$@"
fi
exec python3 -m pfa.service start "$@"
