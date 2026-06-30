
import pygame
from pathlib import Path

# Game Constants
SCREEN_W, SCREEN_H = 1024, 576
FPS = 60
GAME_TITLE = "CR7 Algorithm Quest"

# Asset Directory
ASSETS_DIR = Path(__file__).parent / "assets"

# Colors
COL_DARK_BG = (20, 20, 30)
COL_GOLD = (255, 215, 0)
COL_GOLD_BRIGHT = (255, 240, 100)
COL_CREAM_TEXT = (230, 220, 200)
COL_DANGER = (255, 100, 100)
COL_DANGER_BG = (100, 20, 20)
COL_DANGER_RED = (200, 80, 80)
COL_FIRE = (255, 140, 0)
COL_VISITED = (150, 150, 150)
COL_FRONTIER = (255, 255, 100)
COL_WALL = (50, 50, 50)
COL_WALL_STONE = (60, 60, 60)
COL_GRASS = (50, 100, 50)
COL_GRASS_LIGHT = (100, 150, 80)
COL_GRASS_DARK = (40, 80, 40)
COL_PATH = (100, 120, 80)
COL_PATH_GREY = (120, 120, 100)
COL_SILVER = (200, 200, 210)
COL_PATH_FINAL = (200, 200, 150)
COL_BUTTON_BG = (100, 70, 20)
COL_BUTTON_TEXT = (230, 220, 200)
COL_BUTTON_HOVER = (150, 100, 30)
COL_PANEL_BG = (60, 50, 40)
COL_WOOD_PANEL = (101, 67, 33)
COL_WOOD_LIGHT = (150, 100, 50)
COL_WOOD_MED = (100, 70, 30)
COL_WOOD_DARK = (70, 50, 20)
COL_BLACK = (0, 0, 0)
COL_WHITE = (255, 255, 255)
COL_FOG = (20, 20, 30)

# Game States
STATE_INTRO = "INTRO"
STATE_LEVEL_SELECT = "LEVEL_SELECT"
STATE_GAMEPLAY = "GAMEPLAY"
STATE_LEVELUP = "LEVELUP"
STATE_GAMEOVER = "GAMEOVER"
STATE_VICTORY = "VICTORY"

# Algorithm Names
ALGO_BFS = "BFS"
ALGO_DFS = "DFS"
ALGO_IDS = "IDS"
ALGO_UCS = "UCS"
ALGO_GREEDY = "Greedy"
ALGO_ASTAR = "A*"
ALGO_HILLCLIMB = "Hill Climbing"

# UI Constants
GRID_CELL_SIZE = 64
TYPEWRITER_CPS = 40  # characters per second

# UI Rectangles (pygame.Rect format: (x, y, width, height))
DIALOG_PANEL_RECT = pygame.Rect(30, 400, 964, 150)
PORTRAIT_RECT = pygame.Rect(40, 410, 100, 140)
TEXT_AREA_RECT = pygame.Rect(150, 410, 820, 130)
SKIP_BUTTON_RECT = pygame.Rect(900, 420, 80, 30)
CURRENCY_ICON_RECT = pygame.Rect(50, 30, 24, 24)
LOGO_RECT = pygame.Rect(450, 80, 124, 60)

GRID_ORIGIN = (40, 80)
GRID_RECT = pygame.Rect(40, 80, 640, 400)
SIDE_PANEL_RECT = pygame.Rect(700, 80, 300, 300)

HEADER_TITLE_RECT = pygame.Rect(300, 30, 424, 40)
LEVEL_BADGE_ICON_RECT = pygame.Rect(740, 30, 40, 40)
THUMBNAIL_MAP_RECT = pygame.Rect(700, 100, 120, 100)

CHIBI_PLAYER_RECT = pygame.Rect(360, 200, 304, 304)
CUTSCENE_TITLE_BANNER_RECT = pygame.Rect(150, 50, 724, 80)
LEVEL_STATUS_BADGE_RECT = pygame.Rect(750, 320, 200, 120)
HEURISTIC_GRAPH_BOX_RECT = pygame.Rect(700, 450, 300, 110)

OUTER_FRAME_RECT = pygame.Rect(0, 0, SCREEN_W, SCREEN_H)
OUTER_FRAME_BORDER = 8

# Level Configuration
LEVEL_NAMES = {
    0: "Tim Kiem Mu",
    1: "Tim Kiem Co Thong Tin",
    2: "Leo Nui",
    3: "Tim Kiem Vo Ben"
}

LEVEL_ALGORITHMS = [
    [ALGO_BFS, ALGO_DFS, ALGO_IDS],  # Level 0: Blind Search variants
    [ALGO_UCS, ALGO_GREEDY, ALGO_ASTAR],  # Level 1: Informed Search variants
    ["Hill Climbing", "Steepest Ascent HC", "Stochastic HC"],  # Level 2: Hill Climbing variants
    [ALGO_BFS, ALGO_DFS, ALGO_UCS, ALGO_GREEDY, ALGO_ASTAR, "Hill Climbing"],  # Level 3: uncertainty demo
]
LEVEL_GRID_SIZE = [(9, 5), (9, 5), (12, 7), (12, 7)]
LEVEL_TITLES = {
    0: "LEVEL 1: TIM KIEM MU",
    1: "LEVEL 2: TIM KIEM THONG TIN",
    2: "LEVEL 3: LEO NUI",
    3: "LEVEL 4: TIM KIEM VO BEN"
}

# Kits (Soccer Uniforms) - CR7 inspired
KITS = {
    0: {"name": "Kit1", "label": "Red", "color": (255, 0, 0)},
    1: {"name": "Kit2", "label": "Blue", "color": (0, 0, 255)},
    2: {"name": "Kit3", "label": "Yellow", "color": (255, 255, 0)},
    3: {"name": "Kit4", "label": "Green", "color": (0, 255, 0)},
}

# Story Text
PLAYER_TAG = "CR7"
INTRO_LINE = "Xin chao! Toi la CR7. Hay giup toi tim duong di den cup vo dich bang cach su dung cac thuat toan tim kiem!"

LEVEL_INTRO_LINES = {
    0: "Level 1: Dung tim kiem mu de tim duong di den cup. Khong co ban do!",
    1: "Level 2: Bay gio ban co ban do. Hay dung tim kiem co thong tin!",
    2: "Level 3: Hay tim duong di xuong nui. Chi xuat phat tu vi tri cao nhat!",
    3: "Level 4: Co 2 nhom bai toan. Nhom khong quan sat chi co ? va G/CR7; nhom mot phan quan sat co ca so va ?. Bam BELIEF de mo tat ca thanh so."
}

LEVELUP_LINES = {
    0: "Tuyet voi! Ban da hoan thanh level 1!",
    1: "Day la! Len level 2 voi kit moi!",
    2: "Tam biet co dau. Hay tien len level 3!",
}

VICTORY_LINE = "Tuyet voi! Ban da hoai thanh toan bo tro choi. Ban la nguoi thang!"

GAMEOVER_LINE_STUCK = "Khong the tien tiep... thu thuat toan khac!"

# Cell Cost Mapping
CELL_COST = {
    "grass": 1,
    "path": 1,
    "danger": 2,
    "fire": 5,
    "wall": 999,
    "start": 1,
    "trophy": 1,
}
