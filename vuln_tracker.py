#!/usr/bin/env python3
"""
Cybersecurity Vulnerability Tracker
Persistent, keyboard-driven TUI for tracking CVEs and internal findings.
Data saved to: vulns.json (created automatically)
Run: python3 vuln_tracker.py
Keys: ↑↓ navigate  ·  a add  ·  e edit  ·  d delete  ·  f filter  ·  x export  ·  q quit
"""

import sys, os, tty, termios, select, signal, shutil, json, random, re
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from copy import deepcopy

DB_FILE = os.path.join(os.path.dirname(__file__), 'vulns.json')

# ── Terminal ──────────────────────────────────────────────────────────────────

def getch() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            r, _, _ = select.select([sys.stdin], [], [], 0.05)
            if r: ch += sys.stdin.read(2)
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

def show_cursor(): sys.stdout.write('\033[?25h'); sys.stdout.flush()
def hide_cursor(): sys.stdout.write('\033[?25l'); sys.stdout.flush()
def at(r, c): return f'\033[{r};{c}H'

COLS, ROWS = shutil.get_terminal_size((130, 42))
COLS = max(110, COLS)
ROWS = max(36, ROWS)

# ── Colors ────────────────────────────────────────────────────────────────────

R = '\033[0m'
def c(n, bold=False, dim=False):
    return f'\033[{"1;" if bold else ""}{"2;" if dim else ""}{n}m'

BLK,RED,GRN,YLW,BLU,MAG,CYN,WHT = 30,31,32,33,34,35,36,37
BBLK,BRED,BGRN,BYLW,BBLU,BMAG,BCYN,BWHT = 90,91,92,93,94,95,96,97
BGBLK,BGRED,BGGRN = 40,41,42

# ── Severity & status definitions ─────────────────────────────────────────────

SEVERITIES = ['Critical', 'High', 'Medium', 'Low', 'Info']
SEV_COLOR  = {'Critical': BRED, 'High': BYLW, 'Medium': YLW, 'Low': BGRN, 'Info': BBLK}
SEV_BADGE  = {'Critical':'●','High':'●','Medium':'●','Low':'●','Info':'●'}

STATUSES   = ['Open', 'In Progress', 'Patched', 'Accepted Risk', "Won't Fix"]
STA_COLOR  = {'Open': BRED, 'In Progress': BYLW, 'Patched': BGRN,
              'Accepted Risk': BMAG, "Won't Fix": BBLK}

CVSS_COLOR = lambda score: BRED if score>=9 else BYLW if score>=7 else YLW if score>=4 else BGRN

# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Vuln:
    vid:          str   = ''
    title:        str   = ''
    cve:          str   = 'N/A'
    severity:     str   = 'Medium'
    cvss:         float = 0.0
    status:       str   = 'Open'
    systems:      str   = ''     # comma-separated
    discovered:   str   = ''     # YYYY-MM-DD
    due_date:     str   = ''     # YYYY-MM-DD
    assigned:     str   = ''
    description:  str   = ''
    remediation:  str   = ''
    tags:         str   = ''
    updated:      str   = ''

    @property
    def is_overdue(self) -> bool:
        if not self.due_date or self.status in ('Patched', "Won't Fix"): return False
        try:
            return date.fromisoformat(self.due_date) < date.today()
        except ValueError:
            return False

def next_vid(vulns: List[Vuln]) -> str:
    nums = [int(v.vid.replace('VLN-', '')) for v in vulns if v.vid.startswith('VLN-')]
    return f'VLN-{(max(nums)+1 if nums else 1):04d}'

# ── Persistence ───────────────────────────────────────────────────────────────

def load_db() -> List[Vuln]:
    if not os.path.exists(DB_FILE):
        return _sample_data()
    try:
        with open(DB_FILE) as f:
            return [Vuln(**d) for d in json.load(f)]
    except Exception:
        return []

def save_db(vulns: List[Vuln]):
    with open(DB_FILE, 'w') as f:
        json.dump([asdict(v) for v in vulns], f, indent=2)

def _sample_data() -> List[Vuln]:
    today = date.today()
    return [
        Vuln('VLN-0001','SQL Injection in Admin Login','CVE-2024-12341',
             'Critical',9.8,'Open','auth.internal.co, api.prod',
             str(today-timedelta(days=12)), str(today+timedelta(days=3)),
             'alice@team.co','Parameterized queries not used in /admin/login POST handler. '
             'Confirmed exploitable via time-based blind injection.',
             'Replace raw string concatenation with parameterized queries. '
             'Deploy WAF rule as interim mitigation.',
             'injection,web,auth', str(today-timedelta(days=12))),

        Vuln('VLN-0002','Outdated OpenSSL (1.0.2)','CVE-2022-0778',
             'High',7.5,'In Progress','prod-web-01, prod-web-02, staging',
             str(today-timedelta(days=30)), str(today+timedelta(days=7)),
             'bob@team.co','OpenSSL 1.0.2 is end-of-life and vulnerable to infinite loop '
             'DoS via BN_mod_sqrt() on malformed certificates.',
             'Upgrade to OpenSSL 3.2+ on all affected hosts. '
             'Test against staging before production rollout.',
             'ssl,infra,dos', str(today-timedelta(days=5))),

        Vuln('VLN-0003','S3 Bucket Public Read Access','N/A',
             'High',8.1,'Open','s3://co-marketing-assets',
             str(today-timedelta(days=3)), str(today+timedelta(days=1)),
             'carol@team.co','Marketing assets bucket allows anonymous public read. '
             'Contains unreleased product images and internal campaign docs.',
             'Set bucket ACL to private. Enable S3 Block Public Access. '
             'Review bucket policy and remove any wildcard principals.',
             'cloud,aws,misconfiguration', str(today-timedelta(days=3))),

        Vuln('VLN-0004','Reflected XSS in Search','CVE-2023-45671',
             'Medium',6.1,'Patched','www.example.co/search',
             str(today-timedelta(days=45)), str(today-timedelta(days=10)),
             'alice@team.co','User-controlled `q` parameter reflected unescaped in search '
             'results page title and og:description meta tag.',
             'Input sanitized with html.escape() and output encoding added. '
             'Deployed in release v2.4.1 on 2024-03-15.',
             'xss,web,input-validation', str(today-timedelta(days=10))),

        Vuln('VLN-0005','Default Credentials on Network Printer','N/A',
             'Medium',5.3,'Patched','HP LaserJet M607 (10.0.1.44)',
             str(today-timedelta(days=60)), str(today-timedelta(days=45)),
             'bob@team.co','Printer admin interface accessible with default admin:admin '
             'credentials. Could allow config changes or print queue interception.',
             'Changed admin password to strong credential. Restricted management '
             'interface to IT VLAN only. Added to asset inventory.',
             'default-credentials,network,printer', str(today-timedelta(days=45))),

        Vuln('VLN-0006','Missing HSTS Header','N/A',
             'Low',3.1,'Open','www.example.co, api.example.co',
             str(today-timedelta(days=20)), str(today+timedelta(days=30)),
             'carol@team.co','Strict-Transport-Security header not set on HTTPS responses. '
             'Leaves users vulnerable to SSL stripping attacks on first visit.',
             'Add "Strict-Transport-Security: max-age=31536000; includeSubDomains; preload" '
             'header in nginx config. Submit to HSTS preload list.',
             'headers,tls,hardening', str(today-timedelta(days=20))),

        Vuln('VLN-0007','Dependency: log4j 2.14.1','CVE-2021-44228',
             'Critical',10.0,'Accepted Risk','internal-reporting-tool (isolated)',
             str(today-timedelta(days=180)), str(today-timedelta(days=150)),
             'alice@team.co','Log4Shell present in internal reporting tool (Java). Tool is '
             'air-gapped from internet, no external log4j lookup possible. Exploit requires '
             'internal network access which requires existing compromise.',
             'Tool is isolated with no internet egress. Risk accepted pending full '
             'rewrite of reporting service (Q4 2025). Compensating controls in place.',
             'log4shell,java,dependency', str(today-timedelta(days=150))),

        Vuln('VLN-0008','Password Policy: No MFA on VPN','N/A',
             'High',7.2,'In Progress','Cisco AnyConnect VPN',
             str(today-timedelta(days=8)), str(today+timedelta(days=14)),
             'bob@team.co','VPN access does not require multi-factor authentication. '
             'If credentials are compromised, full internal network access is possible.',
             'Enroll all VPN users in Okta MFA. Configure Cisco AnyConnect to require '
             'Okta SAML assertion. Target rollout: phased, starting with IT/Engineering.',
             'mfa,vpn,access-control', str(today-timedelta(days=8))),
    ]

# ── UI primitives ─────────────────────────────────────────────────────────────

def flush(out): sys.stdout.write(''.join(out)); sys.stdout.flush()

def read_line(prompt: str, row: int, col: int, width: int = 50, default: str = '') -> str:
    buf = list(default); cursor = len(buf)
    show_cursor()
    while True:
        text = ''.join(buf)
        sys.stdout.write(
            f'{at(row,col)}{c(BBLK)}{prompt}{R} {c(BWHT)}{text}{" "*max(0,width-len(text))}{R}'
            f'{at(row, col+len(prompt)+1+cursor)}'
        ); sys.stdout.flush()
        ch = getch()
        if ch in ('\r','\n'):   break
        elif ch in ('\x7f','\x08'):
            if cursor>0: buf.pop(cursor-1); cursor-=1
        elif ch=='\x1b[C':     cursor=min(cursor+1,len(buf))
        elif ch=='\x1b[D':     cursor=max(cursor-1,0)
        elif ch=='\x1b':       break
        elif len(ch)==1 and 32<=ord(ch)<127 and len(buf)<width:
            buf.insert(cursor,ch); cursor+=1
    hide_cursor()
    return ''.join(buf).strip()

def sev_badge(severity: str) -> str:
    col = SEV_COLOR.get(severity, BBLK)
    return f'{c(col,bold=True)}{severity:<8}{R}'

def sta_badge(status: str) -> str:
    col = STA_COLOR.get(status, BBLK)
    return f'{c(col)}{status:<14}{R}'

def cvss_str(score: float) -> str:
    col = CVSS_COLOR(score)
    return f'{c(col,bold=True)}{score:>4.1f}{R}'

# ── Views ─────────────────────────────────────────────────────────────────────

def draw_header(subtitle: str, count: int, filter_active: bool):
    out = ['\033[H']
    out.append(f'{at(1,1)}{c(BGBLK)}{" "*COLS}{R}')
    out.append(f'{at(1,2)}{c(BRED,bold=True)}⬡{R} {c(BWHT,bold=True)}VULN TRACKER{R}  '
               f'{c(BBLK)}Cybersecurity Vulnerability Management{R}')
    if filter_active:
        out.append(f'{at(1,COLS-18)}{c(BYLW)}▶ FILTER ACTIVE{R}')
    out.append(f'{at(2,1)}{c(BBLK)}{"─"*COLS}{R}')
    out.append(f'{at(3,2)}{c(BBLK)}{subtitle}  {R}{c(BBLK)}({count} records){R}')
    out.append(f'{at(4,1)}{c(BBLK)}{"─"*COLS}{R}')
    return ''.join(out)

def view_dashboard(vulns: List[Vuln]):
    out = ['\033[2J', draw_header('DASHBOARD', len(vulns), False)]

    # Severity breakdown
    sev_counts = {s: sum(1 for v in vulns if v.severity==s and v.status not in ('Patched',"Won't Fix"))
                  for s in SEVERITIES}
    sta_counts = {s: sum(1 for v in vulns if v.status==s) for s in STATUSES}
    overdue    = [v for v in vulns if v.is_overdue]
    open_v     = [v for v in vulns if v.status in ('Open','In Progress')]

    ROW = 5
    out.append(f'{at(ROW,2)}{c(BWHT,bold=True)}OPEN BY SEVERITY{R}')
    bar_w = 24
    for sev in SEVERITIES:
        n = sev_counts[sev]
        total_open = sum(sev_counts.values()) or 1
        filled = int(n/total_open * bar_w) if total_open else 0
        col = SEV_COLOR[sev]
        bar = f'{c(col)}{"█"*filled}{c(BBLK)}{"░"*(bar_w-filled)}{R}'
        out.append(f'{at(ROW+SEVERITIES.index(sev)+1, 4)}'
                   f'{c(col,bold=True)}{sev:<9}{R} {bar} {c(col)}{n:>3}{R}')

    # Status breakdown
    out.append(f'{at(ROW,38)}{c(BWHT,bold=True)}STATUS BREAKDOWN{R}')
    for i, sta in enumerate(STATUSES):
        n = sta_counts[sta]
        col = STA_COLOR[sta]
        out.append(f'{at(ROW+i+1, 40)}{c(col)}{sta:<16}{R} {c(col,bold=True)}{n:>3}{R}')

    # KPIs
    out.append(f'{at(ROW,72)}{c(BWHT,bold=True)}KEY METRICS{R}')
    total  = len(vulns)
    patched = sum(1 for v in vulns if v.status=='Patched')
    patch_rate = f'{patched/total*100:.0f}%' if total else '—'
    kpis = [
        ('Total findings',   str(total),      BWHT),
        ('Open / Active',    str(len(open_v)),BRED if open_v else BGRN),
        ('Overdue',          str(len(overdue)), BRED if overdue else BGRN),
        ('Patch rate',       patch_rate,      BGRN if patched else BBLK),
        ('Critical open',    str(sev_counts.get('Critical',0)), BRED),
        ('High open',        str(sev_counts.get('High',0)),     BYLW),
    ]
    for i, (label, val, col) in enumerate(kpis):
        out.append(f'{at(ROW+i+1, 74)}{c(BBLK)}{label:<18}{R}{c(col,bold=True)}{val}{R}')

    # Overdue list
    DROW = ROW + len(SEVERITIES) + 3
    out.append(f'{at(DROW,2)}{c(BRED,bold=True)}OVERDUE  ({len(overdue)}){R}')
    if overdue:
        for i, v in enumerate(overdue[:5]):
            days = (date.today()-date.fromisoformat(v.due_date)).days
            out.append(f'{at(DROW+1+i, 4)}{c(BRED)}{v.vid}{R}  {sev_badge(v.severity)}'
                       f'  {c(WHT)}{v.title[:40]:<40}{R}  {c(BRED)}{days}d overdue{R}')
    else:
        out.append(f'{at(DROW+1, 4)}{c(BGRN)}No overdue vulnerabilities.{R}')

    # Recent activity
    AROW = DROW + 8
    recent = sorted(vulns, key=lambda v: v.updated or '', reverse=True)[:5]
    out.append(f'{at(AROW,2)}{c(BWHT,bold=True)}RECENTLY UPDATED{R}')
    for i, v in enumerate(recent):
        out.append(f'{at(AROW+1+i, 4)}{c(BBLK)}{v.updated[:10] if v.updated else "—":>12}{R}  '
                   f'{c(BBLK)}{v.vid}{R}  {sev_badge(v.severity)}  {c(WHT)}{v.title[:45]}{R}')

    out.append(f'{at(ROWS,1)}{c(BBLK)}  l List   a Add   x Export   q Quit{R}')
    flush(out)

    while True:
        ch = getch()
        if ch in ('q','Q','x1b'): return 'quit'
        elif ch in ('l','L','\r','\n'): return 'list'
        elif ch in ('a','A'): return 'add'
        elif ch in ('x','X'): return 'export'

def view_list(vulns: List[Vuln], filter_sev: str = '', filter_sta: str = '') -> tuple:
    """Returns (action, vuln_or_none)"""
    displayed = [v for v in vulns
                 if (not filter_sev or v.severity==filter_sev)
                 and (not filter_sta or v.status==filter_sta)]
    displayed.sort(key=lambda v: (SEVERITIES.index(v.severity), v.is_overdue==False, v.vid))

    cursor = 0
    COL_W = [10, 10, 9, 7, 16, 14, 12]  # vid, sev, cvss, status, title, assigned, due

    while True:
        out = ['\033[2J',
               draw_header('VULNERABILITY LIST', len(displayed), bool(filter_sev or filter_sta))]

        # Table header
        TROW = 5
        hdr = (f'{c(BBLK)}{"ID":<10}{"SEVERITY":<10}{"CVSS":>5}  {"STATUS":<16}'
               f'{"TITLE":<45}{"ASSIGNED":<20}{"DUE DATE":<12}{"!":<3}{R}')
        out.append(f'{at(TROW,2)}{hdr}')
        out.append(f'{at(TROW+1,2)}{c(BBLK)}{"─"*(COLS-4)}{R}')

        visible_h = ROWS - TROW - 5
        page_start = max(0, cursor - visible_h // 2)
        page = displayed[page_start:page_start+visible_h]

        for i, v in enumerate(page):
            row = TROW + 2 + i
            is_cur = (page_start + i) == cursor
            overdue_flag = f'{c(BRED,bold=True)}!{R}' if v.is_overdue else ' '
            try:
                due_str = v.due_date[5:] if v.due_date else '—'
            except Exception:
                due_str = '—'

            col_pre = f'{c(BGBLK)}' if is_cur else ''
            col_suf = R

            line = (f'{col_pre}{c(BBLK)}{v.vid:<10}{R}{col_pre}'
                    f'{c(SEV_COLOR[v.severity],bold=True)}{v.severity:<10}{R}{col_pre}'
                    f'{cvss_str(v.cvss)}  '
                    f'{c(STA_COLOR[v.status])}{v.status:<16}{R}{col_pre}'
                    f'{c(BWHT,bold=True) if is_cur else c(WHT)}{v.title[:44]:<45}{R}{col_pre}'
                    f'{c(BBLK)}{(v.assigned or "—")[:19]:<20}{R}{col_pre}'
                    f'{c(BRED) if v.is_overdue else c(BBLK)}{due_str:<12}{R}'
                    f'{overdue_flag}')
            out.append(f'{at(row,2)}{line}')

        # Clear remaining rows
        for i in range(len(page), visible_h):
            out.append(f'{at(TROW+2+i, 2)}{" "*(COLS-4)}')

        # Status bar
        filter_str = ''
        if filter_sev: filter_str += f' sev:{filter_sev}'
        if filter_sta: filter_str += f' status:{filter_sta}'
        out.append(f'{at(ROWS-1,1)}{c(BBLK)}{"─"*COLS}{R}')
        out.append(f'{at(ROWS,1)}{c(BBLK)}  ↑↓ navigate  Enter detail  a add  e edit  d delete  '
                   f'f filter{filter_str}  c clear  0 dashboard  q quit{R}')
        flush(out)

        ch = getch()
        if ch in ('\x1b[A','k'):
            cursor = max(0, cursor-1)
        elif ch in ('\x1b[B','j'):
            cursor = min(len(displayed)-1, cursor+1)
        elif ch in ('\r','\n') and displayed:
            return ('detail', displayed[cursor])
        elif ch in ('a','A'):
            return ('add', None)
        elif ch in ('e','E') and displayed:
            return ('edit', displayed[cursor])
        elif ch in ('d','D') and displayed:
            return ('delete', displayed[cursor])
        elif ch in ('f','F'):
            return ('filter', None)
        elif ch in ('c','C'):
            return ('clear_filter', None)
        elif ch in ('0',):
            return ('dashboard', None)
        elif ch in ('x','X'):
            return ('export', None)
        elif ch in ('q','Q'):
            return ('quit', None)
        elif ch in ('h','H','?'):
            return ('help', None)

def view_detail(v: Vuln) -> str:
    out = ['\033[2J', draw_header(f'DETAIL — {v.vid}', 1, False)]

    ROW = 5
    sc = SEV_COLOR.get(v.severity, BBLK)
    stc = STA_COLOR.get(v.status, BBLK)

    out.append(f'{at(ROW,  2)}{c(BWHT,bold=True)}{v.title}{R}')
    out.append(f'{at(ROW+1,2)}{c(BBLK)}{v.vid}  {R}{sev_badge(v.severity)}'
               f'  CVSS {cvss_str(v.cvss)}  {sta_badge(v.status)}')

    # Two-column layout
    left = [
        ('CVE',         v.cve or 'N/A'),
        ('Severity',    v.severity),
        ('CVSS Score',  f'{v.cvss}'),
        ('Status',      v.status),
        ('Assigned',    v.assigned or '—'),
        ('Discovered',  v.discovered or '—'),
        ('Due Date',    v.due_date + (' ⚠ OVERDUE' if v.is_overdue else '')),
        ('Updated',     v.updated or '—'),
    ]
    for i, (label, val) in enumerate(left):
        col = BRED if 'OVERDUE' in val else (sc if label=='Severity' else BWHT)
        out.append(f'{at(ROW+3+i,4)}{c(BBLK)}{label:<14}{R}{c(col)}{val}{R}')

    out.append(f'{at(ROW+3,  50)}{c(BBLK)}Affected Systems{R}')
    for i, sys_name in enumerate((v.systems or 'None').split(',')):
        out.append(f'{at(ROW+4+i, 52)}{c(BWHT)}{sys_name.strip()}{R}')

    out.append(f'{at(ROW+3+len((v.systems or '').split(','))+1, 50)}{c(BBLK)}Tags{R}')
    out.append(f'{at(ROW+3+len((v.systems or '').split(','))+2, 52)}{c(BBLK)}{v.tags or "none"}{R}')

    DROW = ROW + 13
    out.append(f'{at(DROW,  2)}{c(BBLK)}{"─"*(COLS-4)}{R}')
    out.append(f'{at(DROW+1,2)}{c(BCYN,bold=True)}Description{R}')
    for i, line in enumerate(_wrap(v.description, COLS-6)[:5]):
        out.append(f'{at(DROW+2+i, 4)}{c(WHT)}{line}{R}')

    RROW = DROW + 9
    out.append(f'{at(RROW,  2)}{c(BBLK)}{"─"*(COLS-4)}{R}')
    out.append(f'{at(RROW+1,2)}{c(BGRN,bold=True)}Remediation{R}')
    for i, line in enumerate(_wrap(v.remediation, COLS-6)[:5]):
        out.append(f'{at(RROW+2+i, 4)}{c(WHT)}{line}{R}')

    out.append(f'{at(ROWS,1)}{c(BBLK)}  e Edit  d Delete  l Back to list  0 Dashboard  q Quit{R}')
    flush(out)

    while True:
        ch = getch()
        if ch in ('e','E'): return 'edit'
        elif ch in ('d','D'): return 'delete'
        elif ch in ('l','L','\x1b'): return 'list'
        elif ch in ('0',): return 'dashboard'
        elif ch in ('q','Q'): return 'quit'

def view_form(vulns: List[Vuln], existing: Optional[Vuln] = None) -> Optional[Vuln]:
    """Add/edit form. Returns filled Vuln or None if cancelled."""
    v = deepcopy(existing) if existing else Vuln(
        vid=next_vid(vulns),
        discovered=str(date.today()),
        updated=str(date.today()),
        due_date=str(date.today()+timedelta(days=30)),
    )
    is_new = existing is None
    title_str = 'ADD VULNERABILITY' if is_new else f'EDIT — {v.vid}'

    out = ['\033[2J', draw_header(title_str, 1, False)]
    out.append(f'{at(5,4)}{c(BBLK)}Fill in the fields below. Enter to advance. Esc to cancel.{R}')
    flush(out)

    def field(label, row, attr, width=52, default_val=None):
        dv = default_val if default_val is not None else getattr(v, attr, '')
        sys.stdout.write(f'{at(row,4)}{c(BBLK)}{label}{R}\n'); sys.stdout.flush()
        val = read_line('›', row+1, 4, width, str(dv))
        if val: setattr(v, attr, val)

    def pick_field(label, row, attr, options, colors):
        sys.stdout.write(f'{at(row,4)}{c(BBLK)}{label}{R}\n'); sys.stdout.flush()
        current_val = getattr(v, attr)
        cur_idx = options.index(current_val) if current_val in options else 0
        # Horizontal picker
        while True:
            display = ''.join(
                f'{c(colors[options[i]],bold=True)} [{opt}] {R}' if i==cur_idx
                else f'{c(BBLK)} {opt} {R}'
                for i, opt in enumerate(options)
            )
            sys.stdout.write(f'{at(row+1,6)}{display}'); sys.stdout.flush()
            ch = getch()
            if ch in ('\x1b[C','l','j'): cur_idx=(cur_idx+1)%len(options)
            elif ch in ('\x1b[D','h','k'): cur_idx=(cur_idx-1)%len(options)
            elif ch in ('\r','\n'): setattr(v, attr, options[cur_idx]); break
            elif ch=='\x1b': return False
        return True

    field('Title *',               7,  'title', 60)
    field('CVE (e.g. CVE-2024-1234 or N/A)', 10, 'cve', 24)
    if not pick_field('Severity *', 13, 'severity', SEVERITIES, SEV_COLOR): return None
    field('CVSS Score (0.0–10.0)', 16, 'cvss', 6)
    if not pick_field('Status *',   19, 'status', STATUSES, STA_COLOR): return None
    field('Affected Systems (comma-separated)', 22, 'systems', 70)
    field('Assigned To',            25, 'assigned', 40)
    field('Discovered Date (YYYY-MM-DD)',       28, 'discovered', 12)
    field('Due Date (YYYY-MM-DD)',              31, 'due_date',   12)
    field('Tags (comma-separated)',             34, 'tags',       60)
    field('Description (one line summary)',     37, 'description',75)
    field('Remediation steps',                 40, 'remediation',75)

    try: v.cvss = float(str(v.cvss))
    except ValueError: v.cvss = 0.0

    v.updated = str(date.today())
    if not v.vid: v.vid = next_vid(vulns)

    return v

def view_filter(current_sev: str, current_sta: str) -> tuple:
    out = ['\033[2J', draw_header('FILTER', 0, False)]
    out.append(f'{at(6,4)}{c(WHT)}Filter the vulnerability list.{R}  {c(BBLK)}Leave blank to clear.{R}')
    flush(out)

    sys.stdout.write(f'{at(9,4)}{c(BBLK)}Filter by severity (or blank for all):{R}\n')
    sys.stdout.flush()
    # Inline picker
    sev_opts = ['', *SEVERITIES]
    cur = sev_opts.index(current_sev) if current_sev in sev_opts else 0
    while True:
        display = ''.join(
            f'{c(SEV_COLOR.get(opt,BBLK),bold=True)} [{opt or "ALL"}] {R}' if i==cur
            else f'{c(BBLK)} {opt or "ALL"} {R}'
            for i, opt in enumerate(sev_opts)
        )
        sys.stdout.write(f'{at(10,6)}{display}'); sys.stdout.flush()
        ch = getch()
        if ch in ('\x1b[C','l'): cur=(cur+1)%len(sev_opts)
        elif ch in ('\x1b[D','h'): cur=(cur-1)%len(sev_opts)
        elif ch in ('\r','\n'): new_sev=sev_opts[cur]; break
        elif ch=='\x1b': return (current_sev, current_sta)

    sys.stdout.write(f'{at(13,4)}{c(BBLK)}Filter by status (or blank for all):{R}\n')
    sys.stdout.flush()
    sta_opts = ['', *STATUSES]
    cur2 = sta_opts.index(current_sta) if current_sta in sta_opts else 0
    while True:
        display = ''.join(
            f'{c(STA_COLOR.get(opt,BBLK),bold=True)} [{opt or "ALL"}] {R}' if i==cur2
            else f'{c(BBLK)} {opt or "ALL"} {R}'
            for i, opt in enumerate(sta_opts)
        )
        sys.stdout.write(f'{at(14,6)}{display}'); sys.stdout.flush()
        ch = getch()
        if ch in ('\x1b[C','l'): cur2=(cur2+1)%len(sta_opts)
        elif ch in ('\x1b[D','h'): cur2=(cur2-1)%len(sta_opts)
        elif ch in ('\r','\n'): new_sta=sta_opts[cur2]; break
        elif ch=='\x1b': return (current_sev, current_sta)

    return (new_sev, new_sta)

def export_report(vulns: List[Vuln]) -> str:
    today = date.today()
    filename = f'vuln_report_{today}.txt'
    lines = []
    SEP = '━' * 80
    thin = '─' * 80

    def sev_count(sev): return sum(1 for v in vulns if v.severity==sev and v.status not in ('Patched',"Won't Fix"))

    lines += [SEP,
              '  CYBERSECURITY VULNERABILITY REPORT',
              f'  Generated: {datetime.now().strftime("%B %d, %Y at %H:%M")}',
              SEP, '',
              '  EXECUTIVE SUMMARY', thin]
    for sev in SEVERITIES:
        lines.append(f'  {sev:<12}  {sev_count(sev)} open')
    lines += ['', f'  Total findings: {len(vulns)}',
              f'  Patched:        {sum(1 for v in vulns if v.status=="Patched")}',
              f'  Overdue:        {sum(1 for v in vulns if v.is_overdue)}',
              '', SEP, '']

    for sev in SEVERITIES:
        sev_vulns = [v for v in vulns if v.severity==sev]
        if not sev_vulns: continue
        lines += [f'  {sev.upper()} SEVERITY  ({len(sev_vulns)} findings)', thin]
        for v in sorted(sev_vulns, key=lambda x: x.status):
            lines += [f'  {v.vid}  [{v.status}]  CVSS {v.cvss}',
                      f'  {v.title}',
                      f'  CVE: {v.cve or "N/A"}  |  Assigned: {v.assigned or "—"}  |  Due: {v.due_date or "—"}']
            if v.description:
                lines += [f'  Description: {v.description[:200]}']
            if v.remediation:
                lines += [f'  Remediation: {v.remediation[:200]}']
            lines += ['']
        lines += [SEP, '']

    with open(filename, 'w') as f: f.write('\n'.join(lines))
    return filename

# ── Helpers ───────────────────────────────────────────────────────────────────

def _wrap(text: str, width: int) -> List[str]:
    if not text: return []
    words, lines, cur = text.split(), [], []
    for w in words:
        if sum(len(x)+1 for x in cur)+len(w) > width:
            lines.append(' '.join(cur)); cur=[w]
        else: cur.append(w)
    if cur: lines.append(' '.join(cur))
    return lines

def confirm_delete(v: Vuln) -> bool:
    sys.stdout.write(f'{at(ROWS-1,1)}{c(BGRED)}{c(BWHT,bold=True)}'
                     f'  Delete {v.vid} "{v.title[:40]}"?  y = confirm  n = cancel  '
                     f'{" "*(COLS-65)}{R}')
    sys.stdout.flush()
    ch = getch()
    return ch in ('y','Y')

# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    if sys.platform == 'win32':
        print('Windows not supported.'); sys.exit(1)

    def on_exit(sig, frame):
        show_cursor(); sys.stdout.write('\033[0m\n'); sys.exit(0)
    signal.signal(signal.SIGINT, on_exit)

    os.system('clear')
    hide_cursor()

    vulns = load_db()
    view = 'dashboard'
    filter_sev = ''
    filter_sta = ''
    selected_vuln: Optional[Vuln] = None

    try:
        while True:
            if view == 'dashboard':
                action = view_dashboard(vulns)
                if action == 'quit': break
                elif action == 'list': view = 'list'
                elif action == 'add': view = 'add'
                elif action == 'export':
                    hide_cursor()
                    fname = export_report(vulns)
                    sys.stdout.write(f'{at(ROWS,1)}{c(BGRN)}  ✓ Saved: {fname}  Press any key...{R}')
                    sys.stdout.flush(); getch()

            elif view == 'list':
                action, selected_vuln = view_list(vulns, filter_sev, filter_sta)
                if action == 'quit': break
                elif action == 'dashboard': view = 'dashboard'
                elif action == 'detail' and selected_vuln: view = 'detail'
                elif action == 'add': view = 'add'
                elif action == 'edit' and selected_vuln: view = 'edit'
                elif action == 'delete' and selected_vuln: view = 'delete'
                elif action == 'filter': view = 'filter'
                elif action == 'clear_filter': filter_sev = ''; filter_sta = ''
                elif action == 'export':
                    fname = export_report(vulns)
                    sys.stdout.write(f'{at(ROWS,1)}{c(BGRN)}  ✓ Saved: {fname}  Press any key...{R}')
                    sys.stdout.flush(); getch()

            elif view == 'detail' and selected_vuln:
                action = view_detail(selected_vuln)
                if action == 'quit': break
                elif action == 'dashboard': view = 'dashboard'
                elif action == 'list': view = 'list'
                elif action == 'edit': view = 'edit'
                elif action == 'delete': view = 'delete'

            elif view == 'add':
                result = view_form(vulns)
                if result:
                    vulns.append(result)
                    save_db(vulns)
                    selected_vuln = result
                view = 'list'

            elif view == 'edit' and selected_vuln:
                result = view_form(vulns, selected_vuln)
                if result:
                    idx = next((i for i,v in enumerate(vulns) if v.vid==result.vid), -1)
                    if idx >= 0: vulns[idx] = result
                    save_db(vulns)
                    selected_vuln = result
                view = 'detail'

            elif view == 'delete' and selected_vuln:
                if confirm_delete(selected_vuln):
                    vulns = [v for v in vulns if v.vid != selected_vuln.vid]
                    save_db(vulns)
                    selected_vuln = None
                view = 'list'

            elif view == 'filter':
                filter_sev, filter_sta = view_filter(filter_sev, filter_sta)
                view = 'list'

            else:
                view = 'dashboard'

    finally:
        show_cursor()
        sys.stdout.write('\033[0m\033[2J\033[H')
        sys.stdout.flush()

if __name__ == '__main__':
    main()
