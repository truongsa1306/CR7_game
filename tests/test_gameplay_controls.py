import unittest

from entities.grid_cell import ORTHOGONAL_DIRECTIONS, GridModel
from scenes.caro_scene import (
    AI,
    EMPTY,
    HUMAN,
    best_move_ai,
    chance_probabilities,
    evaluate,
    expectimax,
    get_moves,
)
from scenes.gameplay_scene import GameplayScene
from systems.algorithms.blind_search import bfs_steps
from systems.game_state import GameState


class GameplayControlsTests(unittest.TestCase):
    def test_select_algorithm_changes_name_and_restarts(self):
        manager = type('Manager', (), {'change': lambda self, state: None})()
        game_state = GameState()
        scene = GameplayScene(manager, game_state)
        scene._select_algorithm('DFS')
        self.assertEqual(scene.algorithm_name, 'DFS')
        self.assertTrue(scene.auto_play)

    def test_select_algorithm_clears_suggest_algorithm(self):
        manager = type('Manager', (), {'change': lambda self, state: None})()
        game_state = GameState()
        game_state.suggest_algorithm = 'Stochastic HC'
        scene = GameplayScene(manager, game_state)
        scene._select_algorithm('DFS')
        self.assertIsNone(game_state.suggest_algorithm)

    def test_select_algorithm_handles_uninitialized_grid_without_crashing(self):
        manager = type('Manager', (), {'change': lambda self, state: None})()
        game_state = GameState()
        scene = GameplayScene(manager, game_state)
        scene._select_algorithm('UCS')
        self.assertEqual(scene.algorithm_name, 'UCS')
        self.assertTrue(scene.auto_play)
        self.assertIsNotNone(scene.generator)

    def test_next_step_towards_returns_orthogonal_neighbor(self):
        manager = type('Manager', (), {'change': lambda self, state: None})()
        game_state = GameState()
        scene = GameplayScene(manager, game_state)
        scene.grid = GridModel(3, 3, (0, 0), (2, 0), fog=False)
        scene.player.place_at_grid(0, 0, (0, 0), 1)
        self.assertEqual(scene._next_step_towards((0, 2)), (0, 1))

    def test_grid_neighbors_are_orthogonal_only(self):
        grid = GridModel(3, 3, (1, 1), (2, 2), fog=False)
        neighbors = {(cell.col, cell.row) for cell in grid.neighbors(1, 1)}
        self.assertEqual(neighbors, {(0, 1), (2, 1), (1, 0), (1, 2)})
        self.assertNotIn((0, 0), neighbors)
        self.assertNotIn((2, 2), neighbors)
        self.assertEqual(ORTHOGONAL_DIRECTIONS, ((-1, 0), (1, 0), (0, -1), (0, 1)))

    def test_reveal_around_is_orthogonal_only(self):
        grid = GridModel(3, 3, (1, 1), (2, 1), fog=True)
        grid.reveal_around(1, 1, radius=1)
        revealed = {(col, row) for (col, row), cell in grid.cells.items() if cell.revealed}
        self.assertTrue((0, 1) in revealed)
        self.assertTrue((2, 1) in revealed)
        self.assertTrue((1, 0) in revealed)
        self.assertTrue((1, 2) in revealed)
        self.assertFalse((0, 0) in revealed)
        self.assertFalse((2, 2) in revealed)

    def test_bfs_keeps_new_neighbors_in_frontier(self):
        grid = GridModel(3, 3, (0, 0), (2, 2), fog=False)
        step = next(bfs_steps(grid))
        self.assertEqual(step["current"], (0, 0))
        self.assertEqual(set(step["frontier"]), {(1, 0), (0, 1)})
        self.assertEqual(step["visited"], {(0, 0), (1, 0), (0, 1)})

    def test_bfs_reached_includes_neighbors_after_enqueue(self):
        grid = GridModel(3, 3, (0, 0), (2, 2), fog=False)
        step = next(bfs_steps(grid))
        self.assertIn((1, 0), step["visited"])
        self.assertIn((0, 1), step["visited"])

    def test_bfs_does_not_reveal_neighbors_before_player_moves(self):
        grid = GridModel(3, 3, (0, 0), (2, 2), fog=True)
        next(bfs_steps(grid))
        revealed = {(col, row) for (col, row), cell in grid.cells.items() if cell.revealed}
        self.assertEqual(revealed, {(0, 0), (2, 2)})


class CaroExpectimaxTests(unittest.TestCase):
    def test_chance_node_uses_uniform_average(self):
        board = [
            [AI, EMPTY, EMPTY],
            [EMPTY, HUMAN, EMPTY],
            [EMPTY, EMPTY, EMPTY],
        ]
        moves = get_moves(board)
        probabilities = chance_probabilities(moves)
        self.assertAlmostEqual(sum(probabilities), 1.0)
        for probability in probabilities:
            self.assertAlmostEqual(probability, 1 / len(moves))

        values = []
        for row, col in moves:
            board[row][col] = HUMAN
            values.append(evaluate(board))
            board[row][col] = EMPTY

        nodes = [0]
        self.assertAlmostEqual(expectimax(board, 1, False, nodes), sum(values) / len(values))

    def test_expectimax_is_deterministic(self):
        board = [
            [AI, EMPTY, EMPTY],
            [EMPTY, HUMAN, EMPTY],
            [EMPTY, EMPTY, EMPTY],
        ]
        first = best_move_ai([row[:] for row in board], "Expectimax", 3)
        second = best_move_ai([row[:] for row in board], "Expectimax", 3)
        self.assertEqual(first[0], second[0])
        self.assertAlmostEqual(first[3], second[3])


if __name__ == '__main__':
    unittest.main()
