"""
generator.py - Maze Generation Engine
======================================
Implements the Recursive Backtracking (Randomized DFS) algorithm to carve
a perfect maze (a spanning tree of the grid graph):
  - No loops.
  - Fully connected: every cell is reachable from every other cell.
  - Exactly one path exists between any two cells.

Algorithm Complexity:
  Time:  O(N) — each cell is visited exactly once.
  Space: O(N) — the call stack (or explicit stack) can grow up to N deep,
                where N = rows * cols.
"""

from __future__ import annotations
import random
from typing import Generator, List, Optional, Tuple

from maze import Cell, Maze


def generate_maze(maze: Maze, start_x: int = 0, start_y: int = 0) -> Generator[Cell, None, None]:
    """
    Carves passages through `maze` using iterative Recursive Backtracking.

    Uses an explicit stack instead of recursion to avoid Python's default
    recursion limit (~1000), which would be exceeded for large mazes.

    The generator *yields* the current cell at each step so the visualizer
    can animate the carving process in real time.

    Algorithm Steps:
      1. Pick a starting cell; mark it visited; push it onto the stack.
      2. While the stack is not empty:
           a. Peek at the top cell.
           b. Collect all unvisited neighbors.
           c. If unvisited neighbors exist:
                - Pick one at random.
                - Remove the wall between current and chosen neighbor.
                - Mark the neighbor visited; push it.
           d. Else: backtrack (pop the stack).

    Args:
        maze (Maze): A freshly initialized (all walls intact) Maze object.
        start_x (int): Column index of the starting cell.
        start_y (int): Row index of the starting cell.

    Yields:
        Cell: The currently active cell at each generation step.
    """
    # Full reset ensures a clean slate regardless of prior state.
    maze.reset_all()

    start: Cell = maze.get_cell(start_x, start_y)
    start.visited = True

    stack: List[Cell] = [start]

    while stack:
        current: Cell = stack[-1]
        yield current  # Let the visualizer draw the current state.

        # Gather unvisited neighbors (candidates for the next passage).
        unvisited_neighbors: List[Tuple[Cell, str]] = [
            (neighbor, direction)
            for neighbor, direction in maze.get_neighbors(current)
            if not neighbor.visited
        ]

        if unvisited_neighbors:
            # Randomly choose a neighbor to maintain maze unpredictability.
            chosen_neighbor, direction = random.choice(unvisited_neighbors)

            # Carve the passage by removing the shared wall.
            maze.remove_wall(current, direction)

            chosen_neighbor.visited = True
            stack.append(chosen_neighbor)
        else:
            # Dead end reached — backtrack.
            stack.pop()
