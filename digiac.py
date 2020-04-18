#!/usr/bin/python3
"digiac.py - Class that emulates a Digiac 3080"

#   Copyright (C) 2020 Robert N. Evans
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

from array import array
from random import seed, randrange
from time import sleep

try:
    from readchar import readchar
except ImportError:
    exit('You must install the PyPI package "readchar" to use this package.')


def _ta_char(c):
    "ASCII to output for a 6-bit digiac character code during Type Alpha"
    return (
        #  00000000111111112222222233333333 4 444444455555555   6666666677777777
        #  01234567012345670123456701234567 0 123456701234567   0123456701234567
        """0123456789-;/!'= ABCDEFGHIJKLM,\n\tNOPQRSTUVWXYZ.\x00)±@#$% &*(_:?°"+"""
    )[c]


class Digiac3080:
    "Emulate the Digiac-3080 computer system"

    def __init__(self):
        "create a virtual Digiac 3080"
        # randomly populate memory
        seed()
        self.mem = array("L")  # , b'\x00' * 4096)
        for addr in range(4096):
            sgn = randrange(2) << 24
            val = randrange(1 << 24)
            self.mem.append(sgn + val)
        self.pc = 0
        self.a = (0, 0)  # positive zero
        self.b = (0, 0)
        self.instruction_count = 0
        self.ips = 60  # instructions per second
        self.ptp = None  # file handle for tape reader
        self.ptr = None  # file handle for tape punch
        self.bpt = []  # execution breakpoints
        self.acs = []  # address compare stop addresses
        self.run = True  # advise to caller: whether CPU should run or stop
        self._opcode = 0
        self._count = 0
        self._addr = 0

    def reg_str(self, letter, sgn, val):
        "format contents of a register"
        s = (letter + ": ") if letter else ""
        s += "-" if sgn else "+"
        return f"{s}{val:08o}"

    @property
    def areg_str(self):
        "format the A register"
        return self.reg_str("A", self.a[0], self.a[1])

    @property
    def breg_str(self):
        "format the B register"
        return self.reg_str("B", self.b[0], self.b[1])

    def __str__(self):
        "format object for printing"
        instr = self.rm(self.pc) & 0x00FFFFFF
        s = (
            f"Digiac< PC: {self.pc:04o}->{instr:08o} {self.areg_str} "
            + f"{self.breg_str} Icnt: {self.instruction_count} IPS: {self.ips}"
        )
        if self.bpt:
            s += " bpt"
            for b in sorted(self.bpt):
                s += f":{b:04o}"
        if self.acs:
            s += " acs"
            for b in sorted(self.acs):
                s += f":{b:04o}"
        return s + ">"

    def rm(self, addr):
        "read a word from the memory array of 32-bit words"
        if addr in self.acs:
            print(f"Read Memory address Compare Stop @ {addr:04o}")
            self.run = False
        return self.mem[addr]

    def wm(self, addr, val):
        "write to memory array of 32-bit words"
        if addr in self.acs:
            print(f"Write Memory address Compare Stop @ {addr:04o}")
            self.run = False
        self.mem[addr] = val

    def _shift(self, val):
        "shift arguments during load/store"
        if self._count & 0o40:
            val >>= 0o100 - self._count
        else:
            val <<= self._count
        return val & 0x00FFFFFF

    def _sign(self, s):
        "set the argument sign during load/store"
        sgn = 1 if s else 0
        if self._opcode & 3 == 1:
            sgn = 1 - sgn  # negate the value
        elif self._opcode & 3 == 2:
            sgn = 0  # absolute value
        elif self._opcode & 3 == 3:
            sgn = 1  # minus absolute value
        return sgn

    def _arg_fetch(self):
        "fetch arithmetic argument from memory to a sign+magnitude register"
        wd = self.rm(self._addr)
        return self._sign(wd & 0xFF000000), self._shift(wd & 0x00FFFFFF)

    def _store_reg(self, addr, reg):
        "store a register into memory"
        sgn = self._sign(reg[0])
        val = self._shift(reg[1])
        self.wm(addr, (sgn << 24) + val)
        sval = self.reg_str("", sgn, val)
        return f"[{addr:04o}] <- {sval}"

    def exec(self):
        "execute one instruction"

        # NOTE: Breakpoints stop the CPU before instruction executes
        pc = self.pc
        if pc in self.bpt:
            self.run = False
            return f"Breakpoint at {pc:04o}"

        if self.ips:  # throttle to realistic speed
            sleep(1 / self.ips)
        instr = self.rm(pc)  # fetch instruction
        self.pc = (self.pc + 1) % 4096  # increment PC
        self.instruction_count += 1

        # decode instruction
        self._opcode = (instr >> 18) & 0o77
        self._count = (instr >> 12) & 0o77
        self._addr = (instr) & 0o7777

        # Execute / emulate known opcodes
        try:
            impl = self._implemented_instructions[self._opcode]
        except KeyError:
            self.run = False
            rc = f"Invalid or Unknown OPCODE {instr:08o} at {pc:04o}"
        else:
            rc = impl(self)
        return rc

    def _inst_hlt(self):
        "HLT"
        self.run = False
        return f"HALTED at {self.pc:04o}"

    def _inst_and(self):
        "AND"
        sgn, val = self._arg_fetch()
        sgn = self.a[0] if sgn else 0
        val &= self.a[1]
        self.a = (sgn, val)
        return "A      <- " + self.reg_str("", sgn, val)

    def _inst_cla(self):
        "CLA/CLS"
        sgn, val = self._arg_fetch()
        self.a = (sgn, val)
        return "A      <- " + self.reg_str("", sgn, val)

    def _inst_add(self):
        "ADD/SUB"
        sgn, val = self.a  # fetch prior A reg content
        accum = val if not sgn else -val
        sgn, val = self._arg_fetch()
        accum += val if not sgn else -val
        sgn = 1 if accum < 0 else 0
        accum = (-accum if sgn else accum) & 0x00FFFFFF
        self.a = (sgn, accum)
        return "A      <- " + self.reg_str("", sgn, accum)

    def _inst_mlt(self):
        "MLT"
        s, val = self.a  # fetch prior A reg content
        accum = int(val)
        sgn, val = self._arg_fetch()
        accum *= int(val)
        sgn = 0 if bool(s) == bool(sgn) else 1
        a = accum >> 24 & 0x00FFFFFF
        b = accum & 0x00FFFFFF
        self.a = (sgn, a)
        self.b = (sgn, b)
        return f'AB: {"-" if sgn else "+"}{a:08o} {b:08o}'

    def _inst_div(self):
        "DIV"
        sd, dividend = self.a
        sv, divisor = self._arg_fetch()
        sgn = 0 if bool(sd) == bool(sv) else 1
        try:
            divdd = dividend << 24
            quot = divdd // divisor & 0x00FFFFFF
            remd = divdd % divisor & 0x00FFFFFF
        except ZeroDivisionError:
            # FIXME I think 3080 did not halt.
            rc = f"Divide by Zero Stop"
            self.run = False
        else:
            a, b = remd, quot
            self.a = (sgn, a)
            self.b = (sgn, b)
            rc = f'AB: {"-" if sgn else "+"}{a:08o} {b:08o}'
        return rc

    def _inst_sta(self):
        "STA"
        return self._store_reg(self._addr, self.a)

    def _inst_stb(self):
        "STB"
        return self._store_reg(self._addr, self.b)

    def _inst_jmp(self):
        "JMP"
        self.pc = self._addr
        return f"PC     <-      {self.pc:04o}"

    def _inst_br_minus(self):
        "BR-"
        sgn, val = self.a
        return self._inst_jmp() if sgn and val else "no branch"

    def _inst_br_plus(self):
        "BR+"
        sgn, val = self.a
        return self._inst_jmp() if not sgn and val else "no branch"

    def _inst_brz(self):
        "BRZ"
        val = self.a[1]
        return "no branch" if val else self._inst_jmp()

    def _inst_ta(self):
        "TA - Type Alpha"
        buf = ""
        for idx in range((0o100 - self._count) * 4):  # 4 chars per word
            if not idx % 4:
                wd = self.rm(self._addr)  # fetch word
                self._addr = self._addr + 1 & 0o7777
            c = wd >> 18 & 0o77
            wd <<= 6
            if c != 0o66:  # 'BLANK' does not print anything
                buf += _ta_char(c)
        print(buf, end="", flush=True)
        return f"next addr:     {self._addr:04o}"

    def _do_rt(self):
        "read one word from paper tape"
        num_cols = 4
        sgn = None
        val = 0
        while num_cols > 0:
            c = self.ptr.read(1)
            if len(c) == 0:
                self.ptr.close()
                self.ptr = None
                raise EOFError(f"Reading PT beyond EOF")
            c = c[0]
            if c > 64:
                msg = f"Unexpected PT character = 0x{c:02X} at offset {self.ptr.tell()}"
                raise RuntimeError(msg)
            if c == 0:
                continue  # ignore blank leader
            if c == 64:
                c = 0  # non-blank zero value
            if sgn is None:
                sgn = 0x1000000 if c else 0
            else:
                val = val * 0o100 + c
                num_cols -= 1
        return sgn + val

    def _inst_rt(self):
        "RT - Read Tape"
        if self.ptr:
            for idx in range(0o100 - self._count):
                try:
                    self.wm(self._addr, self._do_rt())
                    self._addr = (self._addr + 1) & 0o7777
                except EOFError:
                    break  # stop reading @ EOT
                except RuntimeError as e:
                    print(e)
                    self.run = False
                    break  # stop reading @ invalid character
            rc = f"next addr:     {self._addr:04o}"
        else:
            self.run = False
            rc = f"No Tape in PTReader"
        return rc

    # fmt: off
    # Equivalent Digiac character code for ASCII read by the Type In instruction
    _tichars = {
        "0": 0,  "1": 1,  "2": 2,  "3": 3,  "4": 4,  "5": 5,  "6": 6,  "7": 7,
        "8": 8,  "9": 9,  "-": 10, ";": 11, "/": 12, "!": 13, "'": 14, "=": 15,
        " ": 16, "A": 17, "B": 18, "C": 19, "D": 20, "E": 21, "F": 22, "G": 23,
        "H": 24, "I": 25, "J": 26, "K": 27, "L": 28, "M": 29, ",": 30, "\n": 31,
        "\t": 32,"N": 33, "O": 34, "P": 35, "Q": 36, "R": 37, "S": 38, "T": 39,
        "U": 40, "V": 41, "W": 42, "X": 43, "Y": 44, "Z": 45, ".": 46, "\x00": 47,
        ")": 48, "±": 49, "@": 50, "#": 51, "$": 52, "%": 53, "¢": 54, "&": 55,
        "*": 56, "(": 57, "_": 58, ":": 59, "?": 60, "°": 61, '"': 62, "+": 63,
    }
    # fmt: on

    def _ti_char(self):
        "Read one typed in character and return the matching digiac character code"
        while True:
            c = readchar().upper()
            if ord(c) == 3:
                raise KeyboardInterrupt()  # Control-C
            if c in self._tichars:
                print(c, sep="", end="", flush=True)  # echo the typed character
                return self._tichars[c]
            print("\a", sep="", end="", flush=True)  # ring bell for invalid character

    def _inst_ti(self):
        "TI - Type In"
        wd = 0
        for idx in range((0o100 - self._count) * 4):
            wd = wd << 6 | self._ti_char()
            if idx % 4 == 3:
                self.wm(self._addr, wd)
                self._addr = self._addr + 1 & 0o7777
                wd = 0
        return f"next addr:     {self._addr:04o}"

    _implemented_instructions = {
        0o00: _inst_hlt,  # HLT
        0o04: _inst_and,  # AND
        0o05: _inst_and,
        0o06: _inst_and,
        0o07: _inst_and,
        0o10: _inst_cla,  # CLA
        0o11: _inst_cla,  # CLS
        0o12: _inst_cla,
        0o13: _inst_cla,
        0o14: _inst_add,  # ADD
        0o15: _inst_add,  # SUB
        0o16: _inst_add,
        0o17: _inst_add,
        0o20: _inst_mlt,  # MLT
        0o21: _inst_mlt,
        0o22: _inst_mlt,
        0o23: _inst_mlt,
        0o24: _inst_div,  # DIV
        0o25: _inst_div,
        0o26: _inst_div,
        0o27: _inst_div,
        0o30: _inst_sta,  # STA
        0o31: _inst_sta,
        0o32: _inst_sta,
        0o33: _inst_sta,
        0o34: _inst_stb,  # STB
        0o35: _inst_stb,
        0o36: _inst_stb,
        0o37: _inst_stb,
        0o44: _inst_jmp,  # JMP
        0o45: _inst_br_minus,  # BR+
        0o46: _inst_br_plus,  # BR-
        0o47: _inst_brz,  # BRZ
        # 0o50 TO - Type Octal (not implemented)
        0o54: _inst_ta,  # TA - Type Alpha
        0o60: _inst_rt,  # RT - Read Tape
        # 0o62 RC - Read Card (not implemented)
        0o63: _inst_ti,  # TI - Type In
        # 0o64 PT - Punch Tape (not implemented)
    }
