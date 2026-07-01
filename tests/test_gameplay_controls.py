import unittest

from entities.grid_cell import ORTHOGONAL_DIRECTIONS, GridModel
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

    def test_level_two_has_random_and_edit_buttons(self):
        manager = type('Manager', (), {'change': lambda self, state: None})()
        game_state = GameState()
        game_state.level = 1
        scene = GameplayScene(manager, game_state)
        scene._create_algorithm_buttons()
        self.assertIsNotNone(scene.randomize_button)
        self.assertIsNotNone(scene.matrix_edit_button)
        self.assertIsNotNone(scene.progress_prev_button)

    def test_level_two_default_values_match_cell_meaning(self):
        manager = type('Manager', (), {'change': lambda self, state: None})()
        game_state = GameState()
        game_state.level = 1
        scene = GameplayScene(manager, game_state)
        scene.algorithm_name = 'UCS'
        scene._reset_algorithm_run(reset_energy=False)
        fire_values = [cell.value for cell in scene.grid.cells.values() if cell.kind == 'fire']
        positive_values = [cell.value for cell in scene.grid.cells.values() if cell.kind == 'path']
        self.assertTrue(all(value < 0 for value in fire_values))
        self.assertTrue(any(value > 0 for value in positive_values))

    def test_edit_cycles_level_two_cell(self):
        manager = type('Manager', (), {'change': lambda self, state: None})()
        game_state = GameState()
        game_state.level = 1
        scene = GameplayScene(manager, game_state)
        scene.algorithm_name = 'UCS'
        scene._reset_algorithm_run(reset_energy=False)
        scene.matrix_edit_mode = True
        pos = (1, 1)
        rect_pos = (
            scene.grid_rect.left + pos[0] * scene.cell_size + scene.cell_size // 2,
            scene.grid_rect.top + pos[1] * scene.cell_size + scene.cell_size // 2,
        )
        before = scene.grid.get(*pos).value
        self.assertTrue(scene._handle_matrix_edit_click(rect_pos))
        after = scene.grid.get(*pos).value
        self.assertNotEqual(before, after)

    def test_level_three_has_random_edit_and_step_controls(self):
        manager = type('Manager', (), {'change': lambda self, state: None})()
        game_state = GameState()
        game_state.level = 2
        scene = GameplayScene(manager, game_state)
        scene._create_algorithm_buttons()
        self.assertIsNotNone(scene.randomize_button)
        self.assertIsNotNone(scene.matrix_edit_button)
        self.assertIsNotNone(scene.progress_next_button)
        self.assertIsNotNone(scene.progress_auto_button)
        self.assertIsNone(scene.progress_prev_button)

    def test_level_three_grid_scales_to_available_area(self):
        manager = type('Manager', (), {'change': lambda self, state: None})()
        game_state = GameState()
        game_state.level = 2
        scene = GameplayScene(manager, game_state)
        scene.algorithm_name = 'Hill Climbing'
        scene._reset_algorithm_run(reset_energy=False)
        expected = min(64, 640 // scene.grid.cols, 400 // scene.grid.rows)
        self.assertEqual(scene.cell_size, expected)
        self.assertEqual(scene.grid_rect.size, (scene.grid.cols * expected, scene.grid.rows * expected))

    def test_level_three_cells_cache_shared_h_function(self):
        manager = type('Manager', (), {'change': lambda self, state: None})()
        game_state = GameState()
        game_state.level = 2
        scene = GameplayScene(manager, game_state)
        scene.algorithm_name = 'Hill Climbing'
        scene._reset_algorithm_run(reset_energy=False)
        for (col, row), cell in scene.grid.cells.items():
            if cell.passable:
                self.assertEqual(cell.h, scene.grid.heuristic_value(col, row))

    def test_level_three_edit_cycles_terrain_and_restarts(self):
        manager = type('Manager', (), {'change': lambda self, state: None})()
        game_state = GameState()
        game_state.level = 2
        scene = GameplayScene(manager, game_state)
        scene.algorithm_name = 'Hill Climbing'
        scene._reset_algorithm_run(reset_energy=False)
        scene.matrix_edit_mode = True
        pos = next(pos for pos in scene.grid.cells if pos not in (scene.grid.start, scene.grid.goal))
        click = (
            scene.grid_rect.left + pos[0] * scene.cell_size + scene.cell_size // 2,
            scene.grid_rect.top + pos[1] * scene.cell_size + scene.cell_size // 2,
        )
        before = (scene.grid.get(*pos).kind, scene.grid.get(*pos).value)
        self.assertTrue(scene._handle_matrix_edit_click(click))
        after = (scene.grid.get(*pos).kind, scene.grid.get(*pos).value)
        self.assertNotEqual(before, after)
        self.assertIn('cập nhật', scene.hill_status_message.lower())

    def test_hill_loop_is_reported_without_changing_scene(self):
        manager = type('Manager', (), {'last': None, 'change': lambda self, state: setattr(self, 'last', state)})()
        game_state = GameState()
        game_state.level = 2
        scene = GameplayScene(manager, game_state)
        scene.algorithm_name = 'Hill Climbing'
        scene._reset_algorithm_run(reset_energy=False)
        current = scene.grid.start
        repeated = next((cell.col, cell.row) for cell in scene.grid.neighbors(*current))
        scene.hill_path_history = [current, repeated]
        scene.generator = iter([{
            'current': current,
            'neighbor_scores': {repeated: scene.grid.heuristic_value(*repeated)},
            'chosen': repeated,
            'candidate': repeated,
            'phase': 'inspect',
            'decision': 'accept',
            'improving_neighbors': [repeated],
            'stuck': False,
            'loop': False,
            'path': None,
            'temperature': None,
        }])
        scene._advance_algorithm()
        self.assertIsNone(scene.generator)
        self.assertIn('loop', scene.hill_status_message.lower())
        self.assertIsNone(manager.last)


if __name__ == '__main__':
    unittest.main()
