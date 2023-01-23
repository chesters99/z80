# RC2014 SC126 Z80 Bus Controller
# Graham Chester Jan-2023

import sys, re
from collections import OrderedDict
from micropython import const
#import buscontrol

# MCP23S17 configuraton
MCP23S17_bank = {
    'ADDR_BUS_LO' :{'chip':0, 'bank':0, 'mask': 0b11111111},
    'ADDR_BUS_HI' :{'chip':0, 'bank':1, 'mask': 0b11111111},
    'DATA_BUS'    :{'chip':1, 'bank':0, 'mask': 0b11111111},
    
    'BUSRQ':{'chip':1, 'bank':1, 'mask': 0b00000001},
    'BUSAK':{'chip':1, 'bank':1, 'mask': 0b00000010},
    'WAIT' :{'chip':1, 'bank':1, 'mask': 0b00000100},
    'M1'   :{'chip':1, 'bank':1, 'mask': 0b00001000},
    'MREQ' :{'chip':1, 'bank':1, 'mask': 0b00010000},
    'IOREQ':{'chip':1, 'bank':1, 'mask': 0b00100000},
    'RD'   :{'chip':1, 'bank':1, 'mask': 0b01000000},
    'WR'   :{'chip':1, 'bank':1, 'mask': 0b10000000},
    
    'RESET':{'chip':2, 'bank':0, 'mask': 0b00000001},
    'INT'  :{'chip':2, 'bank':0, 'mask': 0b00000010},
    'NMI'  :{'chip':2, 'bank':0, 'mask': 0b00000100},
    'HALT' :{'chip':2, 'bank':0, 'mask': 0b00001000},
    'TX'   :{'chip':2, 'bank':0, 'mask': 0b00010000},
    'RX'   :{'chip':2, 'bank':0, 'mask': 0b00100000},
    'TX2'  :{'chip':2, 'bank':0, 'mask': 0b01000000},
    'RX2'  :{'chip':2, 'bank':0, 'mask': 0b10000000},
    
    'USER1':{'chip':2, 'bank':1, 'mask': 0b00000001},
    'USER2':{'chip':2, 'bank':1, 'mask': 0b00000010},
    'USER3':{'chip':2, 'bank':1, 'mask': 0b00000100},
    'USER4':{'chip':2, 'bank':1, 'mask': 0b00001000},
    'USER5':{'chip':2, 'bank':1, 'mask': 0b00010000},
    'USER6':{'chip':2, 'bank':1, 'mask': 0b00100000},
    'USER7':{'chip':2, 'bank':1, 'mask': 0b01000000},
    'USER8':{'chip':2, 'bank':1, 'mask': 0b10000000},}

    
class MCP23S17:
    def __init__(self, qwe):
        # TODO
        pass


class Buscontrol:
    def __init__(self, debug):
        self.debug = debug
        self.got_bus = False
        # TODO
         
    def read_loc(self, address):
        # TODO
        from random import randint
        return randint(0, 255)

    def write_loc(self, address, data):
        # TODO
        pass
    
    def reset_z80(self):
        # TODO
        pass
    
    def grab_bus(self, option):
        # TODO
        pass
        



def read_mem(options):
    if len(options) == 0:
        raise ValueError("format is 'rd' <start_address> <length (optional)>'")
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
    if not bus.got_bus:
        bus.grab_bus()
    if len(options) < 2:
        raise ValueError("format is 'wd' <address> <byte> ...")
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
    bus.release_bus()
    
def read_io(options):
    if len(options) == 0:
        raise ValueError("format is 'ri' <start_address> <length (optional)>'")
    # TODO writes to Z80 IO device
    pass

def write_io(options):
    if not bus.got_bus:
        bus.grab_bus()
    # TODO writes to Z80 IO device
    bus.release_bus()
    pass

def read_ctrl(options):
    # TODO reads entire control bus
    pass

def set_ctrl(options):
    # TODO write one bit to the control bus
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
            'rd': {'desc':'read from ',              'params': '<start_address> <num of bytes(optional)>', 'function': read_mem  },
            'wd': {'desc':'write  to ',              'params': '<start_address> <value> ...',              'function': write_mem },
            'ri': {'desc':'read i/o port',           'params': '<i/o address>',                            'function': read_io   },
            'wi': {'desc':'write i/o port',          'params': '<i/o address> <data>...',                  'function': write_io  },
            'z':  {'desc':'put z80 into wait state', 'params': 'no params',                                'function', wait_state},
            's':  {'single step mode', single_step, ],
            'x': ['reset Z80',reset, ],
            'h': ['this help menu', help, ],
            'q': ['quit', sys.exit, ]})


bus = Buscontrol(debug=False);
if bus.debug:
    print('debug mode on')

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
