# Copyright 2016, Jeremy Nation <jeremy@jeremynation.me>
# Released under the GPLv3. See included LICENSE file.
"""
Module containing the main game loop for Roguelike Sokoban.

Functions:

main(scrn, level_file_name = const.DEFAULT_LEVEL_FILE_NAME) : Set up the game
    and enter the main game loop.
    
"""

import curses
import action
import constants as const
import display
import gameobjects
import highscores
import levelloader

__author__ = const.AUTHOR
__email__ = const.AUTHOR_EMAIL
__copyright__ = const.COPYRIGHT
__license__ = const.LICENSE
__version__ = const.VERSION

def main(scrn, level_file_name = const.DEFAULT_LEVEL_FILE_NAME_FULL):
    """Set up the game and enter the main game loop.
    
    This function runs the game and should be passed to curses.wrapper(...).
    
    Input:
    
    scrn : the main curses window generated by curses.wrapper(...).
    
    level_file_name : the name of the level file to load. Defaults to
        const.DEFAULT_LEVEL_FILE_NAME_FULL.
    
    """
    if curses.has_colors():
        curses.use_default_colors()
    disp = display.Display(scrn)
    loader = levelloader.LevelLoader(level_file_name)
    hs = highscores.HighScores()
    keep_playing = True
    name = None
    while keep_playing:
        univ = gameobjects.universe.Universe(loader.get_level(disp, name))
        high_score = hs.get_high_score(level_file_name, univ.level_name)
        disp.level_init(univ, high_score)
        while True:
            disp.draw(univ)
            act = disp.get_action()
            if act == action.QUIT:
                raise KeyboardInterrupt
            elif univ.game_won:
                if act == action.PLAY_AGAIN:
                    name = None
                    break
                else:
                    pass
            else:
                if act == action.PLAY_AGAIN:
                    name = univ.level_name
                    break
                elif act == action.OTHER:
                    pass
                else:
                    univ.eval_action(act)
                    if univ.game_won and (univ.moves_taken < high_score or
                                          high_score == const.NO_SCORE_SET):
                        hs.set_high_score(level_file_name, univ.level_name,
                                          univ.moves_taken)
                        hs.save_high_scores()
