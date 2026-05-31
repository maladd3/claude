#!/usr/bin/env python3
"""
THE DEPTHS — A Terminal Roguelike
Navigate procedurally generated dungeons. Fight monsters. Collect loot. Survive 5 floors.
Run: python3 depths.py
"""

import sys, os, random, math, tty, termios, select, signal, collections, shutil
from dataclasses import dataclass, field
from typing import List, Tuple, Set, Optional

# ── Terminal I/O ──────────────────────────────────────────────────────────────

def getch() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            ready, _, _ = select.select([sys.stdin], [], [], 0.05)
            if ready:
                ch += sys.stdin.read(2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch

def hide_cursor(): sys.stdout.write('\033[?25l')
def show_cursor(): sys.stdout.write('\033[?25h')

# ── Colors ────────────────────────────────────────────────────────────────────

R = '\033[0m'

def fg(n, bold=False):
    return f'\033[{"1;" if bold else ""}{n}m'

BLK,RED,GRN,YLW,BLU,MAG,CYN,WHT = 30,31,32,33,34,35,36,37
BBLK,BRED,BGRN,BYLW,BBLU,BMAG,BCYN,BWHT = 90,91,92,93,94,95,96,97
BGBLK,BGRED,BGGRN,BGYLW,BGBLU,BGMAG,BGCYN,BGWHT = 40,41,42,43,44,45,46,47

# ── Dungeon dimensions (adapt to terminal) ────────────────────────────────────

_cols, _rows = shutil.get_terminal_size((120, 40))
W = max(40, min(72, _cols - 26))
H = max(20, min(30, _rows - 8))

WALL  = '#'
FLOOR = '.'
STAIR = '>'

# ── BSP Dungeon Generator ─────────────────────────────────────────────────────

@dataclass
class Room:
    x: int; y: int; w: int; h: int

    @property
    def cx(self): return self.x + self.w // 2
    @property
    def cy(self): return self.y + self.h // 2

    def rand_pt(self):
        return (random.randint(self.x + 1, self.x + self.w - 2),
                random.randint(self.y + 1, self.y + self.h - 2))


class BSPNode:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.left = self.right = None
        self.room: Optional[Room] = None

    def split(self, min_sz=9, depth=0):
        can_v = self.w >= min_sz * 2
        can_h = self.h >= min_sz * 2
        if not can_v and not can_h:
            return
        if depth > 1 and random.random() < 0.12:
            return
        if can_v and can_h:
            vert = self.w > self.h * 1.25 or (self.h <= self.w * 1.25 and random.random() < 0.5)
        else:
            vert = can_v
        if vert:
            s = random.randint(min_sz, self.w - min_sz)
            self.left  = BSPNode(self.x, self.y, s, self.h)
            self.right = BSPNode(self.x + s, self.y, self.w - s, self.h)
        else:
            s = random.randint(min_sz, self.h - min_sz)
            self.left  = BSPNode(self.x, self.y, self.w, s)
            self.right = BSPNode(self.x, self.y + s, self.w, self.h - s)
        self.left.split(min_sz, depth + 1)
        self.right.split(min_sz, depth + 1)

    def carve(self, grid, rooms):
        if self.left:
            self.left.carve(grid, rooms)
            self.right.carve(grid, rooms)
            la = self.left.any_room()
            ra = self.right.any_room()
            if la and ra:
                _tunnel(grid, la.cx, la.cy, ra.cx, ra.cy)
        else:
            rw = random.randint(max(4, self.w // 3), max(4, self.w - 2))
            rh = random.randint(max(4, self.h // 3), max(4, self.h - 2))
            rx = self.x + random.randint(1, max(1, self.w - rw - 1))
            ry = self.y + random.randint(1, max(1, self.h - rh - 1))
            rx, ry = max(1, min(rx, W - rw - 1)), max(1, min(ry, H - rh - 1))
            rw, rh = min(rw, W - rx - 1), min(rh, H - ry - 1)
            if rw >= 4 and rh >= 4:
                self.room = Room(rx, ry, rw, rh)
                rooms.append(self.room)
                for yy in range(ry, ry + rh):
                    for xx in range(rx, rx + rw):
                        grid[yy][xx] = FLOOR

    def any_room(self) -> Optional[Room]:
        if self.room:
            return self.room
        cands = []
        for child in (self.left, self.right):
            if child:
                r = child.any_room()
                if r: cands.append(r)
        return random.choice(cands) if cands else None


def _tunnel(grid, x1, y1, x2, y2):
    if random.random() < 0.5:
        for x in range(min(x1,x2), max(x1,x2)+1):
            if 0 < x < W and 0 < y1 < H: grid[y1][x] = FLOOR
        for y in range(min(y1,y2), max(y1,y2)+1):
            if 0 < y < H and 0 < x2 < W: grid[y][x2] = FLOOR
    else:
        for y in range(min(y1,y2), max(y1,y2)+1):
            if 0 < y < H and 0 < x1 < W: grid[y][x1] = FLOOR
        for x in range(min(x1,x2), max(x1,x2)+1):
            if 0 < x < W and 0 < y2 < H: grid[y2][x] = FLOOR


def make_dungeon():
    grid = [[WALL] * W for _ in range(H)]
    rooms: List[Room] = []
    root = BSPNode(1, 1, W - 2, H - 2)
    root.split()
    root.carve(grid, rooms)
    return grid, rooms

# ── Field of View (raycasting) ────────────────────────────────────────────────

def compute_fov(grid, px, py, radius=9) -> Set[Tuple[int,int]]:
    vis: Set[Tuple[int,int]] = {(px, py)}
    for deg in range(360):
        rad = math.radians(deg)
        dx, dy = math.cos(rad), math.sin(rad)
        x, y = float(px), float(py)
        for _ in range(radius):
            xi, yi = int(round(x)), int(round(y))
            if not (0 <= xi < W and 0 <= yi < H): break
            vis.add((xi, yi))
            if grid[yi][xi] == WALL: break
            x += dx; y += dy
    return vis

# ── Items ─────────────────────────────────────────────────────────────────────

@dataclass
class Item:
    x: int; y: int
    name: str; char: str; color: int
    effect: str   # heal | atk+ | def+ | blast
    power: int

ITEM_POOL = [
    ('Health Potion',  '!', BRED,  'heal',  15),
    ('Elixir',         '!', RED,   'heal',  35),
    ('Short Sword',    '/', BWHT,  'atk+',   3),
    ('Battle Axe',     '/', BYLW,  'atk+',   6),
    ('Leather Armor',  ']', CYN,   'def+',   2),
    ('Iron Shield',    ']', BCYN,  'def+',   4),
    ('Fire Scroll',    '?', BMAG,  'blast', 28),
    ('Magic Ring',     '=', BYLW,  'atk+',   2),
    ('Amulet',         '"', BCYN,  'def+',   3),
]

# ── Monsters ──────────────────────────────────────────────────────────────────

class Monster:
    def __init__(self, x, y, char, color, name, hp, atk, dfn, exp, speed=1):
        self.x = x; self.y = y
        self.char = char; self.color = color; self.name = name
        self.hp = hp; self.max_hp = hp
        self.atk = atk; self.dfn = dfn; self.exp = exp
        self.speed = speed   # 1=normal, 2=slow (skips every other turn)
        self.tick = 0
        self.awake = False

# (char, color, name, hp, atk, dfn, exp, speed)
BESTIARY = [
    ('r', BYLW,  'Rat',      6,  3, 0,  3, 1),   # 0
    ('g', BGRN,  'Goblin',  12,  5, 1,  8, 1),   # 1
    ('o', GRN,   'Orc',     20,  8, 2, 15, 1),   # 2
    ('s', WHT,   'Skeleton',15,  7, 3, 12, 1),   # 3
    ('T', BRED,  'Troll',   42, 13, 5, 32, 2),   # 4
    ('V', MAG,   'Vampire', 30, 15, 3, 28, 1),   # 5
    ('D', BRED,  'Dragon',  70, 20, 7,105, 2),   # 6
]

def spawn(kind, x, y) -> Monster:
    c, col, n, hp, a, d, e, sp = BESTIARY[kind]
    return Monster(x, y, c, col, n, hp, a, d, e, sp)

FLOOR_POOL = {
    1: [0, 0, 0, 1],
    2: [0, 1, 1, 2],
    3: [1, 2, 2, 3],
    4: [2, 3, 4, 5],
    5: [3, 4, 5, 6],
}

# ── Player ────────────────────────────────────────────────────────────────────

class Player:
    def __init__(self):
        self.x = self.y = 0
        self.name = 'Hero'
        self.hp = self.max_hp = 30
        self.base_atk = 5; self.bonus_atk = 0
        self.base_dfn = 2; self.bonus_dfn = 0
        self.level = 1
        self.exp = 0; self.exp_need = 20
        self.floor_num = 1
        self.inventory: List[Item] = []

    @property
    def atk(self): return self.base_atk + self.bonus_atk
    @property
    def dfn(self): return self.base_dfn + self.bonus_dfn

# ── BFS Pathfinding ───────────────────────────────────────────────────────────

def find_path(grid, monsters, sx, sy, tx, ty) -> List[Tuple[int,int]]:
    if abs(sx-tx) + abs(sy-ty) > 22: return []
    blocked = {(m.x, m.y) for m in monsters}
    q = collections.deque([(sx, sy, [])])
    seen = {(sx, sy)}
    while q:
        x, y, path = q.popleft()
        for dx, dy in ((0,1),(0,-1),(1,0),(-1,0)):
            nx, ny = x+dx, y+dy
            if (nx, ny) in seen: continue
            if not (0 <= nx < W and 0 <= ny < H): continue
            if grid[ny][nx] == WALL: continue
            if (nx, ny) in blocked and (nx, ny) != (tx, ty): continue
            seen.add((nx, ny))
            np2 = path + [(nx, ny)]
            if nx == tx and ny == ty: return np2
            q.append((nx, ny, np2))
    return []

# ── UI layout constants ───────────────────────────────────────────────────────

SIDE_X      = W + 3         # sidebar column (1-indexed terminal col)
SEP_COL     = W + 2
MSG_START   = H + 2         # first message row (1-indexed)
N_MSGS      = 5
STATUS_ROW  = H + N_MSGS + 2

# ── Game ──────────────────────────────────────────────────────────────────────

class Game:
    def __init__(self):
        self.p = Player()
        self.grid: List[List[str]] = []
        self.rooms: List[Room] = []
        self.monsters: List[Monster] = []
        self.floor_items: List[Item] = []
        self.visible: Set[Tuple[int,int]] = set()
        self.seen: Set[Tuple[int,int]] = set()
        self.messages: List[str] = []
        self.turn = 0
        self.alive = True
        self.won = False
        self._dirty = True

    # ── Messages ──────────────────────────────────────────────────────────────

    def msg(self, text, color=None):
        self.messages.append(f'{fg(color)}{text}{R}' if color else text)
        if len(self.messages) > 80:
            self.messages.pop(0)

    # ── Floor generation ──────────────────────────────────────────────────────

    def load_floor(self, num: int):
        self.grid, self.rooms = make_dungeon()
        self.monsters = []
        self.floor_items = []
        self.seen = set()
        self.p.floor_num = num

        # Player in first room, stairs in last
        self.p.x, self.p.y = self.rooms[0].cx, self.rooms[0].cy
        lr = self.rooms[-1]
        self.grid[lr.cy][lr.cx] = STAIR

        pool = FLOOR_POOL.get(num, FLOOR_POOL[5])
        for room in self.rooms[1:]:
            for _ in range(random.randint(0, min(3, num))):
                kind = random.choice(pool)
                x, y = room.rand_pt()
                if not any(m.x == x and m.y == y for m in self.monsters):
                    self.monsters.append(spawn(kind, x, y))

        item_rooms = random.sample(self.rooms, min(len(self.rooms), max(2, len(self.rooms) // 2)))
        for room in item_rooms:
            if random.random() < 0.6:
                x, y = room.rand_pt()
                t = random.choice(ITEM_POOL)
                self.floor_items.append(Item(x, y, t[0], t[1], t[2], t[3], t[4]))

        self._refresh_fov()
        self.msg(f'You descend to floor {num}.', CYN)

    def _refresh_fov(self):
        self.visible = compute_fov(self.grid, self.p.x, self.p.y)
        self.seen |= self.visible

    # ── Rendering ─────────────────────────────────────────────────────────────

    def render(self):
        if not self._dirty: return
        out = ['\033[H']
        p = self.p

        for y in range(H):
            out.append(f'\033[{y+1};1H')
            for x in range(W):
                pos = (x, y)
                tile = self.grid[y][x]

                if pos == (p.x, p.y):
                    out.append(f'{fg(BWHT, bold=True)}@{R}'); continue

                mon = next((m for m in self.monsters if m.x == x and m.y == y), None)
                if mon and pos in self.visible:
                    bar = self._mon_hp(mon)
                    out.append(f'{fg(mon.color, bold=True)}{mon.char}{R}'); continue

                itm = next((i for i in self.floor_items if i.x == x and i.y == y), None)
                if itm and pos in self.visible:
                    out.append(f'{fg(itm.color)}{itm.char}{R}'); continue

                if pos in self.visible:
                    if tile == WALL:  out.append(f'{fg(WHT)}#{R}')
                    elif tile == FLOOR: out.append(f'\033[2;{WHT}m.{R}')
                    elif tile == STAIR: out.append(f'{fg(BYLW, bold=True)}>{R}')
                    else: out.append(' ')
                elif pos in self.seen:
                    ch = {'#':'#', '.':'.', '>':'>'}.get(tile, ' ')
                    out.append(f'{fg(BBLK)}{ch}{R}')
                else:
                    out.append(' ')

        # Vertical separator
        for y in range(1, H + 1):
            out.append(f'\033[{y};{SEP_COL}H{fg(BBLK)}│{R}')

        # Sidebar
        hp = max(0, p.hp)
        hp_r = hp / p.max_hp
        hpc = BGRN if hp_r > 0.5 else (BYLW if hp_r > 0.25 else BRED)
        side = [
            f'{fg(BYLW, bold=True)}THE DEPTHS{R}',
            f'{fg(BBLK)}─────────────────────{R}',
            f'Floor {fg(BCYN)}{p.floor_num}{R}/5   Turn {fg(CYN)}{self.turn}{R}',
            '',
            f'{fg(BWHT, bold=True)}◈ {p.name}{R}  Lv.{fg(BYLW)}{p.level}{R}',
            f'HP {fg(hpc)}{hp:>3}/{p.max_hp:<3}{R} {self._bar(hp, p.max_hp, 10, hpc)}',
            f'   {self._bar(p.exp, p.exp_need, 10, BMAG)} exp',
            f'ATK {fg(BRED)}{p.atk:<3}{R}  DEF {fg(BCYN)}{p.dfn:<3}{R}',
            '',
            f'{fg(BWHT, bold=True)}Pack {fg(BBLK)}({len(p.inventory)}/10){R}',
        ]
        for i, it in enumerate(p.inventory[:8]):
            side.append(f' {fg(BBLK)}{i+1}.{R}{fg(it.color)}{it.char}{R} {it.name}')
        if not p.inventory:
            side.append(f'  {fg(BBLK)}(empty){R}')
        side += [
            '', f'{fg(BWHT, bold=True)}Keys{R}',
            f'{fg(BBLK)}hjkl / ←↑↓→{R}',
            f'{fg(BBLK)}yubn diagonal{R}',
            f'{fg(BBLK)}g grab  i use{R}',
            f'{fg(BBLK)}> stairs q quit{R}',
            f'{fg(BBLK)}. wait   ? help{R}',
        ]
        for i, line in enumerate(side[:H]):
            out.append(f'\033[{i+1};{SIDE_X}H{line}')
        for i in range(len(side), H):
            out.append(f'\033[{i+1};{SIDE_X}H{"                      "}')

        # Horizontal separator
        out.append(f'\033[{H+1};1H{fg(BBLK)}{"─" * (W + 1)}{R}')

        # Message log
        msgs = self.messages[-N_MSGS:]
        for i in range(N_MSGS):
            row = MSG_START + i
            if i < len(msgs):
                out.append(f'\033[{row};1H{msgs[i]:<{W}}{R}')
            else:
                out.append(f'\033[{row};1H{" " * W}')

        # Status bar
        bar_txt = f' THE DEPTHS │ Floor {p.floor_num}/5 │ Turn {self.turn} │ HP {hp}/{p.max_hp} │ Lv {p.level} '
        out.append(f'\033[{STATUS_ROW};1H\033[{BGBLU};{BWHT}m{bar_txt:<{W+24}}{R}')

        sys.stdout.write(''.join(out))
        sys.stdout.flush()
        self._dirty = False

    def _bar(self, val, mx, width, color):
        if mx <= 0: return ''
        filled = max(0, int(val / mx * width))
        return f'{fg(color)}{"█"*filled}{fg(BBLK)}{"░"*(width-filled)}{R}'

    def _mon_hp(self, m):
        # just a helper kept for future use
        return ''

    # ── Combat ────────────────────────────────────────────────────────────────

    def _do_attack(self, attacker, defender):
        dmg = max(1, attacker.atk - defender.dfn + random.randint(-2, 3))
        defender.hp -= dmg
        if isinstance(attacker, Player):
            self.msg(f'You strike the {defender.name} for {fg(BYLW)}{dmg}{R} damage!')
            if defender.hp <= 0:
                self.msg(f'The {defender.name} is slain! (+{defender.exp} exp)', BYLW)
                self.monsters.remove(defender)
                self._gain_exp(defender.exp)
        else:
            self.msg(f'The {attacker.name} hits you for {fg(BRED)}{dmg}{R} damage!')
            if defender.hp <= 0:
                self.alive = False

    def _gain_exp(self, amt: int):
        self.p.exp += amt
        while self.p.exp >= self.p.exp_need:
            self.p.exp -= self.p.exp_need
            self.p.level += 1
            self.p.exp_need = int(self.p.exp_need * 1.6)
            self.p.max_hp += 10
            self.p.hp = min(self.p.max_hp, self.p.hp + 10)
            self.p.base_atk += 2
            self.p.base_dfn += 1
            self.msg(f'★ Level up! Now level {self.p.level}. HP/ATK/DEF increased.', BYLW)

    # ── Player actions ────────────────────────────────────────────────────────

    def _try_move(self, dx, dy) -> bool:
        nx, ny = self.p.x + dx, self.p.y + dy
        if not (0 <= nx < W and 0 <= ny < H): return False
        mon = next((m for m in self.monsters if m.x == nx and m.y == ny), None)
        if mon:
            self._do_attack(self.p, mon); return True
        if self.grid[ny][nx] == WALL: return False
        self.p.x, self.p.y = nx, ny
        if self.grid[ny][nx] == STAIR:
            self.msg('You see stairs leading down. Press > to descend.', CYN)
        self._refresh_fov()
        return True

    def _try_descend(self) -> bool:
        if self.grid[self.p.y][self.p.x] != STAIR:
            self.msg('No stairs here.'); return False
        nf = self.p.floor_num + 1
        if nf > 5:
            self.won = True; self.alive = False; return True
        self.load_floor(nf)
        return True

    def _try_grab(self) -> bool:
        itm = next((i for i in self.floor_items if i.x == self.p.x and i.y == self.p.y), None)
        if not itm:
            self.msg('Nothing to pick up here.'); return False
        if len(self.p.inventory) >= 10:
            self.msg('Your pack is full!', RED); return False
        self.floor_items.remove(itm)
        self.p.inventory.append(itm)
        self.msg(f'You pick up the {fg(itm.color)}{itm.name}{R}.')
        return True

    def _show_inventory(self):
        if not self.p.inventory:
            self.msg('You have no items.'); return
        out = []
        for i, it in enumerate(self.p.inventory):
            row = 3 + i
            out.append(f'\033[{row};5H\033[{BGBLK}m {fg(it.color)}{it.char}{R}\033[{BGBLK}m'
                       f' {i+1}. {it.name:<20} [{it.effect:>5}] {R}')
        out.append(f'\033[{3+len(self.p.inventory)};5H\033[{BGBLK}m'
                   f' Use which? (1-{len(self.p.inventory)}, ESC=cancel)       {R}')
        sys.stdout.write(''.join(out)); sys.stdout.flush()
        key = getch()
        self._dirty = True
        if key.isdigit():
            idx = int(key) - 1
            if 0 <= idx < len(self.p.inventory):
                self._apply_item(self.p.inventory.pop(idx))

    def _apply_item(self, it: Item):
        p = self.p
        if it.effect == 'heal':
            gained = min(it.power, p.max_hp - p.hp)
            p.hp += gained
            self.msg(f'You drink the {it.name} and recover {gained} HP.', BGRN)
        elif it.effect == 'atk+':
            p.bonus_atk += it.power
            self.msg(f'You equip the {it.name}. ATK +{it.power}!', BYLW)
        elif it.effect == 'def+':
            p.bonus_dfn += it.power
            self.msg(f'You equip the {it.name}. DEF +{it.power}!', BCYN)
        elif it.effect == 'blast':
            targets = [m for m in self.monsters if (m.x, m.y) in self.visible]
            if not targets:
                self.msg('The scroll flares but hits nothing.', MAG); return
            for m in targets:
                dmg = it.power + random.randint(-8, 8)
                m.hp -= dmg
                self.msg(f'Fire scorches the {m.name} for {dmg} damage!', BRED)
            self.monsters = [m for m in self.monsters if m.hp > 0]
            self.msg('The scroll crumbles to ash.', MAG)

    # ── Monster AI ────────────────────────────────────────────────────────────

    def _monsters_act(self):
        for m in list(self.monsters):
            if m.hp <= 0: continue
            dist = abs(m.x - self.p.x) + abs(m.y - self.p.y)
            if (m.x, m.y) in self.visible or dist <= 4:
                m.awake = True
            if not m.awake: continue
            m.tick += 1
            if m.speed > 1 and m.tick % m.speed != 0 and dist > 1: continue
            if dist == 1:
                self._do_attack(m, self.p)
            else:
                path = find_path(self.grid, self.monsters, m.x, m.y, self.p.x, self.p.y)
                if path:
                    nx, ny = path[0]
                    if not any(o.x == nx and o.y == ny for o in self.monsters if o is not m):
                        m.x, m.y = nx, ny

    # ── Input handling ────────────────────────────────────────────────────────

    MOVES = {
        'h': (-1,0), 'j': (0,1), 'k': (0,-1), 'l': (1,0),
        'y': (-1,-1), 'u': (1,-1), 'b': (-1,1), 'n': (1,1),
        '\x1b[A': (0,-1), '\x1b[B': (0,1), '\x1b[C': (1,0), '\x1b[D': (-1,0),
    }

    def _handle_key(self, key) -> bool:
        """Returns True if a turn was spent."""
        if key in ('q', 'Q'):
            self.alive = False; return False
        if key in self.MOVES:
            return self._try_move(*self.MOVES[key])
        if key == '>': return self._try_descend()
        if key == 'g': return self._try_grab()
        if key == 'i': self._show_inventory(); return True
        if key == '.': self.msg('You wait...'); return True
        if key == '?': self._show_help(); return False
        return False

    def _show_help(self):
        lines = [
            f'{fg(BCYN, bold=True)}╔══════════════════════════════════════════╗{R}',
            f'{fg(BCYN, bold=True)}║       THE DEPTHS — HELP                  ║{R}',
            f'{fg(BCYN, bold=True)}╠══════════════════════════════════════════╣{R}',
            f'{fg(BCYN)}║{R}  Movement:  hjkl or arrow keys           {fg(BCYN)}║{R}',
            f'{fg(BCYN)}║{R}  Diagonal:  y u b n                      {fg(BCYN)}║{R}',
            f'{fg(BCYN)}║{R}  Wait:      . (period)                   {fg(BCYN)}║{R}',
            f'{fg(BCYN)}║{R}  Pick up:   g                            {fg(BCYN)}║{R}',
            f'{fg(BCYN)}║{R}  Use item:  i (opens inventory)          {fg(BCYN)}║{R}',
            f'{fg(BCYN)}║{R}  Descend:   > (when on stairs {fg(BYLW)}>{R})        {fg(BCYN)}║{R}',
            f'{fg(BCYN)}║{R}  Quit:      q                            {fg(BCYN)}║{R}',
            f'{fg(BCYN, bold=True)}╠══════════════════════════════════════════╣{R}',
            f'{fg(BCYN)}║{R}  Goal: Survive all 5 floors!             {fg(BCYN)}║{R}',
            f'{fg(BCYN)}║{R}  Tip:  Fire Scrolls clear whole rooms.   {fg(BCYN)}║{R}',
            f'{fg(BCYN)}║{R}  Tip:  Slow monsters {fg(RED)}T{R}/{fg(RED)}D{R} still hit hard.  {fg(BCYN)}║{R}',
            f'{fg(BCYN, bold=True)}╚══════════════════════════════════════════╝{R}',
            '',
            '               Press any key to continue...',
        ]
        out = ['\033[2J\033[H']
        for i, line in enumerate(lines):
            out.append(f'\033[{4+i};8H{line}')
        sys.stdout.write(''.join(out)); sys.stdout.flush()
        getch()
        self._dirty = True

    # ── Screens ───────────────────────────────────────────────────────────────

    def _show_title(self):
        art = [
            r"  _____ _   _ _____   ____  _____ ____  _____ _   _ ____  ",
            r" |_   _| | | | ____| |  _ \| ____|  _ \|_   _| | | / ___| ",
            r"   | | | |_| |  _|   | | | |  _| | |_) | | | | |_| \___ \ ",
            r"   | | |  _  | |___  | |_| | |___| ___/  | | |  _  |___) |",
            r"   |_| |_| |_|_____| |____/|_____|_|     |_| |_| |_|____/ ",
        ]
        art_colors = [BRED, BRED, BYLW, BYLW, BGRN]
        subtitle = [
            '',
            f'           {fg(BWHT)}A Terminal Roguelike Adventure{R}',
            '',
            f'  {fg(BBLK)}Navigate procedurally generated dungeons. Fight monsters.{R}',
            f'  {fg(BBLK)}   Collect loot. Survive 5 floors. Become legend.{R}',
            '',
            f'                {fg(BBLK)}Press any key to begin...{R}',
        ]
        out = ['\033[2J\033[H']
        for i, (line, col) in enumerate(zip(art, art_colors)):
            out.append(f'\033[{3+i};1H{fg(col, bold=True)}{line}{R}')
        for i, line in enumerate(subtitle):
            out.append(f'\033[{3+len(art)+i};1H{line}')
        sys.stdout.write(''.join(out)); sys.stdout.flush()
        getch()

    def _show_death(self):
        lines = [
            f'{fg(BRED, bold=True)}',
            '  ╔══════════════════════════════╗',
            '  ║                              ║',
            '  ║       YOU HAVE DIED          ║',
            '  ║                              ║',
            '  ╚══════════════════════════════╝',
            f'{R}',
            f'  You reached floor {self.p.floor_num}.',
            f'  You were level {self.p.level}.',
            f'  You survived {self.turn} turns.',
            '',
            f'  {fg(BBLK)}Press any key to exit...{R}',
        ]
        out = ['\033[2J\033[H']
        for i, line in enumerate(lines):
            out.append(f'\033[{4+i};3H{line}')
        sys.stdout.write(''.join(out)); sys.stdout.flush()
        getch()

    def _show_victory(self):
        lines = [
            f'{fg(BYLW, bold=True)}',
            '  ╔════════════════════════════════════════╗',
            '  ║                                        ║',
            '  ║    YOU CONQUERED THE DEPTHS!           ║',
            '  ║                                        ║',
            '  ╚════════════════════════════════════════╝',
            f'{R}',
            f'  You cleared all 5 floors!',
            f'  Final level: {self.p.level}',
            f'  Total turns: {self.turn}',
            '',
            f'  {fg(BBLK)}Press any key to exit...{R}',
        ]
        out = ['\033[2J\033[H']
        for i, line in enumerate(lines):
            out.append(f'\033[{4+i};3H{line}')
        sys.stdout.write(''.join(out)); sys.stdout.flush()
        getch()

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        os.system('clear')
        self._show_title()
        hide_cursor()
        sys.stdout.write('\033[2J')
        try:
            self.load_floor(1)
            self.msg(f'{fg(BCYN)}Welcome to THE DEPTHS. Press ? for help.{R}')
            while self.alive:
                self._dirty = True
                self.render()
                key = getch()
                spent = self._handle_key(key)
                if spent and self.alive:
                    self._monsters_act()
                    self.turn += 1
        finally:
            show_cursor()
            sys.stdout.write('\033[0m\n')
            sys.stdout.flush()

        if self.won:
            self._show_victory()
        else:
            self._show_death()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if sys.platform == 'win32':
        print('Windows is not supported. Run on macOS or Linux.')
        sys.exit(1)

    def _sigint(sig, frame):
        show_cursor()
        sys.stdout.write('\033[0m\n')
        sys.exit(0)

    signal.signal(signal.SIGINT, _sigint)
    Game().run()
