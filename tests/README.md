# Audio Investigation — Data Collection

## Setup (work machine)

```bash
git clone <repo-url> meetings-countdown-pro
cd meetings-countdown-pro
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## Run the full test matrix

```bash
zsh tests/run_audio_investigation.sh ~/Music/bbc_news_countdown_89s.mp3
```

This runs 8 configurations × 50 cycles each (~30 min total). Pass a second
argument to change the cycle count:

```bash
zsh tests/run_audio_investigation.sh ~/Music/bbc_news_countdown_89s.mp3 100
```

## What it tests

|                              | Default (FFmpeg) backend | Darwin backend |
|------------------------------|--------------------------|----------------|
| Headless, reused player      | ✓                        | ✓              |
| Headless, fresh player       | ✓                        | ✓              |
| UI contention, reused player | ✓                        | ✓              |
| UI contention, fresh player  | ✓                        | ✓              |

## Output

Results land in `tests/audio_results_<timestamp>/`:

- `system_info.txt` — macOS version, hardware, Python/Qt versions, audio devices
- 8 `.log` files — full DEBUG-level state machine traces for every cycle
- `summary.txt` — pass/fail table across all configurations

## Bring results back

Copy the entire `tests/audio_results_<timestamp>/` directory back to the
personal laptop for analysis.
