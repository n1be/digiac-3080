# Digiac-3080

The [Digiac-3080](https://digiac3080.wordpress.com/ "Extinct Computer Tribute Blog") was the first computer architecture I learned.  This simple slow machine with no interrupts or stack could still educate and entertain.  I saved one program, a Stock Market game, from those days and wrote an simulator to be able to run the game again.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

Minimally, you will need these software packages to run the code in this repository.
- **Python 3** - The Digiac simulator been tested with Python 3.7 on Ubuntu Linux.
- **readchar** - The _readchar_ package from the python package index is required.

### Installing

- Install python -- One usually can install the "python3" package via your package manager or app store.  If your operating system does not offer a python package, see [Python.org](https://www.python.org/)

- Install support for python virtual environments and fetching packages from the [Python Package Index](https://pypi.org/):
```
sudo apt install python3-venv
```

- Clone the repository.  If you do not have git installed, you can download a zip of the repository from github:
```
git clone https://github.com/n1be/digiac-3080.git
```

- Create a virtual environment inside the repository directory:
```
python3 -m venv digiac-3080/venv
```

- Enter the virtual environment:
```
cd digiac-3080
source venv/bin/activate
```

- Install dependencies
```
python -m pip install -r requirements.txt
```

Run the Digiac-3080 simulator.
```
python sim3080.py 
Welcome to the Digiac-3080.  Type help or ? to list commands.

Dg> help
Documented commands (type help <topic>):
========================================
aclear  clear    e        go      quit    throttle
acstop  d        eof      help    s       trace
attach  deposit  examine  pdb     status
break   detach   g        q       step

Dg> deposit 0 54750002
Dg> deposit 1 0
Dg> deposit 2 30253434
Dg> deposit 3 42205242
Dg> deposit 4 45342437
Dg> go 0
HELLO WORLD
    2  0001: 00000000 ..  HALTED at 0o0002
Dg> status
Digiac< PC: 0002->30253434 A: +00000000 B: +00000000 Icnt: 2 IPS: 60>
Dg> quit
```

### Documentation
These files explain the Digiac and how to run the simulator.
- **README.md** - Provides an overview of the project (this file).
- **Using the Digiac-3080 Simulator.pdf** - Explains the simulator and how to use it.
- **Digiac info.pdf** - Details of the Digiac-3080 machine architecture.
- **tape/papertape_info.pdf** - Explains the format of Digiac paper tapes.

### Programs
These programs are provided:
- **digiac.py** - The Digiac-3080 instruction set interpreter / CPU emulator.
- **sim3080.py** - The Digiac-3080 simulator.  It calls the emulator to run each digiac instruction.
- **tapedump.py** - A program to examine the content of .ptp (papertape) files.
- **tape/stok.ptp** - Stock Market Game paper tape.
- **tape/stok_no-randomize.ptp** - Unmodified Stock Market Game paper tape from Spring 1970.  (See papertape_info.pdf for more info.)

## License
Copyright (c) 2020 Robert N. Evans
Licensed under the [GNU General Public License (GPL)](https://opensource.org/licenses/GPL-3.0)

