#!/usr/bin/env python3
"""
Interactive Quoting Tool — Creative & Marketing Agency
Edit the AGENCY_* constants below to match your business.
Run: python3 quote.py
"""

import sys, os, tty, termios, select, signal, shutil, random, json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

# ── CUSTOMIZE YOUR AGENCY ─────────────────────────────────────────────────────
AGENCY_NAME    = "MERIDIAN CREATIVE STUDIO"
AGENCY_TAGLINE = "Design · Marketing · Brand"
AGENCY_EMAIL   = "hello@meridiancreative.co"
AGENCY_PHONE   = "(555) 382-7190"
AGENCY_WEB     = "www.meridiancreative.co"
AGENCY_ADDR    = "247 Pelham St, Suite 4 · Portland, OR 97201"
QUOTE_VALIDITY = 30   # days
DEPOSIT_PCT    = 50   # percent required upfront

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

COLS, ROWS = shutil.get_terminal_size((110, 40))
COLS = max(90, COLS)

# ── Colors ────────────────────────────────────────────────────────────────────

R = '\033[0m'
def c(n, bold=False, dim=False):
    return f'\033[{"1;" if bold else ""}{"2;" if dim else ""}{n}m'

BLK,RED,GRN,YLW,BLU,MAG,CYN,WHT = 30,31,32,33,34,35,36,37
BBLK,BRED,BGRN,BYLW,BBLU,BMAG,BCYN,BWHT = 90,91,92,93,94,95,96,97
BGBLK,BGBLU,BGCYN = 40,44,46

# ── Service catalog ───────────────────────────────────────────────────────────

CATALOG: Dict[str, dict] = {
    'brand': {
        'name': 'Brand Identity',
        'packages': [
            ('Essentials', 1_200,
             ['Logo + favicon (2 concepts)', '2 revision rounds', 'PNG, SVG, PDF delivery']),
            ('Standard',   2_500,
             ['Logo + brand guidelines', 'Stationery suite (card, letterhead, envelope)', '3 revision rounds']),
            ('Premium',    4_800,
             ['Full brand system', 'Style guide + complete asset library', 'Unlimited revisions', 'Print + digital formats']),
        ],
        'addons': [
            ('Extra 2 revision rounds',  150, False),
            ('Multilingual asset pack',  300, False),
            ('Rush delivery (<2 wks)',   None, False),  # None = 35% of package
        ],
        'recurring': False,
    },
    'web': {
        'name': 'Website Design & Development',
        'packages': [
            ('Landing Page',   1_800, ['1–3 pages, mobile-responsive', 'Contact form + basic SEO', '2 revision rounds']),
            ('Business Site',  3_900, ['4–8 pages', 'CMS (WordPress) setup', 'Blog-ready, 2 revision rounds']),
            ('Advanced Site',  6_500, ['9–15 pages', 'Custom features + third-party integrations', '3 revision rounds']),
            ('E-Commerce',     8_500, ['Full online store', 'Payment gateway + inventory mgmt', 'Product import, 3 revision rounds']),
        ],
        'addons': [
            ('Blog setup',              300, False),
            ('Speed & performance opt', 400, False),
            ('Accessibility audit+fix', 500, False),
            ('Monthly maintenance',     250, True),   # recurring/mo
        ],
        'recurring': False,
    },
    'social': {
        'name': 'Social Media Management',
        'packages': [
            ('Starter', 650,   ['2 posts/week', '1 platform', 'Monthly analytics report']),
            ('Growth',  1_200, ['4 posts/week', '2 platforms', 'Analytics dashboard + hashtag research']),
            ('Pro',     2_200, ['Daily posts + stories', '3+ platforms', 'Ad management included']),
        ],
        'addons': [
            ('Community management (DMs)',  400, True),
            ('Custom graphic templates',    600, False),
            ('Paid ad management',          500, True),
        ],
        'recurring': True,
    },
    'content': {
        'name': 'Content Creation',
        'packages': [
            ('Blog Package', 800,   ['4 SEO-optimized articles/month', '800–1200 words each', 'Meta descriptions included']),
            ('Photo Day',    1_500, ['Full-day shoot (8 hrs)', 'Edited gallery (50+ images)', 'Commercial license']),
            ('Brand Video',  3_200, ['60–90 sec promo video', 'Scripted, shot, + edited', 'Licensed music']),
            ('Full Suite',   4_800, ['Blog + Photo + Video bundle', 'Best value — save $1,500', 'Unified content strategy']),
        ],
        'addons': [
            ('Rush delivery (+25%)',  None, False),
            ('Social-cut versions',   400, False),
            ('Copywriting / scripting', 350, False),
        ],
        'recurring': False,
    },
    'ads': {
        'name': 'Digital Advertising',
        'packages': [
            ('Campaign Setup',  800,   ['Strategy + audience research', 'Ad copy + creative brief', '1 platform']),
            ('Full Launch',     1_800, ['Setup + first month management', '2 platforms', 'A/B ad testing']),
            ('Monthly Mgmt',    1_500, ['Ongoing bid optimization', 'Monthly report', '2 platforms']),
        ],
        'addons': [
            ('Ad creative design',   600, False),
            ('Landing page design',  900, False),
            ('Competitor analysis',  350, False),
        ],
        'recurring': False,
    },
    'seo': {
        'name': 'SEO Services',
        'packages': [
            ('Audit Only',         750,   ['Technical + content + backlink audit', 'Prioritized action report']),
            ('One-Time Optimize',  1_800, ['Full audit + on-page fixes', 'Keyword mapping', 'Schema markup']),
            ('Monthly Retainer',   1_200, ['Ongoing SEO', 'Content + link building', 'Ranking reports']),
        ],
        'addons': [
            ('Local SEO setup',       400, False),
            ('Google Business opt.',  250, False),
            ('Competitor gap report', 350, False),
        ],
        'recurring': False,
    },
    'print': {
        'name': 'Print & Collateral',
        'packages': [
            ('Starter Pack',   450,   ['Business cards', 'Letterhead + envelope', 'Print-ready files']),
            ('Marketing Pack', 850,   ['Tri-fold brochure', 'Flyer + postcard', 'Print-ready files']),
            ('Full Suite',     1_600, ['All above items', 'Signage design', 'Merchandise artwork']),
        ],
        'addons': [
            ('Extra design variant (+$200)', 200, False),
            ('Signage / large format',       400, False),
            ('Branded merchandise design',   350, False),
        ],
        'recurring': False,
    },
}

SERVICE_ORDER = ['brand', 'web', 'social', 'content', 'ads', 'seo', 'print']

TIMELINE = [
    ('rush',      'Rush  (under 2 weeks)',   1.35, '+35%'),
    ('expedited', 'Expedited  (2–4 weeks)',  1.15, '+15%'),
    ('standard',  'Standard  (4–8 weeks)',   1.00, ''),
    ('flexible',  'Flexible  (8+ weeks)',    0.95, '−5%'),
]

# ── State ─────────────────────────────────────────────────────────────────────

@dataclass
class QuoteState:
    client_company: str = ''
    client_name:    str = ''
    client_email:   str = ''
    client_phone:   str = ''
    project_type:   str = 'New Project'
    selected:       List[str] = field(default_factory=list)
    configs:        Dict      = field(default_factory=dict)
    timeline_key:   str       = 'standard'
    discount_pct:   int       = 0
    notes:          str       = ''
    quote_no:       str       = field(default_factory=lambda:
                                    f'QT-{datetime.now().year}-{random.randint(1000,9999)}')

    def subtotal(self) -> float:
        total = 0.0
        for sid, cfg in self.configs.items():
            total += cfg.get('total', 0.0)
        return total

    def timeline_mult(self) -> float:
        for key, _, mult, _ in TIMELINE:
            if key == self.timeline_key: return mult
        return 1.0

    def grand_total(self) -> float:
        sub = self.subtotal() * self.timeline_mult()
        return sub * (1 - self.discount_pct / 100)

# ── UI primitives ─────────────────────────────────────────────────────────────

def money(n: float) -> str:
    return f'${n:,.2f}'

def draw_chrome(step_n: int, total_steps: int, title: str, state: QuoteState, out: List[str]):
    filled = int(step_n / total_steps * 32)
    pbar = f'{c(BCYN)}{"█"*filled}{c(BBLK)}{"░"*(32-filled)}{R}'
    total = state.grand_total()
    total_str = f'{c(BGRN,bold=True)}{money(total)}{R}' if total > 0 else ''

    out.append('\033[H')
    out.append(f'{at(1,1)}{c(BGBLK)}{" "*COLS}{R}')
    out.append(f'{at(1,2)}{c(BWHT,bold=True)}{AGENCY_NAME}{R}  {c(BBLK)}{AGENCY_TAGLINE}{R}')
    if total_str:
        label = f'  Quote total: {total_str}  '
        out.append(f'{at(1, COLS-26)}{label}')
    out.append(f'{at(2,1)}{c(BBLK)}{"─"*COLS}{R}')
    out.append(f'{at(3,2)}{c(BBLK)}Step {step_n}/{total_steps}  {R}{pbar}  {c(BWHT,bold=True)}{title}{R}')
    out.append(f'{at(4,1)}{c(BBLK)}{"─"*COLS}{R}')

def draw_hint(hint: str, out: List[str]):
    out.append(f'{at(ROWS,1)}{c(BBLK)}{hint:<{COLS}}{R}')

def flush(out: List[str]):
    sys.stdout.write(''.join(out)); sys.stdout.flush()

def read_line(prompt: str, row: int, col: int, width: int = 48, default: str = '') -> str:
    buf = list(default); cursor = len(buf)
    show_cursor()
    while True:
        text = ''.join(buf)
        sys.stdout.write(
            f'{at(row,col)}{c(BBLK)}{prompt}{R} {c(BWHT)}{text}{" "*max(0,width-len(text))}{R}'
            f'{at(row, col+len(prompt)+1+cursor)}'
        ); sys.stdout.flush()
        ch = getch()
        if ch in ('\r', '\n'):   break
        elif ch in ('\x7f','\x08'):
            if cursor > 0: buf.pop(cursor-1); cursor -= 1
        elif ch == '\x1b[C':    cursor = min(cursor+1, len(buf))
        elif ch == '\x1b[D':    cursor = max(cursor-1, 0)
        elif ch == '\x1b':      break
        elif len(ch)==1 and 32<=ord(ch)<127 and len(buf)<width:
            buf.insert(cursor, ch); cursor += 1
    hide_cursor()
    return ''.join(buf).strip()

def pick_one(options: List[Tuple], start_row: int, col: int = 4,
             default: int = 0, accent=BCYN) -> int:
    """Arrow-key single select. Each option is (label, description) or (label, price, desc)."""
    cur = default
    while True:
        out = []
        for i, opt in enumerate(options):
            label = opt[0]
            desc  = opt[-1] if len(opt) > 2 else opt[1] if len(opt) > 1 else ''
            price = f'  {c(BYLW)}{opt[1]}{R}' if len(opt) == 3 else ''
            if i == cur:
                out.append(f'{at(start_row+i,col)}{c(accent,bold=True)} ▶  {label}{R}{price}'
                           f'  {c(BBLK)}{desc}{R}{"  " + " "*(COLS-col-len(label)-len(desc)-20)}')
            else:
                out.append(f'{at(start_row+i,col)}{c(BBLK)}    {R}{c(WHT)}{label}{R}{c(BBLK)}{price}'
                           f'  {desc}{R}')
        flush(out)
        ch = getch()
        if ch in ('j', '\x1b[B'): cur = (cur+1) % len(options)
        elif ch in ('k', '\x1b[A'): cur = (cur-1) % len(options)
        elif ch in ('\r', '\n'):   return cur
        elif ch.isdigit():
            n = int(ch)-1
            if 0 <= n < len(options): return n

def pick_many(options: List[Tuple], start_row: int, col: int = 4,
              presel: Optional[set] = None, accent=BCYN) -> set:
    """Arrow+space multi-select. Each option is (label, description)."""
    sel = set(presel or [])
    cur = 0
    while True:
        out = []
        for i, (label, desc) in enumerate(options):
            chk = f'{c(BGRN)}☑{R}' if i in sel else f'{c(BBLK)}☐{R}'
            arrow = f'{c(accent,bold=True)}▶{R}' if i == cur else ' '
            name_c = c(BWHT,bold=True) if i==cur else c(WHT)
            out.append(f'{at(start_row+i,col)}{arrow} {chk}  {name_c}{label:<40}{R}  {c(BBLK)}{desc}{R}')
        flush(out)
        ch = getch()
        if ch in ('j', '\x1b[B'):  cur = (cur+1) % len(options)
        elif ch in ('k', '\x1b[A'): cur = (cur-1) % len(options)
        elif ch == ' ':
            if cur in sel: sel.remove(cur)
            else: sel.add(cur)
        elif ch in ('\r', '\n'):    return sel

# ── Step renderers ────────────────────────────────────────────────────────────

FORWARD, BACK, QUIT = 1, -1, 0

def step_welcome() -> int:
    out = ['\033[2J\033[H']
    lines = [
        '',
        f'  {c(BWHT,bold=True)}{AGENCY_NAME}{R}',
        f'  {c(BBLK)}{AGENCY_TAGLINE}{R}',
        '',
        f'  {c(BBLK)}{"─"*56}{R}',
        f'  {c(BWHT,bold=True)}Interactive Quoting Tool{R}',
        '',
        f'  {c(BBLK)}Walk through each step to build a professional quote.{R}',
        f'  {c(BBLK)}At the end, preview it on screen and export a .txt file.{R}',
        '',
        f'  {c(BBLK)}{"─"*56}{R}',
        '',
        f'  {c(BBLK)}↑↓ or j/k{R}   Navigate options',
        f'  {c(BBLK)}Enter{R}        Confirm selection',
        f'  {c(BBLK)}Space{R}        Toggle checkbox',
        f'  {c(BBLK)}←  or  b{R}    Go back a step',
        '',
        f'  {c(BCYN)}Press any key to begin...{R}',
    ]
    for i, line in enumerate(lines):
        out.append(f'{at(3+i,1)}{line}')
    flush(out)
    getch()
    return FORWARD

def step_client(state: QuoteState, n: int, total: int) -> int:
    out = ['\033[2J']
    draw_chrome(n, total, 'CLIENT INFORMATION', state, out)
    out.append(f'{at(6,4)}{c(WHT)}Enter the client\'s details below.{R}  {c(BBLK)}Tab or Enter to advance each field.{R}')
    draw_hint('  Enter after each field to advance  ·  Leave blank to skip', out)
    flush(out)

    fields = [
        ('Company / Organization', 48, 'client_company'),
        ('Contact Name',           36, 'client_name'),
        ('Email Address',          42, 'client_email'),
        ('Phone Number',           20, 'client_phone'),
    ]
    for i, (prompt, width, attr) in enumerate(fields):
        row = 9 + i*3
        out2 = [f'{at(row,4)}{c(BBLK)}{prompt}{R}']
        flush(out2)
        val = read_line('›', row+1, 4, width, getattr(state, attr))
        if val: setattr(state, attr, val)
    return FORWARD

def step_project_type(state: QuoteState, n: int, total: int) -> int:
    out = ['\033[2J']
    draw_chrome(n, total, 'PROJECT TYPE', state, out)
    out.append(f'{at(6,4)}{c(WHT)}What kind of engagement is this?{R}')
    draw_hint('  ↑↓ to move  ·  Enter to select', out)
    flush(out)
    types = [('New Project',      'One-time project with defined deliverables'),
             ('Ongoing Retainer', 'Monthly services on a rolling contract'),
             ('Project + Retainer','New project followed by ongoing support')]
    default = next((i for i, (l,_) in enumerate(types) if l==state.project_type), 0)
    choice = pick_one(types, 9, 4, default)
    state.project_type = types[choice][0]
    return FORWARD

def step_services(state: QuoteState, n: int, total: int) -> int:
    out = ['\033[2J']
    draw_chrome(n, total, 'SELECT SERVICES', state, out)
    out.append(f'{at(6,4)}{c(WHT)}Which services will you quote?{R}  {c(BBLK)}Space to toggle  ·  Enter to continue{R}')
    draw_hint('  Space to toggle  ·  ↑↓ to move  ·  Enter to confirm selection  ·  b to go back', out)
    flush(out)

    presel = {SERVICE_ORDER.index(s) for s in state.selected if s in SERVICE_ORDER}
    opts = []
    for sid in SERVICE_ORDER:
        info = CATALOG[sid]
        min_price = min(p for _, p, _ in info['packages'])
        suffix = '/mo' if info['recurring'] else ''
        opts.append((info['name'], f'from {money(min_price)}{suffix}'))

    sel = pick_many(opts, 9, 4, presel)
    if not sel:
        return BACK
    state.selected = [SERVICE_ORDER[i] for i in sorted(sel)]
    return FORWARD

def step_configure(sid: str, state: QuoteState, n: int, total: int) -> int:
    info = CATALOG[sid]
    out = ['\033[2J']
    draw_chrome(n, total, info['name'].upper(), state, out)
    out.append(f'{at(6,4)}{c(WHT)}Choose a package:{R}')
    draw_hint('  ↑↓ to move  ·  Enter to confirm  ·  b to go back', out)
    flush(out)

    prev_cfg = state.configs.get(sid, {})
    pkg_opts = [(name, money(price), ', '.join(includes))
                for name, price, includes in info['packages']]
    pkg_idx = pick_one(pkg_opts, 8, 4, prev_cfg.get('pkg', 0))

    pkg_name, pkg_price, pkg_includes = info['packages'][pkg_idx]

    # Add-ons
    addons_raw = info.get('addons', [])
    if addons_raw:
        out2 = [f'{at(8+len(pkg_opts)+2, 4)}{c(BBLK)}Add-ons:{R}']
        flush(out2)
        addon_opts = []
        for label, price, recurring in addons_raw:
            if price is None:
                desc = f'+35% of package ({money(pkg_price * 0.35)})'
            elif recurring:
                desc = f'+{money(price)}/mo'
            else:
                desc = f'+{money(price)}'
            addon_opts.append((label, desc))
        prev_addons = set(prev_cfg.get('addons', []))
        chosen_addons = pick_many(addon_opts, 8+len(pkg_opts)+3, 4, prev_addons)
    else:
        chosen_addons = set()

    # Recurring: ask months
    months = prev_cfg.get('months', 3)
    if info['recurring']:
        out3 = [f'{at(8+len(pkg_opts)+len(addons_raw)+5, 4)}{c(BBLK)}Contract length:{R}']
        flush(out3)
        month_opts = [('3 months', ''), ('6 months', ''), ('12 months', f'  {c(BGRN)}best value{R}')]
        prev_m = {3:0,6:1,12:2}.get(months, 0)
        m_choice = pick_one(month_opts, 8+len(pkg_opts)+len(addons_raw)+6, 4, prev_m)
        months = [3, 6, 12][m_choice]

    # Compute total
    addon_cost = 0.0
    for i, (label, price, recurring) in enumerate(addons_raw):
        if i in chosen_addons:
            if price is None:
                addon_cost += pkg_price * 0.35
            else:
                addon_cost += price * (months if recurring else 1)

    service_total = (pkg_price * (months if info['recurring'] else 1)) + addon_cost

    state.configs[sid] = {
        'pkg': pkg_idx, 'pkg_name': pkg_name, 'pkg_price': pkg_price,
        'pkg_includes': pkg_includes, 'addons': chosen_addons,
        'months': months, 'total': service_total,
    }
    return FORWARD

def step_timeline(state: QuoteState, n: int, total: int) -> int:
    out = ['\033[2J']
    draw_chrome(n, total, 'PROJECT TIMELINE', state, out)
    out.append(f'{at(6,4)}{c(WHT)}How urgent is this project?{R}  {c(BBLK)}Timeline affects pricing.{R}')
    draw_hint('  ↑↓ to move  ·  Enter to confirm  ·  b to go back', out)
    flush(out)
    opts = [(label, modifier if modifier else 'standard rate', '')
            for key, label, mult, modifier in TIMELINE]
    prev = next((i for i,(k,*_) in enumerate(TIMELINE) if k==state.timeline_key), 2)
    choice = pick_one(opts, 9, 4, prev)
    state.timeline_key = TIMELINE[choice][0]
    return FORWARD

def step_extras(state: QuoteState, n: int, total: int) -> int:
    out = ['\033[2J']
    draw_chrome(n, total, 'DISCOUNT & NOTES', state, out)
    out.append(f'{at(6,4)}{c(WHT)}Optional: apply a discount and add project notes.{R}')
    draw_hint('  Enter after each field  ·  Leave blank to skip', out)
    flush(out)

    out2 = [f'{at(9,4)}{c(BBLK)}Discount %  {c(BBLK)}(0–50, leave blank for none){R}']
    flush(out2)
    disc_val = read_line('›', 10, 4, 5, str(state.discount_pct) if state.discount_pct else '')
    try:
        state.discount_pct = max(0, min(50, int(disc_val)))
    except ValueError:
        state.discount_pct = 0

    out3 = [f'{at(13,4)}{c(BBLK)}Project notes  {c(BBLK)}(will appear in the quote){R}']
    flush(out3)
    state.notes = read_line('›', 14, 4, 70, state.notes)
    return FORWARD

def step_preview(state: QuoteState, n: int, total: int) -> int:
    out = ['\033[2J']
    draw_chrome(n, total, 'QUOTE PREVIEW', state, out)
    flush(out)

    lines = build_quote_lines(state)
    # Show a scrollable preview (first 30 lines)
    visible = lines[:ROWS-7]
    for i, line in enumerate(visible):
        sys.stdout.write(f'{at(5+i, 2)}{line}\n')
    if len(lines) > ROWS-7:
        sys.stdout.write(f'{at(ROWS-1, 2)}{c(BBLK)}... {len(lines)-len(visible)} more lines in saved file ...{R}')
    sys.stdout.write(f'{at(ROWS,1)}{c(BBLK)}  Enter to save quote  ·  b to go back and adjust  ·  q to quit{R}')
    sys.stdout.flush()

    while True:
        ch = getch()
        if ch in ('\r', '\n'): return FORWARD
        elif ch in ('b', '\x1b[D'): return BACK
        elif ch in ('q', 'Q'): return QUIT

def step_export(state: QuoteState) -> str:
    filename = f'quote_{state.quote_no}_{state.client_company.replace(" ","_")[:20]}.txt'
    filename = ''.join(ch for ch in filename if ch.isalnum() or ch in '._-')
    lines = build_quote_lines(state, plain=True)
    with open(filename, 'w') as f:
        f.write('\n'.join(lines))

    out = ['\033[2J\033[H']
    out.append(f'{at(4,4)}{c(BGRN,bold=True)}✓ Quote saved!{R}\n')
    out.append(f'{at(5,4)}{c(BBLK)}File:{R}  {c(BWHT)}{filename}{R}\n')
    out.append(f'{at(7,4)}{c(BBLK)}Quote No:  {R}{c(BYLW)}{state.quote_no}{R}\n')
    out.append(f'{at(8,4)}{c(BBLK)}Total:     {R}{c(BGRN,bold=True)}{money(state.grand_total())}{R}\n')
    out.append(f'{at(9,4)}{c(BBLK)}Client:    {R}{c(WHT)}{state.client_company}  ·  {state.client_name}{R}\n')
    out.append(f'{at(11,4)}{c(BBLK)}You can now email, print, or share this file with your client.{R}\n')
    out.append(f'{at(13,4)}{c(BBLK)}Press q to quit, or r to build another quote.{R}')
    flush(out)

    while True:
        ch = getch()
        if ch in ('q', 'Q', '\x1b'): return 'quit'
        elif ch in ('r', 'R'): return 'restart'

# ── Quote document builder ────────────────────────────────────────────────────

def build_quote_lines(state: QuoteState, plain: bool = False) -> List[str]:
    W = 65
    SEP = '━' * W
    thin = '─' * W

    def hl(text, color=BWHT, bold=False):
        return text if plain else f'{c(color,bold=bold)}{text}{R}'

    def section(title):
        return [SEP, hl(title, BWHT, bold=True), SEP]

    today = datetime.now()
    valid = today + timedelta(days=QUOTE_VALIDITY)
    deposit = state.grand_total() * DEPOSIT_PCT / 100
    remainder = state.grand_total() - deposit

    tl_key, tl_label, tl_mult, tl_tag = next(
        (t for t in TIMELINE if t[0]==state.timeline_key), TIMELINE[2])

    lines = []
    lines += ['', SEP,
              f'  {hl(AGENCY_NAME, BWHT, bold=True)}',
              f'  {AGENCY_TAGLINE}',
              f'  {AGENCY_EMAIL}  ·  {AGENCY_PHONE}',
              f'  {AGENCY_WEB}  ·  {AGENCY_ADDR}',
              SEP, '']

    lines += ['', hl('QUOTATION', BWHT, bold=True), '']
    lines += [f'  Quote Reference:  {hl(state.quote_no, BYLW)}',
              f'  Date Issued:      {today.strftime("%B %d, %Y")}',
              f'  Valid Until:      {hl(valid.strftime("%B %d, %Y"), BRED)}',
              f'  Project Type:     {state.project_type}', '']

    lines += section('PREPARED FOR')
    lines += ['',
              f'  Company:    {hl(state.client_company or "—", BWHT, bold=True)}',
              f'  Contact:    {state.client_name or "—"}',
              f'  Email:      {state.client_email or "—"}',
              f'  Phone:      {state.client_phone or "—"}', '']

    lines += section('SCOPE & PRICING')

    subtotal = 0.0
    for sid in state.selected:
        if sid not in state.configs: continue
        cfg = state.configs[sid]
        info = CATALOG[sid]
        pkg_name = cfg['pkg_name']
        pkg_price = cfg['pkg_price']
        months = cfg.get('months', 1)
        recurring = info['recurring']

        lines.append('')
        svc_header = f'  {hl(info["name"].upper(), BCYN, bold=True)} — {pkg_name}'
        lines.append(svc_header)
        lines.append(f'  {thin}')
        for inc in cfg['pkg_includes']:
            lines.append(f'  · {inc}')
        if recurring:
            lines.append(f'  · {months}-month contract')

        addon_names = []
        addon_cost = 0.0
        for i, (label, price, rec) in enumerate(info.get('addons', [])):
            if i in cfg.get('addons', set()):
                if price is None:
                    ac = pkg_price * 0.35
                elif rec:
                    ac = price * months
                else:
                    ac = price
                addon_names.append((label, ac))
                addon_cost += ac

        base = pkg_price * (months if recurring else 1)
        svc_total = base + addon_cost
        subtotal += svc_total

        if addon_names:
            for label, ac in addon_names:
                lines.append(f'  + {label:<40}  +{money(ac):>10}')

        price_line = f'  {"("+str(months)+" × "+money(pkg_price)+"/mo)" if recurring else "":<38}  {money(svc_total):>10}'
        lines.append(hl(price_line, BYLW))
        lines.append('')

    lines.append(SEP)

    adjusted_sub = subtotal * tl_mult
    discount_amt  = adjusted_sub * state.discount_pct / 100
    grand         = adjusted_sub - discount_amt

    if tl_mult != 1.0:
        lines.append(f'  {"Subtotal":>50}  {money(subtotal):>10}')
        lines.append(f'  {f"Timeline ({tl_label})":>50}  {tl_tag:>10}')

    if state.discount_pct:
        lines.append(f'  {"Subtotal before discount":>50}  {money(adjusted_sub):>10}')
        lines.append(f'  {f"{state.discount_pct}% discount":>50}  -{money(discount_amt):>9}')

    lines.append(hl(f'  {"TOTAL":>50}  {money(grand):>10}', BWHT, bold=True))
    lines.append(SEP)

    lines += ['', hl('TIMELINE', BWHT, bold=True), '']
    lines += [f'  Urgency:      {tl_label}',
              f'  Project start: Upon receipt of deposit', '']

    lines += section('PAYMENT TERMS')
    lines += ['',
              f'  {DEPOSIT_PCT}% deposit due to begin work               {money(deposit)}',
              f'  Remaining balance due on delivery            {money(remainder)}',
              f'  Accepted: Bank transfer  ·  Credit card  ·  Check', '']

    if state.notes:
        lines += section('NOTES')
        lines += ['', f'  {state.notes}', '']

    lines += section('TERMS & CONDITIONS')
    lines += ['',
              f'  · This quote is valid for {QUOTE_VALIDITY} days from the date of issue.',
              '  · Work outside the agreed scope will be quoted separately.',
              '  · Prices are in USD and exclude applicable taxes.',
              '  · Client is responsible for providing required assets and approvals.', '']

    lines += [SEP, '',
              '  ACCEPTED BY:  ' + '_'*30 + '   Date: ' + '_'*12,
              '',
              '  SIGNATURE:    ' + '_'*30,
              '', SEP,
              '',
              f'  {"Thank you for your business.":^{W-4}}',
              '', SEP]

    return lines

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if sys.platform == 'win32':
        print('Windows not supported.'); sys.exit(1)

    def on_exit(sig, frame):
        show_cursor(); sys.stdout.write('\033[0m\n'); sys.exit(0)
    signal.signal(signal.SIGINT, on_exit)

    os.system('clear')
    hide_cursor()

    while True:
        state = QuoteState()

        # Build step list dynamically
        def get_steps():
            fixed_pre  = ['welcome', 'client', 'project_type', 'services']
            svc_steps  = [f'config:{sid}' for sid in state.selected]
            fixed_post = ['timeline', 'extras', 'preview', 'export']
            return fixed_pre + svc_steps + fixed_post

        current = 0
        steps = get_steps()

        try:
            while 0 <= current < len(steps):
                step_id = steps[current]
                total_display = len(steps) - 1  # exclude export from count

                if step_id == 'welcome':
                    result = step_welcome()
                elif step_id == 'client':
                    result = step_client(state, current, total_display)
                elif step_id == 'project_type':
                    result = step_project_type(state, current, total_display)
                elif step_id == 'services':
                    result = step_services(state, current, total_display)
                    if result == FORWARD:
                        steps = get_steps()   # rebuild with selected services
                elif step_id.startswith('config:'):
                    sid = step_id.split(':',1)[1]
                    result = step_configure(sid, state, current, total_display)
                elif step_id == 'timeline':
                    result = step_timeline(state, current, total_display)
                elif step_id == 'extras':
                    result = step_extras(state, current, total_display)
                elif step_id == 'preview':
                    result = step_preview(state, current, total_display)
                elif step_id == 'export':
                    show_cursor()
                    outcome = step_export(state)
                    hide_cursor()
                    if outcome == 'restart':
                        break
                    else:
                        return
                else:
                    result = FORWARD

                # Handle back on 'b' key (embedded in pick_one returns BACK via getch check)
                current += result

                if current < 0: current = 0

        finally:
            show_cursor()
            sys.stdout.write('\033[0m')
            sys.stdout.flush()

if __name__ == '__main__':
    main()
