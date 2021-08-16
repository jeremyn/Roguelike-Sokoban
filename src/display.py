"""
Copyright 2021, Jeremy Nation <jeremy@jeremynation.me>
Released under the GPLv3. See included LICENSE file.

"""
import curses
from typing import Literal, Optional

from src import constants as const
from src.universe import Universe

Action = const.Action

_Lines = dict[Literal["top", "bottom"], list[str]]
_Scroll = dict[str, bool]


class _Coordinates(object):
    def __init__(self, scrn: curses.window, lines: _Lines, univ: Universe):
        self.min_y, self.min_x = scrn.getbegyx()
        self.max_y, self.max_x = scrn.getmaxyx()
        self.mid_y = (self.max_y + self.min_y) // 2
        self.mid_x = (self.max_x + self.min_x) // 2
        self.level_height = len(univ.level_map)
        self.level_width = len(univ.level_map[0])
        self.levelpad_coords, self.scroll_info = self._find_levelpad_coords(lines, univ)
        self._exception_if_too_small(lines)

    def _exception_if_too_small(self, lines: _Lines) -> None:
        padding_for_level_view = 7
        extracted_lines = lines["top"] + lines["bottom"]
        min_height = len(extracted_lines) + padding_for_level_view
        min_width = max([len(line) for line in extracted_lines])
        if self.max_y < min_height or self.max_x < min_width:
            raise Exception(const.TERMINAL_TOO_SMALL_TEXT)

    def _find_levelpad_coords(
        self, lines: _Lines, univ: Universe
    ) -> tuple[tuple[int, int, int, int, int, int], _Scroll]:
        avail_min_y = self.min_y + len(lines["top"]) + 1
        avail_max_y = self.max_y - len(lines["bottom"]) - 2
        avail_min_x = self.min_x + 1
        avail_max_x = self.max_x - 2
        avail_y = avail_max_y - avail_min_y
        avail_x = avail_max_x - avail_min_x
        # Make avail_y and avail_x always even to prevent glitching due to
        # division by 2.
        if avail_y % 2 != 0:
            avail_y -= 1
        if avail_x % 2 != 0:
            avail_x -= 1
        avail_mid_y = (avail_max_y + avail_min_y) // 2
        # +1 in avail_mid_x centers the map better.
        avail_mid_x = (avail_max_x + avail_min_x) // 2 + 1

        player_y = univ.player.curr_y
        player_x = univ.player.curr_x

        if avail_y >= self.level_height:
            pminy = 0
            sminy = avail_mid_y - (self.level_height // 2)
            smaxy = avail_mid_y + (self.level_height // 2)
        else:
            if (self.level_height - player_y) < (avail_y // 2):
                pminy = self.level_height - avail_y
            else:
                pminy = player_y - (avail_y // 2)
            sminy = avail_min_y
            smaxy = avail_max_y

        if avail_x >= self.level_width:
            pminx = 0
            sminx = avail_mid_x - (self.level_width // 2)
            smaxx = avail_mid_x + (self.level_width // 2)
        else:
            if (self.level_width - player_x) < (avail_x // 2):
                pminx = self.level_width - avail_x
            else:
                pminx = player_x - (avail_x // 2)
            sminx = avail_min_x
            smaxx = avail_max_x

        scroll: _Scroll = {
            "UP": pminy > 0,
            "DOWN": (
                self.level_height > avail_y and pminy < self.level_height - avail_y
            ),
            "LEFT": pminx > 0,
            "RIGHT": (
                self.level_width > avail_x and pminx < self.level_width - avail_x
            ),
        }

        return (pminy, pminx, sminy, sminx, smaxy, smaxx), scroll


class Display(object):
    def __init__(self, scrn: curses.window, univ: Universe, best_score: Optional[int]):
        self.scrn = scrn
        self.levelpad = curses.newpad(
            len(univ.level_map) + 1,
            len(univ.level_map[0]) + 1,
        )
        self.level_sym = univ.level_sym
        self.text = {
            "game_name": const.GAME_NAME,
            "bug_line": "",
            "instructions1": (
                "Use the arrow keys to move around, '%s' to quit, and '%s' to "
                "restart this level." % (const.QUIT, const.PLAY_AGAIN)
            ),
            "instructions2": (
                "Move yourself (%s) over floor (%s) into boulders (%s) to "
                "push them into pits (%s)."
                % (
                    self.level_sym["player"],
                    self.level_sym["floor"],
                    self.level_sym["boulder"],
                    self.level_sym["pit"],
                )
            ),
            "level_name": "Level: %s" % univ.level_name,
            "blank": "      ",
            # scroll_info_line here is just a max sized placeholder.
            # scroll_info_line is set in __set_scroll_line(...).
            "scroll_info_line": "Scroll: UP, DOWN, LEFT, RIGHT",
            "goal": "Fill every pit to solve the puzzle.",
            "play_again_prompt": ("-- Press '%s' to play again --" % const.PLAY_AGAIN),
            "quit_prompt": "-- Press '%s' to quit --" % const.QUIT,
        }
        self.best_score = best_score

    def _return_lines(self, univ: Universe) -> _Lines:
        self.text["status_pits"] = "Pits remaining: %d" % univ.pits_remaining
        self.text["status_moves"] = "Moves used: %d" % univ.moves_taken
        self.text["status_boulders"] = "Boulders remaining: %d" % len(univ.boulders)
        self.text[
            "congratulations"
        ] = "You solved the puzzle in %d move%s! Congratulations! " % (
            univ.moves_taken,
            "s" if univ.moves_taken > 1 else "",
        )
        if self.best_score is None:
            self.text["best_score"] = "No current best score"
            self.text["compared_to_best_score"] = (
                "You set the first best score of %d moves!" % univ.moves_taken
            )
        else:
            self.text["best_score"] = "Current best score: %d" % self.best_score
            if univ.moves_taken < self.best_score:
                self.text["compared_to_best_score"] = (
                    "You beat the current best score of %d moves!" % self.best_score
                )
            else:
                self.text["compared_to_best_score"] = ""

        lines: _Lines
        if not univ.game_won:
            lines = {
                "top": [
                    self.text["game_name"],
                    self.text["instructions1"],
                    self.text["instructions2"],
                    self.text["goal"],
                    self.text["level_name"],
                ],
                "bottom": [
                    self.text["scroll_info_line"],
                    (
                        self.text["status_pits"]
                        + self.text["blank"]
                        + self.text["status_boulders"]
                        + self.text["blank"]
                        + self.text["status_moves"]
                    ),
                    self.text["best_score"],
                    self.text["bug_line"],
                ],
            }
        else:
            lines = {
                "top": [
                    self.text["game_name"],
                    self.text["congratulations"],
                    self.text["compared_to_best_score"],
                    self.text["blank"],
                    self.text["level_name"],
                ],
                "bottom": [
                    self.text["blank"],
                    self.text["play_again_prompt"],
                    self.text["quit_prompt"],
                    self.text["bug_line"],
                ],
            }
        return lines

    def _set_scroll_line(self, scroll_info: _Scroll) -> None:
        scroll_info_line = "Scroll: "
        for direction in ("UP", "DOWN", "LEFT", "RIGHT"):
            if scroll_info[direction]:
                scroll_info_line += direction + ", "
        if scroll_info_line == "Scroll: ":
            scroll_info_line = ""
        else:
            scroll_info_line = scroll_info_line[:-2]
        self.text["scroll_info_line"] = scroll_info_line

    def _paint_line(self, row: int, line: str) -> None:
        t_min_x = self.coords.mid_x - (len(line) // 2)
        for i, char in enumerate(line):
            if line == self.text["instructions2"] and char == self.level_sym["player"]:
                self.scrn.addch(row, t_min_x + i, char, curses.A_REVERSE)
            else:
                self.scrn.addch(row, t_min_x + i, char)

    def _paint_text_lines(self, lines: _Lines) -> None:
        for line_number, line in enumerate(lines["top"]):
            self._paint_line(self.coords.min_y + line_number, line)
        for line_number, line in enumerate(lines["bottom"]):
            self._paint_line(
                self.coords.max_y - len(lines["bottom"]) + line_number, line
            )

    def _paint_levelpad(self, univ: Universe) -> None:
        for row_index, row in enumerate(univ.level_map):
            for col_index, square in enumerate(row):
                self.levelpad.addch(row_index, col_index, square)

        player_y = univ.player.curr_y
        player_x = univ.player.curr_x
        player_sym = univ.player.symbol
        self.levelpad.addch(player_y, player_x, player_sym, curses.A_REVERSE)

        for boulder in univ.boulders:
            b_y, b_x, b_sym = boulder.curr_y, boulder.curr_x, boulder.symbol
            self.levelpad.addch(b_y, b_x, b_sym)

    def draw(self, univ: Universe) -> None:
        self.scrn.clear()
        lines = self._return_lines(univ)
        self.coords = _Coordinates(self.scrn, lines, univ)
        self._set_scroll_line(self.coords.scroll_info)
        lines = self._return_lines(univ)
        self._paint_text_lines(lines)
        self.scrn.noutrefresh()
        self._paint_levelpad(univ)
        pminy, pminx, sminy, sminx, smaxy, smaxx = self.coords.levelpad_coords
        self.levelpad.noutrefresh(pminy, pminx, sminy, sminx, smaxy, smaxx)
        curses.doupdate()
        curses.curs_set(0)

    def get_action(self) -> Action:
        k = self.scrn.getch()
        if k == curses.KEY_RESIZE:
            self.scrn.clear()
            curses.endwin()
            self.scrn.refresh()
            act = Action.OTHER
        if k == curses.KEY_UP:
            act = Action.UP
        elif k == curses.KEY_DOWN:
            act = Action.DOWN
        elif k == curses.KEY_LEFT:
            act = Action.LEFT
        elif k == curses.KEY_RIGHT:
            act = Action.RIGHT
        elif k == ord(const.QUIT):
            act = Action.QUIT
        elif k == ord(const.PLAY_AGAIN):
            act = Action.PLAY_AGAIN
        else:
            act = Action.OTHER
        return act
