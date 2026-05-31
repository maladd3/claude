#!/usr/bin/env python3
"""
CRYPTID TOURS CO. ™
  "We'll Find Them. Eventually."

Interactive management dashboard for the world's premier cryptid tourism company.
Run: python3 cryptid_tours.py
Keys: 1-4 to switch views, j/k (or arrows) in cryptid view, q to quit.
"""

import sys, os, time, random, signal, select, tty, termios, shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

# ── Terminal helpers ───────────────────────────────────────────────────────────

def getch_timeout(timeout: float = 2.0) -> Optional[str]:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if not ready:
            return None
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            r2, _, _ = select.select([sys.stdin], [], [], 0.05)
            if r2:
                ch += sys.stdin.read(2)
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

def hide_cursor(): sys.stdout.write('\033[?25l')
def show_cursor(): sys.stdout.write('\033[?25h')
def at(row, col): return f'\033[{row};{col}H'

# ── Colors ─────────────────────────────────────────────────────────────────────

R = '\033[0m'
def c(n, bold=False, dim=False):
    mods = ('1;' if bold else '') + ('2;' if dim else '')
    return f'\033[{mods}{n}m'

BLK,RED,GRN,YLW,BLU,MAG,CYN,WHT = 30,31,32,33,34,35,36,37
BBLK,BRED,BGRN,BYLW,BBLU,BMAG,BCYN,BWHT = 90,91,92,93,94,95,96,97
BGBLK,BGRED,BGGRN,BGYLW,BGBLU,BGMAG,BGCYN,BGWHT = 40,41,42,43,44,45,46,47

# ── Data models ────────────────────────────────────────────────────────────────

@dataclass
class Cryptid:
    cid: str; name: str; alias: str; region: str; category: str
    rarity: int; danger: int; description: str
    art: List[str]; verbs: List[str]; locations: List[str]

@dataclass
class Guide:
    name: str; specialty: str; years: int
    rating: float; sightings: int; catchphrase: str; status: str

@dataclass
class Tour:
    name: str; cid: str; guide: str
    pax: int; max_pax: int; progress: int
    status: str; departs: str; price: int; notes: str

# ── Cryptid roster ─────────────────────────────────────────────────────────────

CRYPTIDS: List[Cryptid] = [
    Cryptid('bigfoot', 'BIGFOOT', 'Sasquatch / Skunk Ape', 'Pacific Northwest, USA',
        'land', 2, 2,
        'Bipedal, hirsute, remarkably camera-shy. Known to steal beef jerky from campgrounds '
        'and leave size-22 footprints in places where no human being would want to go.',
        ['   ▄█▄   ', '  ▐███▌  ', ' ▐█████▌ ', '  ▐███▌  ', '  █▌ ▐█  ', ' ▐█   █▌ '],
        ['lumbering', 'sprinting', 'standing motionless', 'eating berries',
         'waving awkwardly', 'rummaging through a dumpster'],
        ['behind the tree line', 'near Cougar Creek', 'in the parking lot',
         'at the edge of Camp Ridgeline', 'outside the Port-a-Potty']),

    Cryptid('nessie', 'NESSIE', 'Loch Ness Monster / Nessiteras rhombopteryx', 'Loch Ness, Scotland',
        'aquatic', 3, 1,
        'Plesiosaur-adjacent. Possibly several animals sharing one identity. Enjoys rainy '
        'days, haggis, and being slightly out of focus in photographs.',
        ['         ~~~ ', ' ~~  ◕  ~~~~', ' ╭─────╮ ~~~ ', ' │     │~~~  ', '  ╰──────────╯'],
        ['surfacing briefly', 'creating large ripples', 'submerging rapidly',
         'staring at the camera', 'yawning enormously', 'doing a slow lap'],
        ['near the north shore', 'under Urquhart Castle', 'beside the tourist ferry',
         'at 40 meters depth', 'in the reeds at dawn']),

    Cryptid('mothman', 'MOTHMAN', 'The Winged One / Friend', 'Point Pleasant, WV (& wherever doom looms)',
        'aerial', 3, 3,
        'Red-eyed, winged, prophetic. Appears before major disasters as a warning, or possibly '
        'just enjoys a good bridge collapse. His Point Pleasant statue is inexplicably attractive.',
        ['  /▓\\ /▓\\  ', '   ▓▓▓▓▓   ', '   ◉███◉   ', '    ███    ', '   /   \\   '],
        ['hovering silently', 'perching on a rooftop', 'gliding overhead',
         'staring with red eyes', 'vanishing mid-flight', 'following a vehicle on I-64'],
        ['above the Silver Bridge', 'on the power lines', 'outside a bedroom window',
         'at the TNT Area', 'circling the courthouse']),

    Cryptid('chupacabra', 'CHUPACABRA', 'El Chupacabras / Goat Sucker', 'Puerto Rico, Southwest USA',
        'land', 3, 4,
        'Spiny, predatory, and surprisingly difficult to photograph despite being responsible '
        'for 40% of livestock incidents across three counties. Extremely fast. Smells sulfurous.',
        ['   ▲▲▲▲▲  ', '  ╔═════╗ ', '  ║◉   ◉║ ', '  ╚══▽══╝ ', '  /│   │\\ ', ' /_│   │_\\'],
        ['darting between shadows', 'crouching near livestock', 'sprinting across the road',
         'hissing at a rancher', 'circling a chicken coop', 'dissolving into darkness'],
        ['near the old Garza ranch', 'behind the gas station', 'in the dry riverbed',
         'outside Tucson', 'under a mesquite tree on Route 117']),

    Cryptid('jersey_devil', 'JERSEY DEVIL', 'Leeds Devil / The 13th Child', 'Pine Barrens, NJ, USA',
        'aerial', 4, 3,
        'Kangaroo body, bat wings, horse head, devil\'s hooves. Originated from a colonial '
        'New Jersey woman\'s unfortunate 13th pregnancy. Hates New Jersey more than you do.',
        ['   ^ ^    ', '  (o o)   ', ' /|~~~|\\ ', '  |   |   ', '  |   |   ', ' _/ \\_ '],
        ['shrieking overhead', 'walking upright through the pines', 'scratching at a barn door',
         'leaving cloven prints in snow', 'landing on a car roof'],
        ['deep in the Pine Barrens', 'near Leeds Point', 'above the cranberry bogs',
         'outside Chatsworth', 'over Route 72 at 2 AM']),

    Cryptid('flatwoods', 'FLATWOODS MONSTER', 'The Braxton County Monster / Lizzie',
        'Braxton County, West Virginia, USA',
        'interdimensional', 5, 3,
        'Towering, robed, possibly mechanical. Emits a nauseating mist and a high-pitched '
        'hissing sound. First reported in 1952. Has not returned calls. Very professional.',
        ['   ▓▓▓▓▓  ', '  ▓◉   ◉▓ ', '   ▓▓▓▓▓  ', '  /▓▓▓▓▓\\ ', ' / ▓▓▓▓▓ \\'],
        ['hovering above a field', 'emitting green mist', 'making a hissing sound',
         'gliding without legs', 'disappearing in a flash of light'],
        ['Fisher Farm', 'the old schoolhouse hill', 'Route 4 North', 'near Sutton Lake']),

    Cryptid('dover_demon', 'DOVER DEMON', 'The Glow-Eyed One', 'Dover, Massachusetts, USA',
        'interdimensional', 5, 2,
        'Small, pale, large head, glowing orange eyes. Spotted for exactly 48 hours in April '
        '1977 and never definitively again. Very punctual for an otherworldly entity.',
        ['    ◎◎    ', '  (·   ·)  ', '   ─────   ', '   │   │   ', '   ╰───╯   '],
        ['crouching on a stone wall', 'peering around a tree', 'running alongside the road',
         'standing in a field at dusk', 'staring motionlessly for several minutes'],
        ['Farm Street', 'Miller High Road', 'near the Milky Way bar quarry', 'Springdale Ave']),
]

# ── Guide roster ───────────────────────────────────────────────────────────────

GUIDES: List[Guide] = [
    Guide('Dale Hawkins', 'Bigfoot & Appalachian Cryptids', 23, 4.7, 3,
          '"I haven\'t confirmed a sighting yet, but I\'ve had 3 near-misses. That totally counts."',
          'on_tour'),
    Guide('Dr. Fiona MacTavish', 'Aquatic Cryptids (PhD, Marine Biology*)', 14, 4.9, 0,
          '"*The PhD is in Marine Biology. The cryptozoology part is strongly implied by context."',
          'available'),
    Guide('Rex Donovan', 'Mothman & Aerial Cryptids', 8, 4.2, 1,
          '"He found me, really. I just followed the signs. I always follow the signs."',
          'on_tour'),
    Guide('Carmen Vega', 'Southwest & Latin American Cryptids', 11, 4.8, 2,
          '"Chupacabra is real. I have the livestock reports and a very compelling spreadsheet."',
          'on_tour'),
    Guide('Barry "The Fox" Phelps', 'General Cryptids, Former Trophy Hunter', 19, 3.9, 0,
          '"I switched to photographing them. Less paperwork. Marginally less danger."',
          'available'),
    Guide('Yuki Tanaka', 'Interdimensional & Alien-Adjacent Cryptids', 6, 4.6, 1,
          '"The Flatwoods Monster is not scary if you bring the right crystals. I have data."',
          'missing'),
]

# ── Tour manifest ──────────────────────────────────────────────────────────────

TOURS: List[Tour] = [
    Tour('Bigfoot Bonanza',       'bigfoot',      'Dale Hawkins',              8, 8,  72, 'active',    '06:00', 189, 'Strong footprints found at Mile 14. Dale is "cautiously ecstatic."'),
    Tour('Nessie Night Watch',    'nessie',       'Dr. Fiona MacTavish',       4, 6,  45, 'active',    '20:00', 299, 'Sonar contact at 40m. Group is vibrating with excitement.'),
    Tour('Mothman Express',       'mothman',      'Rex Donovan',               6, 6,  88, 'active',    '22:00', 249, 'Something followed the van for 12 miles. Rex is weeping with joy.'),
    Tour('Chupacabra Crawl',      'chupacabra',   'Carmen Vega',               3, 4,  30, 'searching', '18:00', 219, 'Tour bus got a flat. Carmen says it\'s "clearly a sign." Bus disagrees.'),
    Tour('Pine Barrens Plunge',   'jersey_devil', 'Barry "The Fox" Phelps',    5, 6,  15, 'active',    '21:30', 179, 'Heard a shriek at 23:14. Could be an owl. Barry strongly disagrees.'),
    Tour('Flatwoods Expedition',  'flatwoods',    'Yuki Tanaka',               0, 4,   0, 'cancelled', '09:00', 399, 'Guide did not show up. Third time this month. Investigating.'),
    Tour('Dover Demon Overnight', 'dover_demon',  'Barry "The Fox" Phelps',    2, 6,  55, 'active',    '23:00', 229, 'Two guests claim they saw glowing eyes. Barry saw a possum.'),
]

REVENUE_7DAY = [3_200, 5_100, 4_800, 7_200, 6_900, 8_400, 9_120]
DAYS_7 = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

REVIEWS = [
    ('★★★★★', 'BigfootBeliever99',  '"We found a footprint! Dale said a deer COULD have made it. WE KNOW BETTER."'),
    ('★★☆☆☆', 'SkepticalSteve42',   '"Saw a large shadow. Could have been anything. It was probably anything."'),
    ('★★★★★', 'NessieNancy_Loch',   '"The sonar showed a blob! Dr. MacTavish said sediment. I said NESSIE."'),
    ('★★★☆☆', 'RegularRoger_OH',    '"Rex Donovan cried at least twice during the tour. Still, three stars."'),
    ('★★★★★', 'TrueBeliever_Deb',   '"Chupacabra literally stared at the bus. Carmen kept driving. Bold."'),
    ('★☆☆☆☆', 'DisappointedDave',   '"Yuki was nowhere. Pine Barrens were muddy. I lost a shoe. Zero stars if I could."'),
    ('★★★★★', 'MothmanMom_WV',      '"It was right outside my window. Rex said we made eye contact. Life-changing."'),
    ('★★★★☆', 'OpenMindedOlga',     '"No cryptids, but the company was lovely and Barry made excellent sandwiches."'),
    ('★★★★★', 'CryptoKid2009',      '"This was for my 14th birthday. Best. Birthday. Ever. I am a changed person."'),
    ('★★★☆☆', 'AccountantMike',     '"I went for the data. The data was inconclusive. But the bus had good AC."'),
]

# ── Sighting feed ─────────────────────────────────────────────────────────────

def new_sighting(minutes_ago: int = 0) -> str:
    cr = random.choice(CRYPTIDS)
    verb = random.choice(cr.verbs)
    loc = random.choice(cr.locations)
    t = (datetime.now() - timedelta(minutes=minutes_ago)).strftime('%H:%M')
    conf = random.choice(['UNVERIFIED', 'UNVERIFIED', 'UNVERIFIED', 'CONFIRMED!', 'DISPUTED'])
    conf_c = BYLW if conf == 'UNVERIFIED' else (BGRN if conf == 'CONFIRMED!' else BRED)
    return (f'  {c(BBLK)}{t}{R}  {c(BYLW)}●{R} {c(BWHT,bold=True)}{cr.name:<18}{R}'
            f'{verb} {c(BBLK)}{loc}{R}  {c(conf_c)}{conf}{R}')

def build_feed(n=20) -> List[str]:
    offset = 0
    lines = []
    for _ in range(n):
        offset += random.randint(1, 12)
        lines.append(new_sighting(offset))
    return lines

# ── Drawing primitives ────────────────────────────────────────────────────────

def hbar(val, mx, width, color):
    if mx <= 0: return ''
    filled = max(0, int(val / mx * width))
    return f'{c(color)}{"█"*filled}{c(BBLK)}{"░"*(width-filled)}{R}'

def stars(n, mx=5, color=BYLW):
    return f'{c(color)}{"★"*n}{c(BBLK)}{"☆"*(mx-n)}{R}'

STATUS_COLOR = {'active': BGRN, 'searching': BYLW, 'completed': BBLK,
                'cancelled': BRED, 'on_tour': BGRN, 'available': BYLW,
                'missing': BRED, 'sick': MAG}

DANGER_LABEL = ['', 'Cuddly', 'Mild', 'Spooky', 'Dangerous', 'EXTREME']
DANGER_COLOR = ['', BGRN, BGRN, BYLW, BRED, BRED]
CAT_COLOR    = {'land': BGRN, 'aquatic': BCYN, 'aerial': BBLU,
                'interdimensional': BMAG}

def tbox_top(row, col, w, title='', color=BBLK):
    inner = w - 2
    if title:
        filler = inner - len(title) - 4
        top = f'╔═ {title} {"═"*max(0,filler)}╗'
    else:
        top = f'╔{"═"*inner}╗'
    return f'{at(row,col)}{c(color)}{top}{R}'

def tbox_bot(row, col, w, color=BBLK):
    return f'{at(row,col)}{c(color)}╚{"═"*(w-2)}╝{R}'

def tbox_row(row, col, w, color=BBLK):
    return f'{at(row,col)}{c(color)}║{" "*(w-2)}║{R}'

# ── Layout constants ──────────────────────────────────────────────────────────

COLS, ROWS = shutil.get_terminal_size((130, 42))
COLS = max(110, COLS)
ROWS = max(36, ROWS)

# ── Views ─────────────────────────────────────────────────────────────────────

def render_header(view: int) -> str:
    views = {1:'DASHBOARD', 2:'CRYPTID DATABASE', 3:'TOUR TRACKER', 4:'FINANCIALS'}
    logo   = '  CRYPTID TOURS CO.  '
    tag    = '"We\'ll Find Them. Eventually." (TM)'
    crumb  = f'  ▶ {views[view]}  '
    mid    = ' ' * max(0, COLS - len(logo) - len(tag) - len(crumb))
    nav    = f'  [1] Dashboard   [2] Cryptids   [3] Tours   [4] Financials   [Q] Quit  '
    nav_pad = ' ' * max(0, (COLS - len(nav)) // 2)
    sep    = '═' * COLS
    return (
        f'{at(1,1)}{c(BGGRN)}{c(BWHT,bold=True)}{logo}{mid}{tag}{crumb}{R}\n'
        f'{at(2,1)}{c(BGBLK)}{c(BBLK)}{" "*COLS}{R}'
        f'{at(2,1)}{c(BGBLK)}{c(BBLK)}{nav_pad}{nav}{R}\n'
        f'{at(3,1)}{c(BBLK)}{sep}{R}'
    )

def render_dashboard(feed: List[str], tick: int) -> str:
    out = []
    ROW = 4
    half = COLS // 2 - 1
    rhs  = half + 3

    # ── Left: live feed ──
    pulse = c(BRED) + ['◉', '○'][tick % 2] + R
    out.append(f'{at(ROW,1)}{c(BRED,bold=True)}╔═ LIVE SIGHTING FEED {"═"*(half-23)}{pulse}{c(BRED,bold=True)} LIVE ╗{R}')
    feed_h = 13
    for i in range(feed_h):
        idx = len(feed) - feed_h + i
        line = feed[idx] if idx >= 0 else ''
        out.append(f'{at(ROW+1+i, 2)}{line}')
    out.append(f'{at(ROW+feed_h+1,1)}{c(BRED,bold=True)}╚{"═"*(half-1)}╝{R}')

    # ── Right: ops stats ──
    active_tours   = sum(1 for t in TOURS if t.status == 'active')
    guides_out     = sum(1 for g in GUIDES if g.status == 'on_tour')
    guides_missing = sum(1 for g in GUIDES if g.status == 'missing')
    pax_today      = sum(t.pax for t in TOURS if t.status in ('active','completed','searching'))
    rev_today      = sum(t.pax * t.price for t in TOURS if t.status in ('active','completed'))

    out.append(tbox_top(ROW, rhs, COLS-half-2, 'OPERATIONS TODAY', BCYN))
    stats = [
        ('Active Tours',      f'{c(BYLW)}{active_tours}{R}'),
        ('Guides Deployed',   f'{c(BYLW)}{guides_out}{R}'),
        ('Guides Missing',    f'{c(BRED)}{guides_missing}{R}'),
        ('Passengers Aboard', f'{c(BGRN)}{pax_today}{R}'),
        ('Revenue Today',     f'{c(BGRN)}${rev_today:,}{R}'),
        ('Unverified Sightings', f'{c(BYLW)}{len(feed)}{R}  (and counting)'),
    ]
    for i, (label, val) in enumerate(stats):
        out.append(f'{at(ROW+1+i, rhs+2)}{c(BBLK)}{label:<22}{R}{val}')

    # Tour spotlight
    hi = TOURS[tick % len(TOURS)]
    out.append(f'{at(ROW+8, rhs+2)}{c(BCYN,bold=True)}TONIGHT\'S SPOTLIGHT{R}')
    out.append(f'{at(ROW+9, rhs+2)}{c(BBLK)}{"─"*(COLS-half-6)}{R}')
    seats_left = hi.max_pax - hi.pax
    seat_c = BGRN if seats_left > 2 else (BYLW if seats_left > 0 else BRED)
    spotlight_cr = next((cr for cr in CRYPTIDS if cr.cid == hi.cid), CRYPTIDS[0])
    out.append(f'{at(ROW+10, rhs+2)}{c(BWHT,bold=True)}{hi.name}{R}')
    out.append(f'{at(ROW+11, rhs+2)}{c(BBLK)}Target:{R}  {c(BMAG)}{spotlight_cr.name}{R}')
    out.append(f'{at(ROW+12, rhs+2)}{c(BBLK)}Guide:{R}   {c(BCYN)}{hi.guide}{R}')
    out.append(f'{at(ROW+13, rhs+2)}{c(BBLK)}Seats:{R}   {c(seat_c)}{seats_left} remaining{R}')
    out.append(f'{at(ROW+14, rhs+2)}{c(BBLK)}Price:{R}   {c(BYLW)}${hi.price}/person{R}')
    out.append(tbox_bot(ROW+15, rhs, COLS-half-2, BCYN))

    # ── Tour tracker strip ──
    TROW = ROW + feed_h + 3
    out.append(tbox_top(TROW, 1, COLS, 'TOUR TRACKER', BGRN))
    for i, tour in enumerate(TOURS[:5]):
        tr = TROW + 1 + i
        sc = STATUS_COLOR.get(tour.status, WHT)
        pb = hbar(tour.progress, 100, 14, sc)
        cr_name = next((cr.name for cr in CRYPTIDS if cr.cid == tour.cid), '???')
        line = (f'{c(BWHT,bold=True)}{tour.name:<22}{R}'
                f'{pb} {tour.progress:>3}%  '
                f'{c(sc)}{tour.status.upper():<12}{R}'
                f'{c(BCYN)}{tour.guide:<24}{R}'
                f'{c(BMAG)}{cr_name:<20}{R}'
                f'{c(BYLW)}{tour.pax}/{tour.max_pax} pax{R}')
        out.append(f'{at(tr, 3)}{line}')
    out.append(tbox_bot(TROW+6, 1, COLS, BGRN))

    # ── Review ticker ──
    rev = REVIEWS[tick % len(REVIEWS)]
    rev_txt = f'  {rev[0]}  {rev[1]}: {rev[2]}'
    out.append(f'{at(ROWS-1, 1)}{c(BGBLK)}{c(BYLW)}{rev_txt[:COLS]:<{COLS}}{R}')

    return ''.join(out)

def render_cryptids(sel: int) -> str:
    out = []
    ROW = 4
    lw = 30
    rhs = lw + 3
    rw = COLS - lw - 4

    # ── Left: list ──
    out.append(tbox_top(ROW, 1, lw, 'DATABASE', BMAG))
    for i, cr in enumerate(CRYPTIDS):
        r = ROW + 1 + i * 2
        if i == sel:
            out.append(f'{at(r,2)}{c(BGMAG)}{c(BWHT,bold=True)} ▶ {cr.name:<{lw-5}} {R}')
        else:
            out.append(f'{at(r,2)}{c(BMAG)}   {cr.name:<{lw-5}}{R}')
        out.append(f'{at(r+1,5)}{c(BBLK)}{cr.region[:lw-6]}{R}')
    out.append(tbox_bot(ROW + len(CRYPTIDS)*2 + 1, 1, lw, BMAG))

    # ── Right: detail ──
    cr = CRYPTIDS[sel]
    out.append(tbox_top(ROW, rhs, rw, cr.name, BMAG))

    # ASCII art (top-right of detail box)
    art_col = rhs + rw - max(len(l) for l in cr.art) - 3
    for i, line in enumerate(cr.art):
        out.append(f'{at(ROW+1+i, art_col)}{c(BGRN)}{line}{R}')

    dr = ROW + 1
    out.append(f'{at(dr,   rhs+2)}{c(BBLK)}Alias    {R}{c(BWHT)}{cr.alias}{R}')
    out.append(f'{at(dr+1, rhs+2)}{c(BBLK)}Region   {R}{c(BYLW)}{cr.region}{R}')
    out.append(f'{at(dr+2, rhs+2)}{c(BBLK)}Category {R}{c(CAT_COLOR.get(cr.category,WHT))}{cr.category.upper()}{R}')
    out.append(f'{at(dr+3, rhs+2)}{c(BBLK)}Rarity   {R}{stars(cr.rarity)}')
    out.append(f'{at(dr+4, rhs+2)}{c(BBLK)}Danger   {R}{c(DANGER_COLOR[cr.danger])}{DANGER_LABEL[cr.danger]}{R}')

    out.append(f'{at(dr+6, rhs+2)}{c(BBLK)}{"─"*(rw-4)}{R}')

    # Description word-wrap
    words = cr.description.split()
    lines, cur, cur_len = [], [], 0
    for w in words:
        if cur_len + len(w) + 1 > rw - 6:
            lines.append(' '.join(cur)); cur = [w]; cur_len = len(w)
        else:
            cur.append(w); cur_len += len(w) + 1
    if cur: lines.append(' '.join(cur))
    for i, line in enumerate(lines[:4]):
        out.append(f'{at(dr+7+i, rhs+2)}{c(WHT)}{line}{R}')

    out.append(f'{at(dr+12, rhs+2)}{c(BBLK)}{"─"*(rw-4)}{R}')
    out.append(f'{at(dr+13, rhs+2)}{c(BCYN,bold=True)}Known Sighting Behaviors{R}')
    for i, v in enumerate(cr.verbs[:4]):
        out.append(f'{at(dr+14+i, rhs+4)}{c(BBLK)}◆{R} {c(WHT)}{v}{R}')

    out.append(f'{at(dr+19, rhs+2)}{c(BBLK)}{"─"*(rw-4)}{R}')
    out.append(f'{at(dr+20, rhs+2)}{c(BCYN,bold=True)}Active Tours{R}')
    tours_for = [t for t in TOURS if t.cid == cr.cid]
    if tours_for:
        for i, t in enumerate(tours_for[:2]):
            sc = STATUS_COLOR.get(t.status, WHT)
            out.append(f'{at(dr+21+i, rhs+4)}{c(sc)}◆{R} {t.name}  '
                       f'{c(BBLK)}${t.price}/pp  {t.pax}/{t.max_pax} pax  [{t.status}]{R}')
    else:
        out.append(f'{at(dr+21, rhs+4)}{c(BBLK)}No tours currently scheduled.{R}')

    out.append(f'{at(ROWS-1,1)}{c(BBLK)}  ↑/k Previous   ↓/j Next   1-4 Switch View{R}')
    return ''.join(out)

def render_tours() -> str:
    out = []
    ROW = 4
    out.append(tbox_top(ROW, 1, COLS, 'TOUR TRACKER — FULL VIEW', BGRN))
    ROW += 1
    for tour in TOURS:
        cr = next((cr for cr in CRYPTIDS if cr.cid == tour.cid), CRYPTIDS[0])
        guide = next((g for g in GUIDES if g.name == tour.guide), None)
        sc = STATUS_COLOR.get(tour.status, WHT)

        out.append(f'{at(ROW,1)}{c(BBLK)}╟{"─"*(COLS-2)}╢{R}')
        ROW += 1
        seats = tour.max_pax - tour.pax
        seat_c = BGRN if seats > 2 else (BYLW if seats > 0 else BRED)
        out.append(f'{at(ROW,3)}{c(BWHT,bold=True)}{tour.name:<26}{R}'
                   f'{c(sc)}[{tour.status.upper()}]{R}')
        out.append(f'{at(ROW,45)}{c(BBLK)}Target:{R} {c(BMAG)}{cr.name}{R}')
        out.append(f'{at(ROW,72)}{c(BBLK)}Departs:{R} {c(WHT)}{tour.departs}{R}')
        out.append(f'{at(ROW,88)}{c(BBLK)}Price:{R} {c(BYLW)}${tour.price}/pp{R}')
        ROW += 1
        pb = hbar(tour.progress, 100, 28, sc)
        out.append(f'{at(ROW,3)}{pb} {tour.progress:>3}%   '
                   f'{c(BBLK)}Pax:{R} {c(BYLW)}{tour.pax}/{tour.max_pax}{R}  '
                   f'{c(seat_c)}{seats} seats open{R}   '
                   f'{c(BBLK)}Guide:{R} {c(BCYN)}{tour.guide}{R}')
        ROW += 1
        if tour.notes:
            out.append(f'{at(ROW,3)}{c(BBLK)}Field report:{R} {c(WHT)}{tour.notes[:COLS-20]}{R}')
            ROW += 1
        ROW += 1
        if ROW > ROWS - 3: break

    out.append(f'{at(ROW,1)}{c(BGRN,bold=True)}╚{"═"*(COLS-2)}╝{R}')
    return ''.join(out)

def render_financials() -> str:
    out = []
    ROW = 4
    out.append(tbox_top(ROW, 1, COLS, 'FINANCIAL OVERVIEW', BYLW))

    # Revenue bar chart
    out.append(f'{at(ROW+1, 3)}{c(BWHT,bold=True)}7-Day Revenue{R}')
    chart_h = 9
    max_rev = max(REVENUE_7DAY)
    for i, (day, rev) in enumerate(zip(DAYS_7, REVENUE_7DAY)):
        col = 4 + i * 10
        bar_h = max(1, int(rev / max_rev * chart_h))
        for r in range(chart_h, 0, -1):
            clr = BYLW if r == bar_h else (BGRN if r < bar_h else BBLK)
            out.append(f'{at(ROW+2+(chart_h-r), col)}{c(clr)}{"▐██▌"}{R}')
        out.append(f'{at(ROW+2+chart_h+1, col)}{c(BBLK)}{day}{R}')
        out.append(f'{at(ROW+2+chart_h+2, col-1)}{c(BYLW)}${rev//1000}k{R}')

    # KPI panel
    sc = COLS // 2 + 8
    total_7d = sum(REVENUE_7DAY)
    mtd_extra = 21_480
    mtd = total_7d + mtd_extra
    out.append(f'{at(ROW+2,  sc)}{c(BWHT,bold=True)}KEY METRICS{R}')
    out.append(f'{at(ROW+3,  sc)}{c(BBLK)}{"─"*30}{R}')
    metrics = [
        ('7-Day Revenue',       f'{c(BGRN)}${total_7d:>10,}{R}'),
        ('Month-to-Date',       f'{c(BGRN)}${mtd:>10,}{R}'),
        ('Avg Tour Value',      f'{c(BYLW)}${"1,247":>10}{R}'),
        ('Cancellation Rate',   f'{c(BRED)}{"16.7%":>10}{R}'),
        ('Guide Utilization',   f'{c(BGRN)}{"66.7%":>10}{R}'),
        ('Repeat Customers',    f'{c(BCYN)}{"38.2%":>10}{R}'),
        ('Sightings / Tour',    f'{c(BYLW)}{"0.0 (avg)":>10}{R}'),
    ]
    for i, (label, val) in enumerate(metrics):
        out.append(f'{at(ROW+4+i,  sc)}{c(BBLK)}{label:<22}{R}{val}')
    out.append(f'{at(ROW+12, sc)}{c(BBLK)}{"─"*30}{R}')
    out.append(f'{at(ROW+13, sc)}{c(BBLK)}Top earner:    {R}{c(BYLW)}Nessie Night Watch{R}')
    out.append(f'{at(ROW+14, sc)}{c(BBLK)}Most cancelled:{R}{c(BRED)} Flatwoods Expedition{R}')
    out.append(f'{at(ROW+15, sc)}{c(BBLK)}Best guide:    {R}{c(BCYN)} Dr. Fiona MacTavish{R}')
    out.append(f'{at(ROW+16, sc)}{c(BBLK)}Missing guides:{R}{c(BRED)} 1 (Yuki Tanaka){R}')

    # Guide roster
    GR = ROW + chart_h + 7
    out.append(f'{at(GR,   3)}{c(BCYN,bold=True)}GUIDE ROSTER{R}')
    out.append(f'{at(GR+1, 3)}{c(BBLK)}{"─"*(COLS-6)}{R}')
    hdr = f'{"NAME":<24}{"SPECIALTY":<36}{"EXP":>6}{"RATING":>8}{"SIGHTINGS":>11}{"STATUS":>14}'
    out.append(f'{at(GR+2, 3)}{c(BBLK)}{hdr}{R}')
    for i, g in enumerate(GUIDES):
        r = GR + 3 + i
        sc2 = STATUS_COLOR.get(g.status, WHT)
        out.append(f'{at(r,3)}'
                   f'{c(BWHT)}{g.name:<24}{R}'
                   f'{c(WHT,dim=True)}{g.specialty:<36}{R}'
                   f'{c(BBLK)}{g.years:>5}y{R}'
                   f'{c(BYLW)}{g.rating:>7.1f}★{R}'
                   f'{c(BGRN)}{g.sightings:>10}{R}'
                   f'{c(sc2)}{g.status.replace("_"," ").upper():>14}{R}')
    out.append(f'{at(GR+3+len(GUIDES)+1,3)}{c(BBLK)}{"─"*(COLS-6)}{R}')

    # Recent reviews
    out.append(f'{at(GR+3+len(GUIDES)+2, 3)}{c(BWHT,bold=True)}RECENT REVIEWS{R}')
    for i, (stars_str, name, text) in enumerate(REVIEWS[:3]):
        out.append(f'{at(GR+3+len(GUIDES)+3+i, 5)}'
                   f'{c(BYLW)}{stars_str}{R}  {c(BCYN)}{name:<18}{R}  {c(WHT,dim=True)}{text[:COLS-50]}{R}')

    out.append(tbox_bot(min(GR+3+len(GUIDES)+7, ROWS-1), 1, COLS, BYLW))
    return ''.join(out)

# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    if sys.platform == 'win32':
        print('Windows not supported.'); sys.exit(1)

    def on_exit(sig, frame):
        show_cursor()
        sys.stdout.write('\033[0m\033[2J\033[H')
        sys.exit(0)

    signal.signal(signal.SIGINT, on_exit)

    os.system('clear')
    show_splash()
    hide_cursor()
    sys.stdout.write('\033[2J')

    view = 1
    csel = 0
    tick = 0
    feed = build_feed(20)

    try:
        while True:
            out = ['\033[H', render_header(view)]
            if   view == 1: out.append(render_dashboard(feed, tick))
            elif view == 2: out.append(render_cryptids(csel))
            elif view == 3: out.append(render_tours())
            elif view == 4: out.append(render_financials())
            sys.stdout.write(''.join(out))
            sys.stdout.flush()

            key = getch_timeout(2.0)
            tick += 1

            if key is None:
                cr = random.choice(CRYPTIDS)
                feed.append(new_sighting(0))
                continue

            if key in ('q', 'Q'): break
            elif key == '1': view = 1
            elif key == '2': view = 2
            elif key == '3': view = 3
            elif key == '4': view = 4
            elif key in ('j', '\x1b[B') and view == 2:
                csel = (csel + 1) % len(CRYPTIDS)
            elif key in ('k', '\x1b[A') and view == 2:
                csel = (csel - 1) % len(CRYPTIDS)

    finally:
        show_cursor()
        sys.stdout.write('\033[0m\033[2J\033[H')
        sys.stdout.flush()


def show_splash():
    logo = [
        r"   ___  ____  _  _  ____  ____  ____  ____    ____  _____  _  _  ____  ____",
        r"  / __)(  _ \( \/ )(  _ \(_  _)(_  _)(  _ \  (_  _)(  _  )( )( )(  _ \/ ___)",
        r" ( (__  )   / \  /  )___/  )(    )(   )(_) )   )(   )(_)(  )()(  )   /\__ \ ",
        r"  \___)(__)  (__)  (__)   (__) (__) (____/   (__) (_____) \__/ (__)  (____/",
    ]
    colors = [BGRN, BYLW, BRED, BMAG]
    sub = [
        '',
        f'            {c(BWHT,bold=True)}"We\'ll Find Them. Eventually." (TM){R}',
        '',
        f'        {c(BBLK)}Navigate the world\'s premier cryptid tourism management system.{R}',
        f'        {c(BBLK)}Live sighting feed  ·  Cryptid database  ·  Tour tracker  ·  Financials{R}',
        '',
        f'                          {c(BYLW)}Press any key to open the dashboard...{R}',
    ]
    out = ['\033[2J\033[H']
    for i, (line, col) in enumerate(zip(logo, colors)):
        out.append(f'{at(4+i, 2)}{c(col,bold=True)}{line}{R}')
    for i, line in enumerate(sub):
        out.append(f'{at(9+i, 1)}{line}')
    sys.stdout.write(''.join(out))
    sys.stdout.flush()
    getch_timeout(30.0)


if __name__ == '__main__':
    main()
