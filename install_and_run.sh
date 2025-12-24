#!/bin/bash
# Скрипт установки и запуска эмулятора процессора

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     Эмулятор Процессора - Установка и запуск                 ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Проверка версии Python
echo "📋 Проверка версии Python..."
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
required_version="3.8"

if command -v python3 &> /dev/null; then
    if (( $(echo "$python_version >= $required_version" | bc -l) )); then
        echo "✓ Python $python_version найден"
    else
        echo "✗ Требуется Python $required_version или выше, найден Python $python_version"
        exit 1
    fi
else
    echo "✗ Python3 не найден. Пожалуйста, установите Python 3.8+"
    exit 1
fi

echo ""
echo "📦 Проверка зависимостей..."

# Tkinter обычно встроен, но проверим
python3 -c "import tkinter" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Tkinter доступен"
else
    echo "⚠ Tkinter не найден"
    echo ""
    echo "Для установки Tkinter выполните:"
    echo ""
    echo "📱 Linux (Debian/Ubuntu):"
    echo "  sudo apt-get install python3-tk"
    echo ""
    echo "📱 Linux (Fedora/RHEL):"
    echo "  sudo dnf install python3-tkinter"
    echo ""
    echo "📱 macOS:"
    echo "  Tkinter обычно включен в Python с официального сайта"
    echo "  python3 -m tkinter  # для проверки"
    echo ""
    echo "📱 Windows:"
    echo "  Выберите опцию 'tcl/tk' при установке Python"
    echo ""
    exit 1
fi

echo ""
echo "✓ Все зависимости установлены"
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                      ГОТОВО К ЗАПУСКУ                        ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Запуск эмулятора
echo "🚀 Запуск эмулятора процессора..."
echo ""

python3 processor_emulator.py

exit 0
