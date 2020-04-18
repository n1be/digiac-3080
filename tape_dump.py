#!/usr/bin/python3
" tape_dump.py - Dump the contents of Digiac-3080 paper tape (.ptp) files"

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

from sys import argv


def ta_char(digi_code):
    "Printable character or '.' for Type Alpha/Type In"
    #          0000000011111111222222223333333344444444555555556666666677777777
    #          0123456701234567012345670123456701234567012345670123456701234567
    albet = """0123456789-;/!'= ABCDEFGHIJKLM,..NOPQRSTUVWXYZ..)±@#$%¢&*(_:?°"+"""
    return albet[digi_code]


try:
    FILES = argv[1:]
    if not FILES:
        exit("Supply the filename(s) to be dumped on the command line")
    for tape in FILES:
        print()
        buf = bytes(0)
        with open(tape, "rb") as f:
            b = True
            while b:
                b = f.read()
                buf += b
        ln = len(buf)
        print(f"File: {tape} raw data length: {ln}")
        while buf:
            addr = 0
            buf = buf.lstrip(b"\x00")
            l = ln - len(buf)
            if not buf:
                print(f"removed final {l} zero bytes")
                break
            print(
                f"""removed {l} leading zero bytes
  Addr    Octal    Char
  ====  ========   ===="""
            )
            while buf[0] != 0:
                assert buf[0] == 0x40, f'{buf[0]:02X}h =>> "-"?'
                assert buf[1] != 0, f" == {buf[1]}"
                assert buf[2] != 0, f" == {buf[2]}"
                assert buf[3] != 0, f" == {buf[3]}"
                assert buf[4] != 0, f" == {buf[4]}"
                b1 = buf[1] % 64
                b2 = buf[2] % 64
                b3 = buf[3] % 64
                b4 = buf[4] % 64
                c1 = ta_char(b1)
                c2 = ta_char(b2)
                c3 = ta_char(b3)
                c4 = ta_char(b4)
                wd = ((b1 * 64 + b2) * 64 + b3) * 64 + b4
                print(f". {addr:04o}  {wd:08o}   {c1}{c2}{c3}{c4}")
                addr += 1
                buf = buf[5:]
            ln = len(buf)
except BrokenPipeError:
    pass
