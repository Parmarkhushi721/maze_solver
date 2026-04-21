# Pygame Maze Solver

An interactive Python project that generates random mazes and visualizes how different pathfinding algorithms solve them in real time.

This app uses `pygame` to animate:

- Random maze generation
- Pathfinding with Dijkstra's Algorithm, BFS, and DFS
- Custom start and end point selection
- Live stats such as explored cells, path length, and solve time

## Features

- Real-time maze generation animation
- Step-by-step solving visualization
- Compare three search algorithms on the same maze
- Click to choose custom start and end cells
- Simple HUD and legend for understanding the visualization

## Tech Stack

- Python
- Pygame
- `dataclass`-based maze/cell modeling

## Project Structure

| File | Purpose |
|---|---|
| `main.py` | Entry point, app state machine, input handling, main loop |
| `maze.py` | Core `Cell` and `Maze` data structures |
| `generator.py` | Random maze generation logic |
| `algorithms.py` | Dijkstra, BFS, and DFS implementations |
| `visualizer.py` | Rendering, HUD, legends, and animation drawing |
| `PROJECT_REPORT.md` | Detailed project analysis and documentation |

## Installation

1. Make sure Python 3 is installed.
2. Install `pygame`:

```bash
python -m pip install pygame
```

## Run the Project

```bash
python main.py
```

When the window opens, generate a maze first and then choose an algorithm to solve it.

## Controls

| Action | Control |
|---|---|
| Generate a new maze | `SPACE` |
| Solve with Dijkstra | `D` |
| Solve with BFS | `B` |
| Solve with DFS | `F` |
| Reset current solve | `R` |
| Set start / end cells | Left mouse click |
| Quit | `ESC` |

The first click sets the start cell, and the second click sets the end cell.

## How It Works

The maze is treated as a graph:

- Each cell is a node
- Open passages between cells are edges
- The generator carves a connected maze
- The solver algorithms explore the graph to find a path from start to end

The application updates generation and solving in small steps each frame, which makes the process easy to follow visually.

## Notes

- The project currently does not include a `requirements.txt` or `pyproject.toml`.
- A graphical environment is required because the app runs with `pygame`.
- Default maze sizing and animation speed can be adjusted in `main.py`.

## Future Improvements

- Add A* search
- Add automated tests
- Add packaging and dependency files
- Improve configuration through CLI options or a settings menu

## License

Add a license file if you plan to publish or distribute this project.
