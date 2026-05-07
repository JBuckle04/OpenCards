#!/bin/zsh

set -u

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR" || exit 1

print_header() {
  echo ""
  echo "OpenCards"
  echo "=========="
  echo ""
}

pause_before_close() {
  echo ""
  echo "Press Return to close this window."
  read -r _
}

find_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return 0
  fi
  return 1
}

print_header

PYTHON_CMD="$(find_python || true)"
if [[ -z "$PYTHON_CMD" ]]; then
  echo "Python 3 was not found on this Mac."
  echo ""
  echo "Install Python from:"
  echo "https://www.python.org/downloads/"
  echo ""
  echo "After installing it, double-click this file again."
  pause_before_close
  exit 1
fi

"$PYTHON_CMD" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY

if [[ $? -ne 0 ]]; then
  echo "OpenCards needs Python 3.11 or newer."
  echo ""
  echo "The Python found on this Mac is:"
  "$PYTHON_CMD" --version
  echo ""
  echo "Install a newer Python from:"
  echo "https://www.python.org/downloads/"
  pause_before_close
  exit 1
fi

echo "Starting OpenCards..."
"$PYTHON_CMD" "$APP_DIR/app.py"
APP_STATUS=$?

if [[ $APP_STATUS -ne 0 ]]; then
  echo ""
  echo "OpenCards stopped with an error."
  echo "If this keeps happening, share the text in this window with the project maintainer."
  pause_before_close
fi

exit $APP_STATUS
