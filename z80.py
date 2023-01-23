# RC2014 SC126 Z80 Bus Controller
# Graham Chester Jan-2023

import sys, re
from collections import OrderedDict
from micropython import const
#import buscontrol

class MCP23S17:
    def __init__(self, debug):
        self.debug = False
        for chip in ALL_CHIPS:
            self.haen_enable(chip)
    
    def get(self, chip_addr, chip_bank):
        from random import randint
        return randint(0, 0xFF)
        # TODO how to get Pico to talk to MCP23S17

    def put(self, chip_addr, chip_bank, iodir, value):
        pass
        # TODO how to get Pico to talk to MCP23S17

    def reset_to_input(self, chip, bank):
        pass
        # TODO how to get Pico to talk to MCP23S17
    
    def haen_enable(self, chip_addr):
        HAEN_ENABLE = 0b00001000  # enable mcp23s17 hardware address pins
        # TODO complete hardware address enabling

class BusControl:  
    ADDR_CHIP = const(0) # MCP23S17 chip hardware addresses
    DATA_CHIP = const(1)
    CTRL_CHIP = const(2)
    ALL_CHIPS = (ADDR_CHIP, DATA_CHIP, CTRL_CHIP)

    DATA_CHIP_DATA_BANK = const(0) # MCP23S17 chip internal banks
    DATA_CHIP_CTRL_BANK = const(1)
    LO_CHIP_BANK        = const(0)
    HI_CHIP_BANK        = const(1)
    ALL_BANKS = (LO_CHIP_BANK, HI_CHIP_BANK)

    ACTIVE              = const(0) # Z80 ctrl lines are active low
    INACTIVE            = const(1)

    # MCP23S17 ctrl line configuraton
    MCP23S17 = OrderedDict({    
        'BUSRQ': {'chip_addr':1, 'chip_bank':1, 'bit': 0b00000001},
        'BUSAK': {'chip_addr':1, 'chip_bank':1, 'bit': 0b00000010},
        'WAIT' : {'chip_addr':1, 'chip_bank':1, 'bit': 0b00000100},
        'M1'   : {'chip_addr':1, 'chip_bank':1, 'bit': 0b00001000},
        'MREQ' : {'chip_addr':1, 'chip_bank':1, 'bit': 0b00010000},
        'IOREQ': {'chip_addr':1, 'chip_bank':1, 'bit': 0b00100000},
        'RD'   : {'chip_addr':1, 'chip_bank':1, 'bit': 0b01000000},
        'WR'   : {'chip_addr':1, 'chip_bank':1, 'bit': 0b10000000},
        
        'RESET': {'chip_addr':2, 'chip_bank':0, 'bit': 0b00000001},
        'HALT' : {'chip_addr':2, 'chip_bank':0, 'bit': 0b00000010},
        'INT'  : {'chip_addr':2, 'chip_bank':0, 'bit': 0b00000100},
        'NMI'  : {'chip_addr':2, 'chip_bank':0, 'bit': 0b00001000},
        'TX'   : {'chip_addr':2, 'chip_bank':0, 'bit': 0b00010000},
        'RX'   : {'chip_addr':2, 'chip_bank':0, 'bit': 0b00100000},
        'TX2'  : {'chip_addr':2, 'chip_bank':0, 'bit': 0b01000000},
        'RX2'  : {'chip_addr':2, 'chip_bank':0, 'bit': 0b10000000},
        
        'USER1': {'chip_addr':2, 'chip_bank':1, 'bit': 0b00000001},
        'USER2': {'chip_addr':2, 'chip_bank':1, 'bit': 0b00000010},
        'USER3': {'chip_addr':2, 'chip_bank':1, 'bit': 0b00000100},
        'USER4': {'chip_addr':2, 'chip_bank':1, 'bit': 0b00001000},
        'USER5': {'chip_addr':2, 'chip_bank':1, 'bit': 0b00010000},
        'USER6': {'chip_addr':2, 'chip_bank':1, 'bit': 0b00100000},
        'USER7': {'chip_addr':2, 'chip_bank':1, 'bit': 0b01000000},
        'USER8': {'chip_addr':2, 'chip_bank':1, 'bit': 0b10000000},})

    def __init__(self, debug):
        self.debug          = debug
        self.got_bus        = False
        self.single_step    = False
        self.save_ss_addresses = []
        self.mcp23s17 = MCP23S17(False)

    def reset_to_input(self, chips=None, banks=None):
        chips = list(chips) if chips else ALL_CHIPS
        banks = list(banks) if banks else ALL_BANKS
        for chip in chips:
            for bank in banks:
                self.mcp23s17.reset_to_input(chip, bank)

    def bus_control(self, option):
        if len(options) !=1 or option[0] not in ('grab','release'):
            raise ValueError('Can only grab or release bus')
        if self.got_bus:
            print('Warning: cant grab bus as already grabbed, no action taken')
            return
        
        self.mcp23s17.reset_to_input() # make totally sure, all chips banks are left in input mode
        if option[0] == 'grab':
            self.mcp23s17.put(MCP23S17['BUSRQ']['chip_addr'], MCP23S17['BUSRQ']['chip_bank'], MCP23S17_ctrl['BUSREQ']['bit'], ACTIVE)
            while self.mcp23s17.get(MCP23S17['BUSAK']['chip_addr'], MCP23S17['BUSAK']['chip_bank'], MCP23S17_ctrl['BUSAK']['bit']) != ACTIVE:
                print('waiting on BUSAK')
            self.got_bus = True
        elif if option[0] == 'release':
            self.mcp23s17.put(MCP23S17['BUSRQ']['chip_addr'], MCP23S17['BUSRQ']['chip_bank'], MCP23S17_ctrl['BUSREQ']['bit'], INACTIVE)
            self.got_bus = False
        self.mcp23s17.reset_to_input() # make totally sure, all chips banks are left in input mode

    def read_mem_address(self, address):
        if not self.got_bus:
            raise RunTimeException('Trying to access bus without BUSAK high') # protect against program bugs
        self.mcp23s17.put(ADDR_CHIP, ADDR_LO_CHIP_BANK, address & 0x00FF)
        self.mcp23s17.put(ADDR_CHIP, ADDR_HI_CHIP_BANK, address >> 8)
        self.mcp23s17.put(MCP23S17['RD'  ]['chip_addr'], MCP23S17['RD'  ]['chip_bank'], MCP23S17_ctrl['RD'  ]['bit'], ACTIVE)
        self.mcp23s17.put(MCP23S17['MREQ']['chip_addr'], MCP23S17['MREQ']['chip_bank'], MCP23S17_ctrl['MREQ']['bit'], ACTIVE)
        data = self.mcp23s17.get(DATA_CHIP, DATA_CHIP_BANK)
        self.mcp23s17.reset_to_input(MCP23S17['MREQ']['chip_addr'], MCP23S17['MREQ']['chip_bank']) # reset ctrl lines back to input
        return data

    def write_mem_address(self, address, data):
        if not self.got_bus:
            raise RunTimeException('Trying to access bus without BUSAK high') # protect against program bugs
        self.mcp23s17.put(ADDR_CHIP, ADDR_LO_CHIP_BANK, address & 0x00FF)
        self.mcp23s17.put(ADDR_CHIP, ADDR_HI_CHIP_BANK, address >> 8)
        self.mcp23s17.put(MCP23S17['WR'  ]['chip_addr'], MCP23S17['WR'  ]['chip_bank'], MCP23S17_ctrl['WR'  ]['bit'], ACTIVE)
        self.mcp23s17.put(MCP23S17['MREQ']['chip_addr'], MCP23S17['MREQ']['chip_bank'], MCP23S17_ctrl['MREQ']['bit'], ACTIVE)
        self.mcp23s17.put(DATA_CHIP, DATA_CHIP_BANK, data)
        self.mcp23s17.put(MCP23S17['MREQ']['chip_addr'], MCP23S17['MREQ']['chip_bank'], 0x00, 0) 
        self.mcp23s17.reset_to_input(MCP23S17['MREQ']['chip_addr'], MCP23S17['MREQ']['chip_bank']) # reset ctrl lines back to input

    def read_all_ctrl_lines(self):
        lookup = {'{:d}_{:d}_{:d}'.format(sig[1]['chip_addr'], sig[1]['chip_bank'], 7-'{:08b}'.format(sig[1]['bit']).find('1')): sig[0]  
                  for sig in MCP23S17.items()} # form lookup dict in the form {'chip_bank_signalbit': signalname, ...}
        signals = []
        for chip, bank in [(DATA_CHIP, DATA_CHIP_CTRL_BANK), (CTRL_CHIP, LO_CHIP_BANK), (CTRL_CHIP, HI_CHIP_BANK)]:
            byte = self.mcp23s17.get(chip, bank) 
            for bit in range(8):
                key = '{:d}_{:d}_{:d}'.format(chip, bank, bit)
                signal_name = lookup[key]
                signal_value = (byte >> bit) & 1
                signals.append([signal_name, signal_value])
        return signals 

    def reset_z80(self):
        if not self.got_bus:
            raise RunTimeException('Trying to access bus without BUSAK high') # protect against program bugs
        self.mcp23s17.put(MCP23S17['RESET']['chip_addr'], MCP23S17['RESET']['chip_bank'], MCP23S17_ctrl['RESET']['bit'], ACTIVE)
        self.mcp23s17.put(MCP23S17['RESET']['chip_addr'], MCP23S17['RESET']['chip_bank'], MCP23S17_ctrl['RESET']['bit'], INACTIVE)
        self.mcp23s17.reset_to_input(MCP23S17['RESET']['chip_addr'], MCP23S17['RESET']['chip_bank']) # reset ctrl lines back to input

    def single_step(single_step, address):
        # TODO single step is a total mess
        if single_step=='on':
            self.single_step = True
            self.grab_bus()
            
            self.save_buff[0] = bus.read_loc(0x0000)
            self.save_buff[1] = bus.read_loc(0x0001)
            self.save_buff[2] = bus.read_loc(0x0002)
            self.write_loc(0x0000, 0xC3)             # write jump instruction
            self.write_loc(0x0001, address & 0x00FF) # write jump address high byte
            self.write_loc(0x0002, address >> 8)     # write jump address low  byte
            self.reset_z80()
            self.wait_z80()
        elif single_step == 'off':
            pass
        else:
            print('invalid single step request, ignoring request'):


# start main functions
def read_memory(command, options):
    if len(options) not in (1,2):
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    start  = int(options[0])
    length = 1 if len(options) == 1 else int(options[1])

    bytes_per_line = const(16)
    bus.bus_control('grab')
    if length < bytes_per_line: # print single column if not too much to dump else print 16 on a line
        for i, address in enumerate(range(start, start+length)):
            val = bus.read_loc(address)
            print("{:04X} {:02X} {:s}".format(address, val, chr(val if 0x20 <= val <= 0x7E  else 0x2E) ))
    else:
        data = []
        length = ((length + 15) & (-16)) # round bytes to display up to next multiple of 16
        for i,address in enumerate(range(start, start+length)):
            data.append( bus.read_address(address) )
            if (i+1) % bytes_per_line == 0 and i > 0:                
                print('{:04X} '.format(start + i-bytes_per_line+1),
                      ''.join(['{:02X} '.format(val) for val in data]),
                      ''.join([chr(val if 0x20 <= val <= 0x7E  else 0x2E) for val in data]) )
                data = []
    bus.bus_control('release')
            
def write_memory(command, options):
    if len(options) < 2:
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    start_address = int(options[0])
    if start_address < 0 or start_address + len(options[1:]) > 65536:
        raise ValueError('address less than zero or address + data length > 655536')
    data = [int(i) for i in options[1:]]
    if min(data) < 0 or max(data) > 255:
        raise ValueError('byte value outside 0 to 255')
    
    bus.bus_control('grab')
    print('writing memory address 0x{:04X}: '.format(start_address), end='')
    for i, value in enumerate(data):
        bus.write_address(start_address+i, value)
        print('0x{:02X} '.format(value), end='')
    print()
    bus.bus_control('release')
    
def read_io(command, options):
    if len(options) != 1:
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    bus.bus_control('grab')
    # TODO read from Z80 IO device
    bus.bus_control('release')


def write_io(command, options):
    if len(options) < 2:
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    bus.bus_control('grab')
     # TODO write to Z80 IO device
    bus.bus_control('release')

def read_ctrl(command, options):
    if len(options) != 0:
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    # TODO reads entire control bus

def write_ctrl(command, options):
    if len(options) != 0:
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    # TODO write one bit to the control bus

def single_step(command, options):
    if not ((len(options) == 1 and options[0] == 'off') or (len(options) == 2 and options[0] == 'on')):
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    address = int(options[0])
    bus.single_step('on')
    while true:
        reply = input('press <enter> to step, x <enter> to run as normal')
        address = bus.get_address
        data = bus.read_loc(address)
        print('{:04X}: {:02X} '.format(address, data))
        address += 1
    bus.single_step('off')

def reset(command, options):
    if len(options) != 1 or options[0] !='confirm':
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    print('resetting z80')
    bus.reset_z80()

def help_menu(command, options):
    for command in commands.items():
        print(command[0], command[1]['desc'] + ' ' + command[1]['params'])
        

# Main Processing
commands = OrderedDict({
    'rd': {'desc': 'read from',               'params': '<start_address> <num of bytes(optional)>', 'function': read_mem    },
    'wd': {'desc': 'write  to',               'params': '<start_address> <value> ...',              'function': write_mem   },
    'ri': {'desc': 'read i/o port',           'params': '<i/o address>',                            'function': read_io     },
    'wi': {'desc': 'write i/o port',          'params': '<i/o address> <data>...',                  'function': write_io    },
    'rc': {'desc': 'read control bus',        'params': 'no params',                                'function': read_ctrl   },
    'wc': {'desc': 'write control line',      'params': '<control bit> = <0 or 1>',                 'function': write_ctrl  },
    'ss': {'desc': 'single step mode',        'params': '<on/off> <start address (for on only)>',   'function': single_step },
    'zw': {'desc': 'put z80 into wait state', 'params': 'no parameters',                            'function': wait_z80    },
    'zr': {'desc': 'halt Z80',                'params': 'no parameters',                            'function': halt_z80    },
    'zr': {'desc': 'reset Z80',               'params': '"confirm"',                                'function': reset_z80   },
    'h':  {'desc': 'this help menu',          'params': 'no parameters',                            'function': help_menu   },
    'q':  {'desc': 'quit program',            'params': 'no parameters',                            'function': sys.exit    }}

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
        function(command, user_input[1:])
    except ValueError as e:
        print(e)
