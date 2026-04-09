"""
maze.py - Core Data Structures
==============================
Defines the fundamental building blocks of the maze:
  - Cell: Represents a single node in the grid graph.
  - Maze: Manages the 2D grid, neighbor lookups, and wall removal.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Cell:
    """
    Represents a single cell (node) in the maze grid.

    The wall configuration uses a dictionary keyed by cardinal direction
    ('N', 'S', 'E', 'W') for O(1) wall lookup and removal.

    Attributes:
        x (int): Column index (0-based).
        y (int): Row index (0-based).
        walls (dict): Active walls. True = wall exists.
        visited (bool): Whether the generator has visited this cell.
        in_path (bool): Whether this cell is part of the solved path.
        explored (bool): Whether a solver algorithm has explored this cell.
        distance (float): Used by Dijkstra; shortest known distance from start.
        parent (Optional[Cell]): Back-pointer used to reconstruct the path.
    """
    x: int
    y: int
    walls: dict = field(default_factory=lambda: {'N': True, 'S': True, 'E': True, 'W': True})
    visited: bool = False
    in_path: bool = False
    explored: bool = False
    distance: float = float('inf')
    parent: Optional['Cell'] = field(default=None, repr=False, compare=False)

    def reset_solver_state(self) -> None:
        """Clears all solver-related state, keeping structural (wall) data intact."""
        self.in_path = False
        self.explored = False
        self.distance = float('inf')
        self.parent = None

    def reset_all(self) -> None:
        """Full reset: clears both generator and solver state."""
        self.walls = {'N': True, 'S': True, 'E': True, 'W': True}
        self.visited = False
        self.reset_solver_state()

    def __hash__(self):
        return hash((self.x, self.y))

    def __eq__(self, other):
        if isinstance(other, Cell):
            return self.x == other.x and self.y == other.y
        return NotImplemented

    def __lt__(self, other):
        """Enables comparison in heapq (priority queue) by distance."""
        return self.distance < other.distance


class Maze:
    """
    Manages the 2D grid of Cell objects and provides graph-traversal helpers.

    The grid is stored as a flat list for cache locality, indexed by
    (y * cols + x). Neighbor and wall removal operations are O(1).

    Attributes:
        rows (int): Number of rows in the grid.
        cols (int): Number of columns in the grid.
        cell_size (int): Pixel size of each cell (used by visualizer).
        grid (List[Cell]): Flat list of all Cell instances.
    """

    # Maps each direction to (dx, dy) and its opposite direction key.
    DIRECTION_MAP = {
        'N': (0, -1, 'S'),
        'S': (0,  1, 'N'),
        'E': (1,  0, 'W'),
        'W': (-1, 0, 'E'),
    }

    def __init__(self, rows: int, cols: int, cell_size: int = 30) -> None:
        self.rows = rows
        self.cols = cols
        self.cell_size = cell_size
        self.grid: List[Cell] = [
            Cell(x=col, y=row)
            for row in range(rows)
            for col in range(cols)
        ]

    # ------------------------------------------------------------------
    # Grid Access
    # ------------------------------------------------------------------

    def get_cell(self, x: int, y: int) -> Optional[Cell]:
        """Returns the Cell at (x, y), or None if out of bounds. O(1)."""
        if 0 <= x < self.cols and 0 <= y < self.rows:
            return self.grid[y * self.cols + x]
        return None

    def get_neighbors(self, cell: Cell) -> List[Tuple[Cell, str]]:
        """
        Returns all valid (in-bounds) neighbors with their direction from `cell`.

        Returns:
            List of (neighbor_cell, direction_string) tuples.
        """
        neighbors = []
        for direction, (dx, dy, _) in self.DIRECTION_MAP.items():
            neighbor = self.get_cell(cell.x + dx, cell.y + dy)
            if neighbor is not None:
                neighbors.append((neighbor, direction))
        return neighbors

    def get_accessible_neighbors(self, cell: Cell) -> List[Cell]:
        """
        Returns neighbors reachable from `cell` (i.e., no wall between them).
        Used exclusively by pathfinding algorithms. O(4) = O(1).
        """
        accessible = []
        for direction, (dx, dy, _) in self.DIRECTION_MAP.items():
            if not cell.walls[direction]:
                neighbor = self.get_cell(cell.x + dx, cell.y + dy)
                if neighbor is not None:
                    accessible.append(neighbor)
        return accessible

    # ------------------------------------------------------------------
    # Wall Operations
    # ------------------------------------------------------------------

    def remove_wall(self, cell_a: Cell, direction: str) -> None:
        """
        Removes the wall between cell_a and its neighbor in `direction`.
        Updates both cells to maintain bidirectional consistency. O(1).
        """
        dx, dy, opposite = self.DIRECTION_MAP[direction]
        cell_b = self.get_cell(cell_a.x + dx, cell_a.y + dy)
        if cell_b is not None:
            cell_a.walls[direction] = False
            cell_b.walls[opposite] = False

    # ------------------------------------------------------------------
    # State Management
    # ------------------------------------------------------------------

    def reset_solver_state(self) -> None:
        """Resets all solver-related attributes across every cell. O(N)."""
        for cell in self.grid:
            cell.reset_solver_state()

    def reset_all(self) -> None:
        """Full maze reset: restores all walls and clears all state. O(N)."""
        for cell in self.grid:
            cell.reset_all()

    @property
    def start_cell(self) -> Cell:
        """Convenience: top-left corner as the default start."""
        return self.get_cell(0, 0)

    @property
    def end_cell(self) -> Cell:
        """Convenience: bottom-right corner as the default end."""
        return self.get_cell(self.cols - 1, self.rows - 1)
