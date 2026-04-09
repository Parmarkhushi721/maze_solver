"""
main.py - Application Controller
==================================
Entry point for the Pygame Maze Solver.

Responsibilities:
  - Pygame window initialization and main event loop (target 60 FPS).
  - Application state machine (IDLE → GENERATING → READY → SOLVING → DONE).
  - Keyboard and mouse input handling.
  - Orchestrating the generator and solver coroutines frame-by-frame.
  - Delegating all rendering to visualizer.draw_frame().

Controls:
  SPACE          → Generate a new random maze.
  D              → Solve with Dijkstra's Algorithm.
  B              → Solve with BFS.
  F              → Solve with DFS (depth-first).
  R              → Reset solver (keep current maze).
  Left Click     → First click sets Start; second click sets End.
  ESC / Window X → Quit.

Configuration:
  Adjust ROWS, COLS, and CELL_SIZE to resize the maze. The window size
  is computed automatically from these values plus the left panel width.
"""

from __future__ import annotations

import sys
import time
from enum import Enum, auto
from typing import Generator, List, Optional, Set, Tuple

import pygame

from algorithms import bfs, dijkstra, dfs
from maze import Cell, Maze
from generator import generate_maze
from visualizer import draw_frame

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROWS: int       = 21        # Number of maze rows     (odd numbers look best)
COLS: int       = 31        # Number of maze columns  (odd numbers look best)
CELL_SIZE: int  = 28        # Pixels per cell side
FPS: int        = 60

LEFT_PANEL_W: int = 220     # Width of the stats/legend side panel (pixels)
GRID_OFFSET_X: int = LEFT_PANEL_W + 10   # Maze top-left X
GRID_OFFSET_Y: int = 10                  # Maze top-left Y

WINDOW_W: int = GRID_OFFSET_X + COLS * CELL_SIZE + 10
WINDOW_H: int = max(GRID_OFFSET_Y + ROWS * CELL_SIZE + 10, 600)

WINDOW_TITLE = "Pygame Maze Solver — Dijkstra | BFS | DFS"

# How many generator/solver steps to advance per frame.
# Higher = faster animation; lower = slower, more detailed animation.
GEN_STEPS_PER_FRAME: int  = 3
SOLVE_STEPS_PER_FRAME: int = 2


# ---------------------------------------------------------------------------
# Application State
# ---------------------------------------------------------------------------

class AppState(Enum):
    IDLE       = auto()   # No maze generated yet.
    GENERATING = auto()   # Maze carving in progress.
    READY      = auto()   # Maze ready; awaiting solver command.
    SOLVING    = auto()   # Solver running.
    DONE       = auto()   # Solver finished.


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class App:
    """
    Main application class encapsulating state, event handling, and the loop.

    Attributes:
        maze          : The active Maze object.
        state         : Current AppState.
        start_cell    : User-selected start cell (defaults to top-left).
        end_cell      : User-selected end cell (defaults to bottom-right).
        click_phase   : 0 = next click sets start; 1 = next click sets end.
        gen_coroutine : Generator from generate_maze().
        gen_current   : The latest cell yielded by the generator.
        solve_coroutine: Generator from the active algorithm.
        explored      : Set of explored cells during solving.
        path          : Reconstructed path (filled on completion).
        algorithm_name: Display name of the active algorithm.
        elapsed_ms    : Total milliseconds spent in the solve step loop.
        solve_start_t : perf_counter timestamp when solving began.
        cells_explored: Count of explored cells.
    """

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        self.clock  = pygame.time.Clock()

        self.maze = Maze(rows=ROWS, cols=COLS, cell_size=CELL_SIZE)

        self.state: AppState = AppState.IDLE
        self.start_cell: Cell = self.maze.get_cell(0, 0)
        self.end_cell:   Cell = self.maze.get_cell(COLS - 1, ROWS - 1)
        self.click_phase: int = 0  # 0 → set start, 1 → set end

        self.gen_coroutine:   Optional[Generator]  = None
        self.gen_current:     Optional[Cell]        = None
        self.solve_coroutine: Optional[Generator]  = None

        self.explored:       Set[Cell]  = set()
        self.path:           List[Cell] = []
        self.algorithm_name: str        = "None"
        self.elapsed_ms:     float      = 0.0
        self.solve_start_t:  float      = 0.0
        self.cells_explored: int        = 0

    # ------------------------------------------------------------------
    # Public Entry Point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Main game loop — runs until the user closes the window."""
        while True:
            self._handle_events()
            self._update()
            self._render()
            self.clock.tick(FPS)

    # ------------------------------------------------------------------
    # Event Handling
    # ------------------------------------------------------------------

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()

            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)

    def _handle_keydown(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self._quit()

        elif key == pygame.K_SPACE:
            self._start_generation()

        elif key == pygame.K_r:
            self._reset_solver()

        elif key == pygame.K_d:
            self._start_solver("Dijkstra", dijkstra)

        elif key == pygame.K_b:
            self._start_solver("BFS", bfs)

        elif key == pygame.K_f:
            self._start_solver("DFS", dfs)

    def _handle_click(self, pos: Tuple[int, int]) -> None:
        """Maps a mouse click to a cell and updates start/end accordingly."""
        mx, my = pos
        gx = mx - GRID_OFFSET_X
        gy = my - GRID_OFFSET_Y

        if gx < 0 or gy < 0:
            return  # Click was outside the grid.

        col = gx // CELL_SIZE
        row = gy // CELL_SIZE

        clicked = self.maze.get_cell(col, row)
        if clicked is None:
            return

        if self.click_phase == 0:
            self.start_cell = clicked
            self.click_phase = 1
        else:
            if clicked != self.start_cell:
                self.end_cell = clicked
            self.click_phase = 0

        # Auto-reset solver visuals when markers change.
        if self.state in (AppState.SOLVING, AppState.DONE, AppState.READY):
            self._reset_solver()

    # ------------------------------------------------------------------
    # State Transitions
    # ------------------------------------------------------------------

    def _start_generation(self) -> None:
        """Resets everything and begins carving a new maze."""
        self.maze.reset_all()
        self.start_cell    = self.maze.get_cell(0, 0)
        self.end_cell      = self.maze.get_cell(COLS - 1, ROWS - 1)
        self.click_phase   = 0
        self._clear_solver_state()
        self.gen_coroutine = generate_maze(self.maze)
        self.gen_current   = None
        self.state         = AppState.GENERATING

    def _start_solver(self, name: str, algorithm_func) -> None:
        """
        Initializes and starts a pathfinding algorithm.

        Only allowed in READY or DONE states (maze must be generated first).
        """
        if self.state not in (AppState.READY, AppState.DONE):
            return  # Silently ignore if maze isn't ready.

        self._clear_solver_state()
        self.algorithm_name  = name
        self.solve_start_t   = time.perf_counter()
        self.elapsed_ms      = 0.0
        self.solve_coroutine = algorithm_func(self.maze, self.start_cell, self.end_cell)
        self.state           = AppState.SOLVING

    def _reset_solver(self) -> None:
        """Clears solver state and returns to READY (maze structure preserved)."""
        if self.state == AppState.IDLE:
            return
        self._clear_solver_state()
        self.state = AppState.READY if self.state != AppState.IDLE else AppState.IDLE

    def _clear_solver_state(self) -> None:
        """Internal helper: zeros out all solver-related data."""
        self.maze.reset_solver_state()
        self.solve_coroutine = None
        self.explored        = set()
        self.path            = []
        self.algorithm_name  = "None"
        self.elapsed_ms      = 0.0
        self.solve_start_t   = 0.0
        self.cells_explored  = 0

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def _update(self) -> None:
        """Advances the active coroutine by the configured steps per frame."""
        if self.state == AppState.GENERATING:
            self._step_generator()

        elif self.state == AppState.SOLVING:
            self._step_solver()

    def _step_generator(self) -> None:
        """Advances the maze generator coroutine."""
        for _ in range(GEN_STEPS_PER_FRAME):
            try:
                self.gen_current = next(self.gen_coroutine)
            except StopIteration:
                self.gen_current   = None
                self.gen_coroutine = None
                # Mark every cell as unvisited again (visitor flag was for generation).
                for cell in self.maze.grid:
                    cell.visited = False
                self.state = AppState.READY
                break

    def _step_solver(self) -> None:
        """Advances the active solving algorithm coroutine."""
        if self.solve_coroutine is None:
            return

        for _ in range(SOLVE_STEPS_PER_FRAME):
            try:
                explored, path, done = next(self.solve_coroutine)
                self.explored       = explored
                self.cells_explored = len(explored)
                self.elapsed_ms     = (time.perf_counter() - self.solve_start_t) * 1000

                if done:
                    self.path  = path
                    self.state = AppState.DONE
                    self.solve_coroutine = None
                    break
            except StopIteration:
                self.state = AppState.DONE
                self.solve_coroutine = None
                break

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render(self) -> None:
        draw_frame(
            self.screen,
            self.maze,
            start_cell=self.start_cell,
            end_cell=self.end_cell,
            offset_x=GRID_OFFSET_X,
            offset_y=GRID_OFFSET_Y,
            generation_current=self.gen_current,
            algorithm_name=self.algorithm_name,
            elapsed_ms=self.elapsed_ms,
            cells_explored=self.cells_explored,
            path_length=len(self.path),
            is_generating=(self.state == AppState.GENERATING),
            is_solving=(self.state == AppState.SOLVING),
            is_done=(self.state == AppState.DONE),
            panel_x=10,
            hud_y=10,
            legend_y=200,
            color_legend_y=430,
            panel_w=LEFT_PANEL_W,
        )
        pygame.display.flip()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    @staticmethod
    def _quit() -> None:
        pygame.quit()
        sys.exit(0)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = App()
    app.run()
