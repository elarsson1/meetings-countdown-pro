#!/usr/bin/env zsh
#
# Audio Investigation — Full Test Matrix
#
# Run this on the work machine to collect data. It will:
#   1. Capture system/environment info
#   2. Run 8 test configurations (headless/UI × reused/fresh × default/darwin)
#   3. Save all logs to a timestamped directory
#
# Usage:
#   cd meetings-countdown-pro
#   python3 -m venv venv && source venv/bin/activate
#   pip install -r requirements.txt
#   zsh tests/run_audio_investigation.sh ~/Music/bbc_news_countdown_89s.mp3
#
# The sound file path is the only required argument.
# Results land in tests/audio_results_<timestamp>/

set -euo pipefail

SOUND_FILE="${1:?Usage: $0 <path-to-sound-file>}"
CYCLES="${2:-50}"

if [[ ! -f "$SOUND_FILE" ]]; then
    echo "ERROR: Sound file not found: $SOUND_FILE"
    exit 1
fi

# Ensure we're in the project root
if [[ ! -f "requirements.txt" ]]; then
    echo "ERROR: Run this from the project root (where requirements.txt is)"
    exit 1
fi

# Ensure venv is active
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    echo "ERROR: Activate the virtualenv first: source venv/bin/activate"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTDIR="tests/audio_results_${TIMESTAMP}"
mkdir -p "$OUTDIR"

echo "============================================================"
echo "Audio Investigation — Full Test Matrix"
echo "============================================================"
echo "Sound file:  $SOUND_FILE"
echo "Cycles:      $CYCLES per config"
echo "Output dir:  $OUTDIR"
echo "============================================================"
echo ""

# ---------------------------------------------------------------
# Step 1: System & environment info
# ---------------------------------------------------------------
echo "Collecting system info..."

{
    echo "=== Date ==="
    date

    echo ""
    echo "=== macOS Version ==="
    sw_vers

    echo ""
    echo "=== Hardware ==="
    sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "(unknown CPU)"
    sysctl -n hw.memsize 2>/dev/null | awk '{printf "RAM: %.0f GB\n", $1/1073741824}' || true

    echo ""
    echo "=== Python ==="
    python3 --version
    which python3

    echo ""
    echo "=== PyQt6 / Qt Versions ==="
    python3 -c "
from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
print(f'PyQt6: {PYQT_VERSION_STR}')
print(f'Qt:    {QT_VERSION_STR}')
"

    echo ""
    echo "=== Qt Multimedia Backend (default) ==="
    python3 -c "
import os
print(f'QT_MEDIA_BACKEND env: {os.environ.get(\"QT_MEDIA_BACKEND\", \"(not set)\")}')
# Try to detect which backend Qt actually uses
from PyQt6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv[:1])
from PyQt6.QtMultimedia import QMediaPlayer
p = QMediaPlayer()
# The FFmpeg backend prints version info to stderr on init — captured in test logs
print('(Check test logs for FFmpeg version line to confirm backend)')
app.quit()
"

    echo ""
    echo "=== Audio Devices ==="
    python3 -c "
from PyQt6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv[:1])
from PyQt6.QtMultimedia import QMediaDevices
for dev in QMediaDevices.audioOutputs():
    is_default = ' (DEFAULT)' if dev == QMediaDevices.defaultAudioOutput() else ''
    print(f'  {dev.description()} — id={dev.id().data().decode()}{is_default}')
app.quit()
"

    echo ""
    echo "=== Sound File Info ==="
    file "$SOUND_FILE"
    ls -lh "$SOUND_FILE"

    echo ""
    echo "=== Installed Packages ==="
    pip list 2>/dev/null | grep -iE "pyqt|qt|objc|audio" || echo "(none matched filter)"

} > "$OUTDIR/system_info.txt" 2>&1

echo "  -> $OUTDIR/system_info.txt"

# ---------------------------------------------------------------
# Step 2: Run test matrix
# ---------------------------------------------------------------

# Each row: label, extra_args
tests=(
    "headless_reused_default"       ""
    "headless_fresh_default"        "--fresh-player"
    "ui_reused_default"             "--ui"
    "ui_fresh_default"              "--ui --fresh-player"
    "headless_reused_darwin"        "--backend darwin"
    "headless_fresh_darwin"         "--fresh-player --backend darwin"
    "ui_reused_darwin"              "--ui --backend darwin"
    "ui_fresh_darwin"               "--ui --fresh-player --backend darwin"
)

TOTAL_CONFIGS=$(( ${#tests[@]} / 2 ))
CONFIG_NUM=0

for (( i=1; i<=${#tests[@]}; i+=2 )); do
    LABEL="${tests[$i]}"
    EXTRA_ARGS="${tests[$((i+1))]}"
    CONFIG_NUM=$((CONFIG_NUM + 1))

    LOGFILE="$OUTDIR/${LABEL}.log"

    echo ""
    echo "[$CONFIG_NUM/$TOTAL_CONFIGS] $LABEL"
    echo "  Command: python tests/audio_stress_test.py --sound-file \"$SOUND_FILE\" --cycles $CYCLES $EXTRA_ARGS"

    # Run with DEBUG logging to capture full state machine transitions
    python3 tests/audio_stress_test.py \
        --sound-file "$SOUND_FILE" \
        --cycles "$CYCLES" \
        --log-level DEBUG \
        $EXTRA_ARGS \
        > "$LOGFILE" 2>&1 || true

    # Extract and display the summary
    echo "  Result:"
    grep -E "(Successes|Failures|Silent cycles)" "$LOGFILE" | sed 's/^/    /'
    echo "  -> $LOGFILE"
done

# ---------------------------------------------------------------
# Step 3: Summary report
# ---------------------------------------------------------------
echo ""
echo "============================================================"
echo "SUMMARY"
echo "============================================================"

{
    printf "%-35s %10s %10s %10s\n" "Configuration" "Successes" "Failures" "Rate"
    printf "%-35s %10s %10s %10s\n" "---" "---" "---" "---"

    for (( i=1; i<=${#tests[@]}; i+=2 )); do
        LABEL="${tests[$i]}"
        LOGFILE="$OUTDIR/${LABEL}.log"

        SUCCESSES=$(grep "Successes:" "$LOGFILE" 2>/dev/null | grep -oE '[0-9]+' | head -1 || echo "?")
        FAILURES=$(grep "Failures:" "$LOGFILE" 2>/dev/null | grep -oE '[0-9]+' | head -1 || echo "?")

        if [[ "$FAILURES" == "0" ]]; then
            RATE="100%"
        elif [[ "$SUCCESSES" != "?" && "$FAILURES" != "?" ]]; then
            TOTAL=$((SUCCESSES + FAILURES))
            if [[ "$TOTAL" -gt 0 ]]; then
                RATE="$(( SUCCESSES * 100 / TOTAL ))%"
            else
                RATE="N/A"
            fi
        else
            RATE="ERR"
        fi

        printf "%-35s %10s %10s %10s\n" "$LABEL" "$SUCCESSES" "$FAILURES" "$RATE"
    done
} | tee "$OUTDIR/summary.txt"

echo ""
echo "Full results in: $OUTDIR/"
echo "Bring this entire directory back for analysis."
echo ""
echo "If any failures occurred, the DEBUG logs contain full state"
echo "machine transitions for every cycle. Look for SILENT lines."
