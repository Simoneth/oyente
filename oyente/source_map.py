import json
import global_params
from utils import run_command

class Source:
    def __init__(self, filename):
        self.filename = filename
        self.content = self.__load_content()
        self.line_break_positions = self.__load_line_break_positions()

    def __load_content(self):
        with open(self.filename, 'r') as f:
            content = f.read()
        return content

    def __load_line_break_positions(self):
        return [i for i, letter in enumerate(self.content) if letter == '\n']

class SourceMap:
    parent_filename = ""
    position_groups = {}
    sources = {}

    def __init__(self, cname, parent_filename):
        self.cname = cname
        if not SourceMap.parent_filename:
            SourceMap.parent_filename = parent_filename
            SourceMap.position_groups = SourceMap.__load_position_groups()
        self.source = self.__get_source()
        self.positions = self.__get_positions()
        self.instr_positions = {}

    def find_source_code(self, pc):
        try:
            pos = self.instr_positions[pc]
        except:
            return ""
        begin = pos['begin']
        end = pos['end']
        return self.source.content[begin:end]

    def to_str(self, pcs, bug_name):
        s = ""
        for pc in pcs:
            source_code = self.find_source_code(pc).split("\n", 1)[0]
            if not source_code:
                continue

            location = self.get_location(pc)
            if global_params.WEB:
                s += "%s:%s:%s: %s:<br />" % (self.cname.split(":", 1)[1], location['begin']['line'] + 1, location['begin']['column'] + 1, bug_name)
                s += "<span style='margin-left: 20px'>%s</span><br />" % source_code
                s += "<span style='margin-left: 20px'>^</span><br />"
            else:
                s += "\n%s:%s:%s\n" % (self.cname, location['begin']['line'] + 1, location['begin']['column'] + 1)
                s += source_code + "\n"
                s += "^"
        return s

    def get_location(self, pc):
        pos = self.instr_positions[pc]
        return self.__convert_offset_to_line_column(pos)

    def reduce_same_position_pcs(self, pcs):
        d = {}
        for pc in pcs:
            pos = str(self.instr_positions[pc])
            if pos not in d:
                d[pos] = pc
        return d.values()

    def __get_source(self):
        fname = self.__get_filename()
        if SourceMap.sources.has_key(fname):
            return SourceMap.sources[fname]
        else:
            SourceMap.sources[fname] = Source(fname)
            return SourceMap.sources[fname]

    @classmethod
    def __load_position_groups(cls):
        cmd = "solc --combined-json asm %s" % cls.parent_filename
        out = run_command(cmd)
        out = json.loads(out)
        return out['contracts']

    def __get_positions(self):
        asm = SourceMap.position_groups[self.cname]['asm']['.data']['0']
        positions = asm['.code']
        while(True):
            try:
                positions.append(None)
                positions += asm['.data']['0']['.code']
                asm = asm['.data']['0']
            except:
                break
        return positions

    def __get_location(self, pc):
        pos = self.instr_positions[pc]
        return self.__convert_offset_to_line_column(pos)

    def __convert_offset_to_line_column(self, pos):
        ret = {}
        ret['begin'] = None
        ret['end'] = None
        if pos['begin'] >= 0 and (pos['end'] - pos['begin'] + 1) >= 0:
            ret['begin'] = self.__convert_from_char_pos(pos['begin'])
            ret['end'] = self.__convert_from_char_pos(pos['end'])
        return ret

    def __convert_from_char_pos(self, pos):
        line = self.__find_lower_bound(pos, self.source.line_break_positions)
        if self.source.line_break_positions[line] != pos:
            line += 1
        begin_col = 0 if line == 0 else self.source.line_break_positions[line - 1] + 1
        col = pos - begin_col
        return {'line': line, 'column': col}

    def __find_lower_bound(self, target, array):
        start = 0
        length = len(array)
        while length > 0:
            half = length >> 1
            middle = start + half
            if array[middle] <= target:
                length = length - 1 - half
                start = middle + 1
            else:
                length = half
        return start - 1

    def __get_filename(self):
        return self.cname.split(":")[0]
