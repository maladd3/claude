# claude

Terminal tools built with Claude Code. All run in the terminal, no dependencies beyond the Python standard library.

## Tools

### `depths.py` — The Depths (Roguelike)
Navigate procedurally generated dungeons across 5 floors. Fight monsters, collect loot, survive.

```
python3 depths.py
```

### `cryptid_tours.py` — Cryptid Tours Co.
Interactive management dashboard for a cryptid tourism company. Switch between views with `1–4`, navigate with `j/k` or arrow keys, quit with `q`.

```
python3 cryptid_tours.py
```

### `quote.py` — Agency Quoting Tool
Keyboard-driven quoting tool for a creative/marketing agency. Edit the `AGENCY_*` constants at the top of the file to match your business.

```
python3 quote.py
```

### `vuln_tracker.py` — Vulnerability Tracker
Persistent TUI for tracking CVEs and internal security findings. Data saved to `vulns.json`.

```
python3 vuln_tracker.py
```

| Key | Action |
|-----|--------|
| `↑↓` | Navigate |
| `a` | Add entry |
| `e` | Edit entry |
| `d` | Delete entry |
| `f` | Filter |
| `x` | Export |
| `q` | Quit |

## Requirements

Python 3.8+, macOS or Linux (uses `termios`).
