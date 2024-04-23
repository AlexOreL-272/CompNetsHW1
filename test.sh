#!/usr/bin/env bash
set -xeuo pipefail

python3 -m pytest -v protocol_test.py -o log_cli=true
