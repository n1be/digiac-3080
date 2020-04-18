#!/usr/bin/python3
"sim3080.py - User interface for control of the Digiac-3080 emulator"

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

from cmd import Cmd
from pdb import set_trace
from digiac import Digiac3080

d = Digiac3080()

# for examine as characters
def _chars(word):
    "Printable characters or '.' for a register or momory word"
    #        0000000011111111222222223333333344444444555555556666666677777777
    #        0123456701234567012345670123456701234567012345670123456701234567
    abc = """0123456789-;/!'= ABCDEFGHIJKLM,..NOPQRSTUVWXYZ..)±@#$%¢&*(_:?°"+"""
    result = ""
    while len(result) < 4:
        result += abc[word >> 18 & 0o77]
        word <<= 6
    return result


class SimShell(Cmd):
    "command line interpreter"
    intro = "Welcome to the Digiac-3080.  Type help or ? to list commands.\n"
    prompt = "Dg> "
    use_rawinput = False
    digi_known_devices = ("ptr",)
    digi_known_registers = ("a", "b", "pc")
    digi_trace = 0  # bitmask?

    def emptyline(self):
        "Override default repeat of prior command on empty input line"
        return None

    def precmd(self, line):
        ls = line.split()
        return ls[0].lower() + " " + (" ".join(ls[1:])) if ls else ""

    def do_pdb(self, arg):
        "Enter thhe Python DeBugger"
        set_trace()

    # ----- Exiting from the emulator -----
    def do_eof(self, arg):
        "Quit/Exit from the emulator: ^D"
        return self.do_quit(arg)

    def do_q(self, arg):
        "Quit/Exit from the emulator: Q"
        return self.do_quit(arg)

    def do_quit(self, arg):
        "Quit/Exit from the emulator: QUIT"
        if d.ptp:
            d.ptp.close()
            d.ptp = None
        if d.ptr:
            d.ptr.close()
            d.ptr = None
        return True

    # ----- Emulated device control -----
    def do_attach(self, arg):
        "Attach file to device: ATTACH PTR <filepath>"
        args = arg.split()
        if len(args) != 2:
            print("Two arguments must be provided")
        elif args[0].lower() not in self.digi_known_devices:
            print(f"Unknown device: {args[0]}")
        else:  # FIXME needs expansion to handle multiple devices ...
            if d.ptr:
                d.ptr.close()
            try:
                d.ptr = open(args[1], "rb")
            except OSError as e:
                d.ptr = None
                print(e)

    def do_detach(self, arg):
        "Detach file from a device: DETACH [PTP|PTR]"
        args = arg.split()
        if len(args) != 1:
            print("One argument must be provided")
        elif args[0].lower() not in self.digi_known_devices:
            print(f"Unknown device: {args[0]}")
        else:  # FIXME needs expansion to handle multiple devices ...
            if d.ptr:
                d.ptr.close()
            d.ptr = None

    # ----- Memory Access -----
    def do_e(self, arg):
        "Examine memory or register: E A|B|PC|####"
        return self.do_examine(arg)

    def do_examine(self, arg):
        "Examine memory or register: EXAMINE A|B|PC|####"
        args = arg.split()
        if len(args) != 1:
            print("One argument must be provided")
            return
        adr = args[0].lower()
        if adr == "a":
            print(d.areg_str, _chars(d.a[1]))
        elif adr == "b":
            print(d.breg_str, _chars(d.b[1]))
        elif adr == "pc":
            print(f"PC: {d.pc:04o}")
        else:
            try:
                addr = int(args[0], 8)
                assert 0 <= addr <= 0o7777
            except:
                print(f'invalid address "{args[0]}"')
                return
            wd = d.rm(addr)
            val_str = d.reg_str(None, wd & 0xFF000000, wd & 0x00FFFFFF)
            print(f"{addr:04o}: {val_str} {_chars(wd)}")

    def do_d(self, arg):
        "Store a value in memory or reg: D A|B|PC|#### -12345670"
        return self.do_deposit(arg)

    def do_deposit(self, arg):
        "Store a value in memory or reg: DEPOSIT A|B|PC|#### -12345670"
        args = arg.split()
        if len(args) != 2:
            print("Two arguments must be provided")
            return
        try:
            sgn = 1 if args[1].startswith("-") else 0
            val = int(args[1], 8)
            assert -0x1000000 < val < 0x1000000
            if args[0] == "pc":
                assert 0 <= val <= 0o7777
                assert sgn == 0
            elif val < 0:
                # convert to sign and magnitude
                sgn = 1
                val = (~val + 1) & 0x00FFFFFF
        except:
            print(f'invalid data value "{args[1]}"')
            return
        adr = args[0].lower()
        if adr == "a":
            d.a = (sgn, val)
        elif adr == "b":
            d.b = (sgn, val)
        elif adr == "pc":
            d.pc = val
        else:
            try:
                addr = int(args[0], 8)
                assert 0 <= addr <= 0o7777
            except:
                print(f'invalid address "{args[0]}"')
                return
            wd = (sgn << 24) | val
            d.wm(addr, wd)

    # ----- Instruction Execution -----
    def run_virtual_machine(self, num_instr=None):
        "Loop executing emulated instructions"
        instr_cnt = 0
        d.run = True
        if d.pc in d.bpt:  # continuing from a BPT
            held_bpt = d.pc
            d.bpt.remove(held_bpt)
        else:
            held_bpt = None
        while d.run:
            pc = d.pc
            inst = d.rm(pc)
            try:
                result = d.exec()
                instr_cnt += 1
            except KeyboardInterrupt:
                d.run = False
                result = "Control-C"
            if held_bpt is not None:
                d.bpt.append(held_bpt)
                held_bpt = None
            if (num_instr is not None) and (instr_cnt >= num_instr):
                if num_instr > 1:
                    print(f"Instruction count {instr_cnt} reached")
                d.run = False
            if self.digi_trace & 1:
                print(f"{d.instruction_count: 5d}  {pc:04o}: {inst:08o} .. {result}")
        if not self.digi_trace & 1:
            print(f"{d.instruction_count: 5d}  {pc:04o}: {inst:08o} .. {result}")

    def do_s(self, arg):
        "Execute 1 or # instructions: S [#instr]"
        return self.do_step(arg)

    def do_step(self, arg):
        "Execute 1 or # instructions: STEP [#instr]"
        args = arg.split()
        if args:
            try:
                steps = int(args[0])
                assert steps > 0
            except:
                print(f'Invalid number of instructions: "{args[0]}"')
                return
        else:
            steps = 1
        self.run_virtual_machine(num_instr=steps)

    def do_g(self, arg):
        "Start or continue execution: G [addr]"
        return self.do_go(arg)

    def do_go(self, arg):
        "Start or continue instruction execution: GO [addr]"
        args = arg.split()
        if args:
            try:
                addr = int(args[0], 8)
                assert 0 <= addr <= 0o7777
            except:
                print(f'Invalid address: "{args[0]}"')
                return
            d.pc = addr
        self.run_virtual_machine()

    def do_throttle(self, arg):
        "Limit execution speed to given ips: THROTTLE [ips] (default=60 IPS, zero=no throttle)"
        args = arg.split()
        if args:
            try:
                ips = int(args[0])
                assert ips >= 0
                d.ips = ips
            except:
                print(f'Invalid # instructions per second: "{args[0]}"')
        else:
            print(f"{d.ips} Instr/sec" if d.ips else "not throttled")

    def do_trace(self, arg):
        "Set/clear tracing opions: TRACE 0|1"
        args = arg.split()
        if args:
            try:
                tflags = int(args[0])
                assert tflags >= 0
                self.digi_trace = tflags
            except:
                print(f'Invalid trace flags: "{args[0]}"')
        else:
            print(f"trace flags: {self.digi_trace:02X}h")

    # ----- Breakpoints -----
    def do_break(self, arg):
        "Set breakpoint at addr: BREAK [1234]"
        args = arg.split()
        if args:
            try:
                addr = int(args[0], 8)
                assert 0 <= addr <= 0o7777
            except:
                print(f'Invalid address: "{args[0]}"')
                return
            if addr not in d.bpt:
                d.bpt.append(addr)
        else:
            bpts = " ".join(map(lambda x: f"{x:04o}", sorted(d.bpt))) if d.bpt else None
            print(f"Breakpoints: {bpts}")

    def do_clear(self, arg):
        "Clear breakpoint at addr: CLEAR 1234"
        args = arg.split()
        if len(args) == 1:
            try:
                addr = int(args[0], 8)
                assert 0 <= addr <= 0o7777
            except:
                print(f'Invalid address: "{args[0]}"')
                return
            if addr in d.bpt:
                d.bpt.remove(addr)
        else:
            print(f"Missing address of breakpoint to clear")

    def do_acstop(self, arg):
        "Set an address compare stop addr: ACSTOP <addr>"
        args = arg.split()
        if args:
            try:
                addr = int(args[0], 8)
                assert 0 <= addr <= 0o7777
            except:
                print(f'Invalid address: "{args[0]}"')
                return
            if addr not in d.acs:
                d.acs.append(addr)
        else:
            acss = " ".join(map(lambda x: f"{x:04o}", sorted(d.acs))) if d.acs else None
            print(f"Address Compare Stops: {acss}")

    def do_aclear(self, arg):
        "Clear an address compare stop addr: ACLEAR <addr>"
        args = arg.split()
        if len(args) == 1:
            try:
                addr = int(args[0], 8)
                assert 0 <= addr <= 0o7777
            except:
                print(f'Invalid address: "{args[0]}"')
                return
            if addr in d.acs:
                d.acs.remove(addr)
        else:
            print(f"Missing address of Address Compare Stop to clear")

    def do_status(self, arg):
        "Show emulator status: STATUS"
        print(d)


if __name__ == "__main__":
    SimShell().cmdloop()
