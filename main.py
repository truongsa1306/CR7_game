"""
main.py
=======
Integration entry point for CR7 Algorithm Quest.
"""
import pygame

import config as C
from scenes.gameover_scene import GameOverScene
from scenes.gameplay_scene import GameplayScene
from scenes.intro_scene import IntroScene
from scenes.level_select_scene import LevelSelectScene
from scenes.levelup_scene import LevelUpScene
from scenes.victory_scene import VictoryScene
from systems.game_state import GameState
from systems.scene_manager import SceneManager


def build_scene_manager():
    game_state = GameState()
    manager = SceneManager()
    manager.register(C.STATE_INTRO, IntroScene(manager, game_state))
    manager.register(C.STATE_LEVEL_SELECT, LevelSelectScene(manager, game_state))
    manager.register(C.STATE_GAMEPLAY, GameplayScene(manager, game_state))
    manager.register(C.STATE_LEVELUP, LevelUpScene(manager, game_state))
    manager.register(C.STATE_GAMEOVER, GameOverScene(manager, game_state))
    manager.register(C.STATE_VICTORY, VictoryScene(manager, game_state))
    manager.change(C.STATE_INTRO)
    return manager


def main():
    pygame.init()
    screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
    pygame.display.set_caption(C.GAME_TITLE)
    clock = pygame.time.Clock()
    manager = build_scene_manager()

    running = True
    while running:
        dt = clock.tick(C.FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                manager.handle_event(event)

        manager.update(dt)
        manager.draw(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
