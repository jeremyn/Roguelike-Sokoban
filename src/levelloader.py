# Copyright 2016, Jeremy Nation <jeremy@jeremynation.me>
# Released under the GPLv3. See included LICENSE file.
import constants as const


class MalformedLevelFileError(Exception):

    pass

class LevelFileHandlingError(Exception):
    
    pass

class LevelLoader(object):

    def __init__(self, level_file_name):
        self.level_file_name = level_file_name
        try:
            level_file = open(self.level_file_name)
        except IOError:
            reason = "could not open file \'%s\'." % self.level_file_name
            raise LevelFileHandlingError(reason)
        raw_level_file_lines = level_file.readlines()
        if raw_level_file_lines == []:
            reason = "file \'%s\' is empty." % self.level_file_name
            raise MalformedLevelFileError(reason)
        temp_level_file_lines = []
        level_symbol_lines = []
        symbol_type_counter = 0
        for i, line in enumerate(raw_level_file_lines):
            if line.strip() == "":
                reason = "blank line found in file \'%s\'." % \
                        self.level_file_name
                raise MalformedLevelFileError(reason)
            elif line[0] == const.COMMENT:
                continue
            elif symbol_type_counter < len(const.LEVEL_SYMBOL_TYPES):
                symbol_type_counter += 1
                level_symbol_lines.append(line)
                continue
            elif line[0].isalpha():
                line = line[:const.MAX_LEVEL_NAME_LENGTH]
                try:
                    if raw_level_file_lines[i+1][0].isalpha():
                        raise MalformedLevelFileError
                except (IndexError, MalformedLevelFileError):
                    reason = "empty level \'%s\' found in file \'%s\'." % \
                            (line.strip(), self.level_file_name)
                    raise MalformedLevelFileError(reason)
                temp_level_file_lines.append(line.rstrip())
            else:
                temp_level_file_lines.append(line.rstrip())
        self.level_file_lines = temp_level_file_lines
        self.__set_level_symbols(level_symbol_lines)
        self.__set_level_names()
        
    def __set_level_symbols(self, level_symbol_lines):
        level_sym = {}
        for line in level_symbol_lines:
            name, symbol = line.split("=")
            name = name.strip()
            symbol = symbol.strip()
            if name not in const.LEVEL_SYMBOL_TYPES:
                reason = "unrecognized symbol type \'%s\' found in file "\
                        "\'%s\'. Recognized symbol types are: " % \
                        (name, self.level_file_name)
                for i, sym in enumerate(const.LEVEL_SYMBOL_TYPES):
                    reason += sym
                    if i != (len(const.LEVEL_SYMBOL_TYPES)-1):
                        reason += ", "
                    else:
                        reason += "."
                raise MalformedLevelFileError(reason)
            for key in level_sym:
                if name == key:
                    reason = "symbol type \'%s\' defined more than once in "\
                            "file \'%s\'." % (name, self.level_file_name)
                    raise MalformedLevelFileError(reason)
                if symbol == level_sym[key]:
                    reason = "symbol \'%s\' used for more than one symbol "\
                            "type in file \'%s\'." % (symbol, 
                                                      self.level_file_name)
                    raise MalformedLevelFileError(reason)
            level_sym[name] = symbol
        self.level_sym = level_sym

    def __set_level_names(self):
        level_names = []
        for line in self.level_file_lines:
            if line[0].isalpha():
                if line in level_names:
                    reason = "duplicate level name \'%s\' found in file "\
                    "\'%s\'." % (line, self.level_file_name)
                    raise MalformedLevelFileError(reason)
                else:
                    level_names.append(line)
        if level_names == []:
            reason = "no level names found in file \'%s\'." % \
                    self.level_file_name
            raise MalformedLevelFileError(reason)
        if len(level_names) > const.MAX_LEVELS_PER_FILE:
            reason = "more than %d levels found in file \'%s\'." % \
                    (const.MAX_LEVELS_PER_FILE, self.level_file_name)
            raise MalformedLevelFileError(reason)
        self.level_names = level_names
        
    def get_level(self, disp, name = None):
        if name is not None:
            for entry in self.level_names:
                if name == entry[:len(name)]:
                    chosen_level_name = entry
                    break
        else:
            chosen_level_name = disp.level_prompt(self.level_names, 
                                              self.level_file_name)
        choice_number = self.level_names.index(chosen_level_name)
        start = self.level_file_lines.index(chosen_level_name) + 1
        if (choice_number + 1) == len(self.level_names):
            end = len(self.level_file_lines)
        else:
            end = self.level_file_lines.index(self.level_names[choice_number
                                                               + 1])
        self.chosen_level_name = chosen_level_name.strip()
        self.chosen_level_lines = self.level_file_lines[start:end]
        self.__process_level_lines()
        self.__exception_if_level_unplayable()
        return self.chosen_level_name, self.chosen_level_lines, self.level_sym

    def __process_level_lines(self):
        level = self.chosen_level_lines
        max_line_length = reduce(max, [len(line) for line in level])
        # Pad each line with spaces to the end of the longest line.
        for line_num, line in enumerate(level[:]):
            line = list(line)
            while len(line) < max_line_length:
                line.append(" ")
            level[line_num] = line
        # Add line of spaces to the beginning and end of level.
        blank_line = []
        while len(blank_line) < max_line_length:
            blank_line.append(" ")
        level.insert(0, blank_line)
        level.append(blank_line)
        # Add a space to the beginning and end of each line
        for row in level:
            row.insert(0, " ")
            row.append(" ")

    def __exception_if_level_unplayable(self):
        boulders = 0
        players = 0
        pits = 0
        for row in self.chosen_level_lines:
            for square in row:
                if square == self.level_sym["Boulder"]:
                    boulders += 1
                elif square == self.level_sym["Player"]:
                    players += 1
                elif square == self.level_sym["Pit"]:
                    pits += 1
        if players != 1:
            reason = "level \'%s\' in file \'%s\' does not have exactly one "\
                    "player \'%s\'." % (self.chosen_level_name,
                                        self.level_file_name,
                                        self.level_sym["Player"])
            raise MalformedLevelFileError(reason)
        if pits == 0:
            reason = "level \'%s\' in file \'%s\' has no pits \'%s\'." % \
                    (self.chosen_level_name, self.level_file_name,
                     self.level_sym["Pit"])
            raise MalformedLevelFileError(reason)
        if boulders < pits:
            reason = "level \'%s\' in file \'%s\' does not have enough "\
                    "boulders (%s) to fill the pits \'%s\'." % \
                    (self.chosen_level_name, self.level_file_name,
                     self.level_sym["Boulder"], self.level_sym["Pit"])
            raise MalformedLevelFileError(reason)
