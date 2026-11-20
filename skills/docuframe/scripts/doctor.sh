#!/usr/bin/env sh
# Check this machine for docuframe. macOS / Linux.  Usage: sh scripts/doctor.sh [--fix]
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3 || command -v python)"
if [ -z "$PY" ]; then
  echo "Python 3.10+ is not installed."
  echo "  macOS:  brew install python@3.12   (Homebrew: https://brew.sh)"
  echo "  Linux:  sudo apt install -y python3 python3-pip"
  exit 1
fi
exec "$PY" "$DIR/docuframe.py" doctor "$@"
