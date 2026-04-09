"""
algorithms.py - Pathfinding Engines
=====================================
Implements three classic graph search algorithms as Python generators.
Each algorithm yields its state after every meaningful step, allowing the
visualizer to animate the exploration process frame by frame.

Every algorithm shares the same contract:
  - Accepts: maze (Maze), start (Cell), end (Cell)
  - Yields:  (explored_set, path_list, done_flag)
       explored_set  -> set of Cells explored so far (for live rendering)
       path_list     -> reconstructed path once `done` is True, else []
       done_flag     -> True only on the final yield (path found or exhausted)
  - When done, path_list contains the optimal (or found) path from start→end.

All algorithms operate exclusively on the maze graph via
`maze.get_accessible_neighbors()`, respecting carved passages only.
"""

from __future__ import annotations
import heapq
from collections import deque
from typing import Generator, List, Optional, Set, Tuple

from maze import Cell, Maze


# ---------------------------------------------------------------------------
# Shared Utility
# ---------------------------------------------------------------------------

def _reconstruct_path(end: Cell) -> List[Cell]:
    """
    Walks the parent back-pointer chain from `end` to the start.

    Time:  O(P) where P = path length.
    Space: O(P)

    Returns:
        List[Cell] ordered from start → end.
    """
    path: List[Cell] = []
    current: Optional[Cell] = end
    while current is not None:
        path.append(current)
        current = current.parent
    path.reverse()
    return path


# ---------------------------------------------------------------------------
# Dijkstra's Algorithm
# ---------------------------------------------------------------------------

def dijkstra(
    maze: Maze,
    start: Cell,
    end: Cell,
) -> Generator[Tuple[Set[Cell], List[Cell], bool], None, None]:
    """
    Dijkstra's Single-Source Shortest Path algorithm.

    Because all edge weights in a carved maze are uniform (each passage has
    cost 1), Dijkstra degenerates to a BFS. However, the full priority-queue
    implementation is retained here for generality and educational clarity.

    Data Structures:
      - Min-heap (priority queue) via `heapq`: O(log N) push/pop.
      - Visited set for O(1) membership testing.

    Time Complexity:
      O((V + E) log V) — V = number of cells, E = number of open passages.
      In a perfect maze: E = V - 1, so effectively O(V log V).

    Space Complexity:
      O(V) — for the priority queue, visited set, and parent pointers.

    Args:
        maze  (Maze): The maze containing the graph structure.
        start (Cell): Source node.
        end   (Cell): Target node.

    Yields:
        Tuple[Set[Cell], List[Cell], bool]:
          - Set of explored cells so far.
          - Reconstructed path (only non-empty when done=True and path found).
          - Boolean indicating whether the search has concluded.
    """
    maze.reset_solver_state()

    start.distance = 0.0
    explored: Set[Cell] = set()

    # Heap entries: (distance, tie-breaking counter, cell)
    # The counter prevents Python from comparing Cell objects directly
    # when distances are equal, avoiding TypeError since Cell.__lt__
    # is defined but a counter is cleaner and avoids ambiguity.
    counter = 0
    heap: List[Tuple[float, int, Cell]] = [(0.0, counter, start)]

    while heap:
        dist, _, current = heapq.heappop(heap)

        # Skip stale entries (cell already settled with a shorter distance).
        if current in explored:
            continue

        explored.add(current)
        current.explored = True

        if current == end:
            path = _reconstruct_path(end)
            for cell in path:
                cell.in_path = True
            yield explored, path, True
            return  # Search complete.

        for neighbor in maze.get_accessible_neighbors(current):
            if neighbor in explored:
                continue

            # Edge weight = 1 for all passages.
            new_dist = dist + 1.0

            if new_dist < neighbor.distance:
                neighbor.distance = new_dist
                neighbor.parent = current
                counter += 1
                heapq.heappush(heap, (new_dist, counter, neighbor))

        yield explored, [], False  # Intermediate step — still searching.

    # Destination unreachable.
    yield explored, [], True


# ---------------------------------------------------------------------------
# Breadth-First Search (BFS)
# ---------------------------------------------------------------------------

def bfs(
    maze: Maze,
    start: Cell,
    end: Cell,
) -> Generator[Tuple[Set[Cell], List[Cell], bool], None, None]:
    """
    Breadth-First Search guarantees the shortest path in an unweighted graph.

    BFS explores all nodes at depth d before any node at depth d+1, making
    it optimal for uniform-cost graphs such as this maze.

    Data Structures:
      - deque (double-ended queue) for O(1) FIFO enqueue/dequeue.
      - Set for O(1) visited membership testing.

    Time Complexity:
      O(V + E) — every cell and passage is processed at most once.

    Space Complexity:
      O(V) — the queue can hold up to V cells; parent pointers add O(V).

    Args:
        maze  (Maze): The maze structure.
        start (Cell): Starting cell.
        end   (Cell): Goal cell.

    Yields:
        Tuple[Set[Cell], List[Cell], bool]: Same contract as `dijkstra`.
    """
    maze.reset_solver_state()

    explored: Set[Cell] = set()
    queue: deque[Cell] = deque()

    start.explored = True
    explored.add(start)
    queue.append(start)

    while queue:
        current: Cell = queue.popleft()  # O(1) for deque.

        if current == end:
            path = _reconstruct_path(end)
            for cell in path:
                cell.in_path = True
            yield explored, path, True
            return

        for neighbor in maze.get_accessible_neighbors(current):
            if neighbor not in explored:
                neighbor.explored = True
                neighbor.parent = current
                explored.add(neighbor)
                queue.append(neighbor)

        yield explored, [], False

    # Destination unreachable.
    yield explored, [], True


# ---------------------------------------------------------------------------
# Depth-First Search (DFS)
# ---------------------------------------------------------------------------

def dfs(
    maze: Maze,
    start: Cell,
    end: Cell,
) -> Generator[Tuple[Set[Cell], List[Cell], bool], None, None]:
    """
    Depth-First Search explores as far as possible along each branch before
    backtracking.

    Important: DFS does NOT guarantee the shortest path. It finds *a* path,
    which may be significantly longer than optimal. It is included to
    contrast visually and analytically with BFS and Dijkstra.

    Data Structures:
      - list used as an explicit LIFO stack for O(1) push/pop.
      - Set for O(1) visited membership testing.

    Time Complexity:
      O(V + E) — each cell and passage visited at most once.

    Space Complexity:
      O(V) — the stack can grow to V entries in the worst case (a single
              long winding path through the entire graph).

    Args:
        maze  (Maze): The maze structure.
        start (Cell): Starting cell.
        end   (Cell): Goal cell.

    Yields:
        Tuple[Set[Cell], List[Cell], bool]: Same contract as `dijkstra`.
    """
    maze.reset_solver_state()

    explored: Set[Cell] = set()
    stack: List[Cell] = [start]

    while stack:
        current: Cell = stack.pop()  # LIFO — O(1).

        if current in explored:
            continue  # Already processed via another stack entry.

        explored.add(current)
        current.explored = True

        if current == end:
            path = _reconstruct_path(end)
            for cell in path:
                cell.in_path = True
            yield explored, path, True
            return

        for neighbor in maze.get_accessible_neighbors(current):
            if neighbor not in explored:
                neighbor.parent = current
                stack.append(neighbor)

        yield explored, [], False

    # Destination unreachable.
    yield explored, [], True
