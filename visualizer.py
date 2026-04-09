"""
visualizer.py - Pygame Rendering Engine
=========================================
Handles all drawing operations for the maze solver application:
  - Rendering the grid (cells, walls, start/end markers).
  - Animating the algorithm exploration (visited cells) and shortest path.
  - Drawing a real-time HUD (heads-up display) with statistics.
  - Rendering an interactive control panel legend.

Design:
  All colors are defined as module-level constants for easy theming.
  Each draw_* function is a pure function operating on a pygame Surface,
  keeping rendering logic decoupled from application state.
"""

from __future__ import annotations
import pygame
from typing import List, Optional, Set, Tuple

from maze import Cell, Maze


# ---------------------------------------------------------------------------
# Color Palette (Dark Theme)
# ---------------------------------------------------------------------------
COLOR_BG             = (10,  12,  20)   # Near-black background (wall fill base)
COLOR_CELL_DEFAULT   = (58,  74, 122)   # Open corridor — clearly lighter steel-blue
COLOR_WALL           = (255, 255, 255)  # Pure white walls — maximum contrast
COLOR_EXPLORED       = (50,  160, 220)  # Explored cells — bright cyan-blue
COLOR_PATH           = (255, 210,  40)  # Shortest path — golden yellow
COLOR_START          = (50,  225, 110)  # Start marker — vivid green
COLOR_END            = (240,  65,  65)  # End marker — vivid red
COLOR_GENERATION     = (170,  80, 230)  # Generator frontier — bright purple
COLOR_GRID_LINE      = (30,  36,  58)   # Subtle grid lines between cells
COLOR_HUD_BG         = (20,  22,  35, 210)  # Semi-transparent HUD panel
COLOR_HUD_TEXT       = (210, 220, 255)  # HUD primary text
COLOR_HUD_HIGHLIGHT  = (255, 200,  40)  # HUD value highlight
COLOR_LEGEND_BG      = (22,  26,  42, 200)  # Legend panel background
COLOR_PANEL_BORDER   = (70,  80, 130)   # Panel border accent


# ---------------------------------------------------------------------------
# Font Cache (initialized lazily after pygame.init())
# ---------------------------------------------------------------------------
_fonts: dict = {}

def _get_font(size: int, bold: bool = False) -> pygame.font.Font:
    """Returns a cached pygame font object for the given size."""
    key = (size, bold)
    if key not in _fonts:
        try:
            # Prefer a clean system font; fallback to pygame default.
            _fonts[key] = pygame.font.SysFont("Segoe UI", size, bold=bold)
        except Exception:
            _fonts[key] = pygame.font.Font(None, size)
    return _fonts[key]


# ---------------------------------------------------------------------------
# Cell & Grid Drawing
# ---------------------------------------------------------------------------

def draw_cell(
    surface: pygame.Surface,
    cell: Cell,
    cell_size: int,
    offset_x: int = 0,
    offset_y: int = 0,
    *,
    generation_current: bool = False,
) -> None:
    """
    Draws a single cell with its fill color and walls onto `surface`.

    Fill priority (highest wins):
      in_path > explored > generation_current > default

    Args:
        surface           : Target pygame Surface.
        cell              : The Cell to render.
        cell_size         : Pixel dimension of each cell.
        offset_x/offset_y : Pixel offset for the top-left of the maze grid.
        generation_current: If True, paint this cell as the active generator cell.
    """
    px = offset_x + cell.x * cell_size
    py = offset_y + cell.y * cell_size

    # --- Fill ---
    # The entire cell square starts as the wall color (background = wall mass).
    # We then paint the inner corridor region with the passage color,
    # and mask open sides by extending the corridor color to the cell edge.
    # This gives thick, solid, gapless walls with a bright open-path interior.
    W = 3  # Wall thickness in pixels

    if cell.in_path:
        color = COLOR_PATH
    elif cell.explored:
        color = COLOR_EXPLORED
    elif generation_current:
        color = COLOR_GENERATION
    else:
        color = COLOR_CELL_DEFAULT

    # Paint the whole cell as wall first (solid dark base).
    pygame.draw.rect(surface, COLOR_BG, (px, py, cell_size, cell_size))

    # Inner corridor rectangle (inset by W on all walled sides).
    left_inset   = W if cell.walls['W'] else 0
    top_inset    = W if cell.walls['N'] else 0
    right_inset  = W if cell.walls['E'] else 0
    bottom_inset = W if cell.walls['S'] else 0

    inner_x = px + left_inset
    inner_y = py + top_inset
    inner_w = cell_size - left_inset - right_inset
    inner_h = cell_size - top_inset  - bottom_inset

    if inner_w > 0 and inner_h > 0:
        pygame.draw.rect(surface, color, (inner_x, inner_y, inner_w, inner_h))

    # Draw explicit wall lines on closed sides (bright white, W px thick).
    # This ensures walls are always crisp and fully opaque.
    right  = px + cell_size
    bottom = py + cell_size

    if cell.walls['N']:
        pygame.draw.rect(surface, COLOR_WALL, (px, py, cell_size, W))
    if cell.walls['S']:
        pygame.draw.rect(surface, COLOR_WALL, (px, bottom - W, cell_size, W))
    if cell.walls['W']:
        pygame.draw.rect(surface, COLOR_WALL, (px, py, W, cell_size))
    if cell.walls['E']:
        pygame.draw.rect(surface, COLOR_WALL, (right - W, py, W, cell_size))


def draw_maze(
    surface: pygame.Surface,
    maze: Maze,
    offset_x: int = 0,
    offset_y: int = 0,
    generation_current: Optional[Cell] = None,
) -> None:
    """
    Draws the entire maze grid — all cells and their walls.

    Args:
        surface            : Target pygame Surface.
        maze               : The Maze object to render.
        offset_x/offset_y  : Pixel offset of the grid's top-left corner.
        generation_current : If set, this cell is highlighted as the active carver.
    """
    for cell in maze.grid:
        draw_cell(
            surface, cell, maze.cell_size, offset_x, offset_y,
            generation_current=(cell is generation_current),
        )


def draw_marker(
    surface: pygame.Surface,
    cell: Cell,
    cell_size: int,
    color: Tuple[int, int, int],
    offset_x: int = 0,
    offset_y: int = 0,
    label: str = "",
) -> None:
    """
    Draws a filled circle marker (start or end) centered on `cell`.

    Args:
        surface   : Target pygame Surface.
        cell      : The cell to mark.
        cell_size : Pixel size of each cell.
        color     : RGB color of the marker.
        offset_x/y: Grid pixel offset.
        label     : Single-character label drawn inside the circle.
    """
    cx = offset_x + cell.x * cell_size + cell_size // 2
    cy = offset_y + cell.y * cell_size + cell_size // 2
    radius = max(cell_size // 2 - 4, 4)

    pygame.draw.circle(surface, color, (cx, cy), radius)
    pygame.draw.circle(surface, (255, 255, 255), (cx, cy), radius, 2)  # White border

    if label:
        font = _get_font(max(cell_size - 10, 10), bold=True)
        text_surf = font.render(label, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(cx, cy))
        surface.blit(text_surf, text_rect)


# ---------------------------------------------------------------------------
# HUD (Statistics Panel)
# ---------------------------------------------------------------------------

def draw_hud(
    surface: pygame.Surface,
    *,
    algorithm_name: str,
    elapsed_ms: float,
    cells_explored: int,
    path_length: int,
    maze_size: Tuple[int, int],
    is_generating: bool,
    is_solving: bool,
    is_done: bool,
    panel_x: int,
    panel_y: int,
    panel_w: int,
    panel_h: int,
) -> None:
    """
    Renders a translucent HUD panel with live statistics.

    Args:
        surface        : Target pygame Surface.
        algorithm_name : Name of the active algorithm (or 'None').
        elapsed_ms     : Time elapsed in milliseconds.
        cells_explored : Number of cells marked as explored.
        path_length    : Length of the found path (0 if not found yet).
        maze_size      : (rows, cols) tuple.
        is_generating  : Whether generation is in progress.
        is_solving     : Whether solving is in progress.
        is_done        : Whether solving has completed.
        panel_x/y/w/h  : Position and dimensions of the HUD panel.
    """
    # Semi-transparent background
    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel_surf.fill(COLOR_HUD_BG)
    surface.blit(panel_surf, (panel_x, panel_y))
    pygame.draw.rect(surface, COLOR_PANEL_BORDER, (panel_x, panel_y, panel_w, panel_h), 1, border_radius=6)

    font_title = _get_font(15, bold=True)
    font_label = _get_font(13)
    font_value = _get_font(13, bold=True)

    margin = 10
    line_h = 22
    y = panel_y + margin

    # Title
    status = "Generating..." if is_generating else ("Solving..." if is_solving else ("Done!" if is_done else "Ready"))
    title_surf = font_title.render("MAZE SOLVER", True, COLOR_HUD_HIGHLIGHT)
    surface.blit(title_surf, (panel_x + margin, y)); y += line_h + 4

    # separator
    pygame.draw.line(surface, COLOR_PANEL_BORDER,
                     (panel_x + margin, y), (panel_x + panel_w - margin, y), 1)
    y += 8

    rows_str  = f"{maze_size[0]} × {maze_size[1]}"
    elapsed_str = f"{elapsed_ms / 1000:.3f}s" if elapsed_ms > 0 else "—"
    explored_str = str(cells_explored) if cells_explored > 0 else "—"
    path_str = str(path_length) if path_length > 0 else "—"

    stats = [
        ("Status",    status),
        ("Algorithm", algorithm_name),
        ("Grid Size", rows_str),
        ("Time",      elapsed_str),
        ("Explored",  explored_str),
        ("Path Len",  path_str),
    ]

    for label, value in stats:
        lbl_surf = font_label.render(f"{label}:", True, COLOR_HUD_TEXT)
        val_surf = font_value.render(value, True, COLOR_HUD_HIGHLIGHT)
        surface.blit(lbl_surf, (panel_x + margin, y))
        surface.blit(val_surf, (panel_x + panel_w - margin - val_surf.get_width(), y))
        y += line_h


# ---------------------------------------------------------------------------
# Legend / Controls Panel
# ---------------------------------------------------------------------------

CONTROLS = [
    ("SPACE",   "Generate New Maze"),
    ("D",       "Dijkstra's Algorithm"),
    ("B",       "BFS (Breadth-First)"),
    ("F",       "DFS (Depth-First)"),
    ("R",       "Reset Solver"),
    ("Click",   "Set Start / End"),
    ("ESC",     "Quit"),
]

def draw_legend(
    surface: pygame.Surface,
    panel_x: int,
    panel_y: int,
    panel_w: int,
) -> None:
    """
    Renders a translucent controls/legend panel.

    Args:
        surface         : Target pygame Surface.
        panel_x/y/w    : Position and width; height is computed automatically.
    """
    font_title = _get_font(14, bold=True)
    font_key   = _get_font(12, bold=True)
    font_desc  = _get_font(12)

    margin = 10
    line_h = 20
    panel_h = margin * 2 + line_h + 6 + len(CONTROLS) * line_h + 4

    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel_surf.fill(COLOR_LEGEND_BG)
    surface.blit(panel_surf, (panel_x, panel_y))
    pygame.draw.rect(surface, COLOR_PANEL_BORDER, (panel_x, panel_y, panel_w, panel_h), 1, border_radius=6)

    y = panel_y + margin
    title = font_title.render("CONTROLS", True, COLOR_HUD_HIGHLIGHT)
    surface.blit(title, (panel_x + margin, y)); y += line_h + 2
    pygame.draw.line(surface, COLOR_PANEL_BORDER,
                     (panel_x + margin, y), (panel_x + panel_w - margin, y), 1)
    y += 6

    for key, desc in CONTROLS:
        key_surf  = font_key.render(f"[{key}]", True, (160, 200, 255))
        desc_surf = font_desc.render(desc, True, COLOR_HUD_TEXT)
        surface.blit(key_surf,  (panel_x + margin, y))
        surface.blit(desc_surf, (panel_x + margin + 58, y))
        y += line_h


# ---------------------------------------------------------------------------
# Color Legend (cell type swatches)
# ---------------------------------------------------------------------------

COLOR_SWATCHES = [
    (COLOR_START,      "Start"),
    (COLOR_END,        "End"),
    (COLOR_EXPLORED,   "Explored"),
    (COLOR_PATH,       "Path"),
    (COLOR_GENERATION, "Generating"),
]

def draw_color_legend(
    surface: pygame.Surface,
    panel_x: int,
    panel_y: int,
    panel_w: int,
) -> None:
    """Renders small colored swatches explaining cell colors."""
    font = _get_font(12)
    margin = 10
    swatch_size = 12
    line_h = 20
    panel_h = margin * 2 + len(COLOR_SWATCHES) * line_h

    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel_surf.fill(COLOR_LEGEND_BG)
    surface.blit(panel_surf, (panel_x, panel_y))
    pygame.draw.rect(surface, COLOR_PANEL_BORDER, (panel_x, panel_y, panel_w, panel_h), 1, border_radius=6)

    y = panel_y + margin
    for color, label in COLOR_SWATCHES:
        pygame.draw.rect(surface, color,
                         (panel_x + margin, y + (line_h - swatch_size) // 2,
                          swatch_size, swatch_size), border_radius=3)
        text = font.render(label, True, COLOR_HUD_TEXT)
        surface.blit(text, (panel_x + margin + swatch_size + 8, y))
        y += line_h


# ---------------------------------------------------------------------------
# Full Frame Composer
# ---------------------------------------------------------------------------

def draw_frame(
    surface: pygame.Surface,
    maze: Maze,
    *,
    start_cell: Cell,
    end_cell: Cell,
    offset_x: int,
    offset_y: int,
    generation_current: Optional[Cell] = None,
    algorithm_name: str = "None",
    elapsed_ms: float = 0.0,
    cells_explored: int = 0,
    path_length: int = 0,
    is_generating: bool = False,
    is_solving: bool = False,
    is_done: bool = False,
    panel_x: int = 10,
    hud_y: int = 10,
    legend_y: int = 200,
    color_legend_y: int = 430,
    panel_w: int = 200,
) -> None:
    """
    Composes a complete frame: background → maze → markers → HUD → legend.

    This single call is all main.py needs to render one frame.
    """
    surface.fill(COLOR_BG)

    draw_maze(surface, maze, offset_x, offset_y, generation_current)
    draw_marker(surface, start_cell, maze.cell_size, COLOR_START, offset_x, offset_y, "S")
    draw_marker(surface, end_cell,   maze.cell_size, COLOR_END,   offset_x, offset_y, "E")

    draw_hud(
        surface,
        algorithm_name=algorithm_name,
        elapsed_ms=elapsed_ms,
        cells_explored=cells_explored,
        path_length=path_length,
        maze_size=(maze.rows, maze.cols),
        is_generating=is_generating,
        is_solving=is_solving,
        is_done=is_done,
        panel_x=panel_x,
        panel_y=hud_y,
        panel_w=panel_w,
        panel_h=175,
    )

    draw_legend(surface, panel_x, legend_y, panel_w)
    draw_color_legend(surface, panel_x, color_legend_y, panel_w)
