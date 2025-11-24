#!/bin/bash
# Script to activate RadStream virtual environment
# Usage: source activate_venv.sh

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PATH="$SCRIPT_DIR/venv"

if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found at $VENV_PATH"
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_PATH"
    echo "✅ Virtual environment created"
fi

echo "Activating virtual environment..."
source "$VENV_PATH/bin/activate"

echo "✅ Virtual environment activated!"
echo "Python: $(python --version)"
echo "Pip: $(pip --version)"
echo ""
echo "To deactivate, run: deactivate"

