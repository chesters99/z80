# RC2014 SC126 Z80 Bus Controller
# Graham Chester Jan-2023

import sys, re
#import buscontrol
from random import randint
from collections import OrderedDict
from micropython import const

# address of MCP23S17
CTRL_ADDR = const(0)
ADDR_ADDR = const(1)
DATA_ADDR = const(2)

# control bus pins from ctrl MCP23S17
BUSRQ = const(0xFF)
BUSAK = const(0xFF)
WAIT  = const(0xFF)
M1    = const(0xFF)
MREQ  = const(0xFF)
IOREQ = const(0xFF)
WR    = const(0xFF)
RD    = const(0xFF)
RESET = const(0xFF)
INT   = const(0xFF)
NMI   = const(0xFF)
HALT  = const(0xFF)
TX    = const(0xFF)
RX    = const(0xFF)
TX2   = const(0xFF)
RX2   = const(0xFF)

# control bus pins from data MCP23S17
USER1 = const(0xFF)
USER2 = const(0xFF)
USER3 = const(0xFF)
USER4 = const(0xFF)
USER5 = const(0xFF)
USER6 = const(0xFF)
USER7 = const(0xFF)
USER8 = const(0xFF)









class MCP23S17:
    def __init__(self, qwe):
        # TODO
        pass


class Buscontrol:
    def __init__(self, debug):
        self.ctrl = MCP23S17(CTRL_ADDR)
        self.addr = MCP23S17(1)
        self.data = MCP23S17(2)
        self.debug = debug
        if debug:
            print('debug mode on')
        # TODO
         
    def read_loc(self, address):
        # TODO
        return randint(0, 255)

    def write_loc(self, address, data):
        # TODO
        pass
    def reset_z80(self):
        # TODO
        pass



def read_mem(options):
    if len(options) == 0:
        raise ValueError("format is 'r' <start_address> <length (optional)>'")
    start  = int(options[0])
    length = 1 if len(options) == 1 else int(options[1])

    bytes_per_line = const(16)
    if length < bytes_per_line: # print single column if not too much to dump else print 16 on a line
        for i, address in enumerate(range(start, start+length)):
            val = bus.read_loc(address)
            print("{:04X} {:02X} {:s}".format(address, val, chr(val if 0x20 <= val <= 0x7E  else 0x2E) ))
    else:
        data = []
        length = ((length + 15) & (-16)) # round bytes to display up to next multiple of 16
        for i,address in enumerate(range(start, start+length)):
            data.append( bus.read_loc(address) )
            if (i+1) % bytes_per_line == 0 and i > 0:                
                print('{:04X} '.format(start + i-bytes_per_line+1),
                      ''.join(['{:02X} '.format(val) for val in data]),
                      ''.join([chr(val if 0x20 <= val <= 0x7E  else 0x2E) for val in data]) )
                data = []
            

def write_mem(options):
    if len(options) < 2:
        raise ValueError("format is 'w' <address> <byte> ...")
    start_address = int(options[0])
    if start_address < 0 or start_address + len(options[1:]) > 65536:
        raise ValueError('address less than zero or address + data length > 655536')
    data = [int(i) for i in options[1:]]
    if min(data) < 0 or max(data) > 255:
        raise ValueError('byte value outside 0 to 255')
    
    print('writing memory address 0x{:04X}: '.format(start_address), end='')
    for i, value in enumerate(data):
        bus.write_loc(start_address+i, value)
        print('0x{:02X} '.format(value), end='')
    print()

def read_ctrl(options):
    // TODO reads entire control bus
    pass

def set_ctrl(options):
    // TODO write one bit to the control bus
    pass

def reset(options):
    if len(options) == 0 or len(options) > 1 or options[0] !='confirm':
        raise ValueError("format is 'x confirm' to reset Z80")
    print('resetting z80')
    bus.reset_z80()

def help(options):
    for command in commands.items():
        print(command[0], command[1][0])
        

# Main Processing
commands = OrderedDict({
            'r': ['read from location X, Y bytes', read_mem, ],
            'w': ['write  to location X, Y bytes', write_mem, ],
            'z': ['Z80 wait mode', wait, ],
            's': ['single step from address', single_step, ],
            'x': ['reset Z80',reset, ],
            'h': ['this help menu', help, ],
            'q': ['quit', sys.exit, ]})


bus = Buscontrol(debug=False);

while True:
    user_input = input('Enter command (h for help): ').lower().split()
    command = user_input[0] if len(user_input) > 0 else None
    if command not in commands:
        print('invalid command, enter h for help')
        continue
    
    function = commands[command][1]
    try:
        function(user_input[1:])
    except ValueError as e:
        print(e)
