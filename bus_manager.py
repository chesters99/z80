from micropython import const
import time
from collections import OrderedDict
from mcp23s17_manager import MCP23S17s
from machine import Pin

class BusManager:  
    ACTIVE       = const(0) # Z80 ctrl lines are active low
    INACTIVE     = const(1)
    INACTIVE_ALL = const(0b11111111)
    ACTIVE_ALL   = const(0b00000000)
    
    RESET_PIN    = const(26)
    NMI_PIN      = const(27)
    INT_PIN      = const(28)
        
    # MCP23S17 ctrl line configuraton
    MCP = OrderedDict({
        'ADDR_LO' : {'addr':0, 'bank':0,'iodir': 0b11111111},
        'ADDR_HI' : {'addr':0, 'bank':1,'iodir': 0b11111111},
        'DATA'    : {'addr':1, 'bank':0,'iodir': 0b11111111},
        'CTRL'    : {'addr':1, 'bank':1,'iodir': 0b11111111},

        'BUSRQ': {'addr':1, 'bank':1, 'iodir': 0b11111110},
        'BUSAK': {'addr':1, 'bank':1, 'iodir': 0b11111101},
        'WAIT' : {'addr':1, 'bank':1, 'iodir': 0b11111011},
        'M1'   : {'addr':1, 'bank':1, 'iodir': 0b11110111},
        'MREQ' : {'addr':1, 'bank':1, 'iodir': 0b11101111},
        'IOREQ': {'addr':1, 'bank':1, 'iodir': 0b11011111},
        'RD'   : {'addr':1, 'bank':1, 'iodir': 0b10111111},
        'WR'   : {'addr':1, 'bank':1, 'iodir': 0b01111111},})


    def __init__(self, debug=False):
        self.debug          = debug
        self.got_bus        = False
        self.wait_state     = False
        self.single_step    = False
        self.mcp23s17s      = MCP23S17s(debug=debug)
        if self.debug:
            print('DEBUG: bus manager debug mode on')

    def bus_control(self, option):
        if option not in ('grab','release'):
            raise ValueError('Can only grab or release bus')
        
        if option == 'grab':
            if self.got_bus:
                print('Warning: cant grab bus as already grabbed, no action taken')
                return
            self.mcp23s17s.write_bus(self.MCP['BUSRQ']['addr'], self.MCP['BUSRQ']['bank'], self.ACTIVE_ALL, self.MCP['BUSRQ']['iodir'])
            self.got_bus = False
            for iteration in range(3):
                data = self.mcp23s17s.read_bus(self.MCP['BUSAK']['addr'], self.MCP['BUSAK']['bank']) 
                print('bing1 {:08b}'.format(data))
                data = data & (0b11111111 - self.MCP['BUSAK']['iodir'])
                print('bing2 {:08b}'.format(data))
                if data == self.ACTIVE:
                    self.got_bus = True
                    break
            
        elif option == 'release':
            self.mcp23s17s.write_bus(self.MCP['BUSRQ']['addr'], self.MCP['BUSRQ']['bank'], self.INACTIVE_ALL, self.MCP['BUSRQ']['iodir'])
            self.got_bus = False
        if self.debug:
            print('DEBUG: bus manager {} Z80 bus'.format(option))

    def read_memory(self, address):
        if not self.got_bus:
            raise RuntimeError('Trying to access bus without BUSAK low active') # protect against program bugs
        self.mcp23s17s.write_bus(self.MCP['ADDR_LO']['addr'], self.MCP['ADDR_LO']['bank'], address & 0x00FF, ACTIVE_ALL)
        self.mcp23s17s.write_bus(self.MCP['ADDR_HI']['addr'], self.MCP['ADDR_HI']['bank'], address >> 8,     ACTIVE_ALL)
        self.mcp23s17s.write_bus(self.MCP['RD'     ]['addr'], self.MCP['RD'     ]['bank'], self.ACTIVE_ALL, self.MCP['MREQ']['iodir'] & self.MCP['RD'  ]['iodir'])
        data = self.mcp23s17s.read_bus(self.MCP['DATA']['addr'], self.MCP['DATA']['bank'])
        input('read memory - press enter to continue')
        self.mcp23s17s.write_bus(self.MCP['ADDR_LO']['addr'], self.MCP['ADDR_LO']['bank'], 0xFF, INACTIVE_ALL)
        self.mcp23s17s.write_bus(self.MCP['ADDR_HI']['addr'], self.MCP['ADDR_HI']['bank'], 0xFF, INACTIVE_ALL)
        reset_mreq_rd = 0b11111111 - self.MCP['MREQ']['iodir'] & self.MCP['RD'  ]['iodir']
        self.mcp23s17s.write_bus(self.MCP['MREQ'   ]['addr'], self.MCP['MREQ']['bank'], reset_mreq_rd)
        return data

    def write_memory(self, address, data):
        if not self.got_bus:
            raise RuntimeError('Trying to access bus without BUSAK low active') # protect against program bugs
        self.mcp23s17s.write_bus(self.MCP['ADDR_LO']['addr'], self.MCP['ADDR_LO']['bank'], address & 0x00FF, ACTIVE_ALL)
        self.mcp23s17s.write_bus(self.MCP['ADDR_HI']['addr'], self.MCP['ADDR_HI']['bank'], address >> 8,     ACTIVE_ALL)
        self.mcp23s17s.write_bus(self.MCP['WR'     ]['addr'], self.MCP['WR'     ]['bank'],  self.ACTIVE_ALL, self.MCP['MREQ']['iodir'] & self.MCP['WR'  ]['iodir'])
        self.mcp23s17s.write_bus(self.MCP['DATA'   ]['addr'], self.MCP['DATA'   ]['bank'], data,     ACTIVE_ALL)
        input('read memory - press enter to continue')
        reset_mreq_rd = 0b11111111 - self.MCP['MREQ']['iodir'] & self.MCP['WR']['iodir']
        self.mcp23s17s.write_bus(self.MCP['MREQ'   ]['addr'], self.MCP['MREQ'   ]['bank'], reset_mreq_rd)
        self.mcp23s17s.write_bus(self.MCP['ADDR_LO']['addr'], self.MCP['ADDR_LO']['bank'], 0xFF, INACTIVE_ALL)
        self.mcp23s17s.write_bus(self.MCP['ADDR_HI']['addr'], self.MCP['ADDR_HI']['bank'], 0xFF, INACTIVE_ALL)
        self.mcp23s17s.write_bus(self.MCP['DATA'   ]['addr'], self.MCP['DATA'   ]['bank'], 0xFF, INACTIVE_ALL)


    def read_io(self, address):
        if not self.got_bus:
            raise RuntimeError('Trying to access bus without BUSAK high') # protect against program bugs
        self.mcp23s17s.write_bus(self.MCP['ADDR_LO']['addr'], self.MCP['ADDR_LO']['bank'], address & 0x00FF)
        self.mcp23s17s.write_bus(self.MCP['RD'     ]['addr'], self.MCP['RD'     ]['bank'],  self.ACTIVE_ALL, self.MCP['IOREQ']['iodir'] & self.MCP['RD'   ]['iodir'])
        data = self.mcp23s17s.read_bus(self.MCP['DATA']['addr'], self.MCP['DATA']['bank'])
        reset_ioreq_rd = 0b11111111 - self.MCP['IOREQ']['iodir'] & self.MCP['RD'  ]['iodir']
        self.mcp23s17s.write_bus(self.MCP['IOREQ'   ]['addr'], self.MCP['IOREQ']['bank'], reset_ioreq_rd)
        return data

    def write_io(self, address, data):
        if not self.got_bus:
            raise RuntimeError('Trying to access bus without BUSAK low active') # protect against program bugs
        self.mcp23s17s.write_bus(self.MCP['ADDR_LO']['addr'], self.MCP['ADDR_LO']['bank'], address & 0x00FF)
        self.mcp23s17s.write_bus(self.MCP['WR'  ]['addr'], self.MCP['WR'  ]['bank'], self.ACTIVE_ALL, self.MCP['IOREQ']['iodir'] & self.MCP['WR'  ]['iodir'])
        self.mcp23s17s.write_bus(self.MCP['DATA']['addr'], self.MCP['DATA']['bank'], data)
        reset_ioreq_wr = 0b11111111 - self.MCP['IOREQ']['iodir'] & self.MCP['RD'  ]['iodir']
        self.mcp23s17s.write_bus(self.MCP['MREQ']['addr'], self.MCP['MREQ']['bank'], reset_ioreq_wr) # set all z80 bus control lines inactive

    def read_z80_bus(self, bus_name):
        if bus_name == 'addr':
            addr_hi = self.mcp23s17s.read_bus(self.MCP['ADDR_HI']['addr'], self.MCP['ADDR_HI']['bank']) << 8
            addr_lo = self.mcp23s17s.read_bus(self.MCP['ADDR_LO']['addr'], self.MCP['ADDR_LO']['bank'])
            return addr_hi + addr_lo

        if bus_name == 'data':
            data = self.mcp23s17s.read_bus(self.MCP['DATA']['addr'], self.MCP['DATA']['bank'])
            return data

        if bus_name == 'ctrl':
            lookup = {'{:d}_{:d}_{:d}'.format(x[1]['addr'], x[1]['bank'], 7-'{:08b}'.format(x[1]['iodir']).find('1')): (x[0], x[1]['iodir'])  
                  for x in self.MCP.items() if 'ADDR' not in x[0] and 'DATA' not in x[0] and 'CTRL' not in x[0]} # build lookup dict l{chip_bank_signalbit: (signalname, iodir), }
            signals = OrderedDict()
            for addr, bank in [(self.MCP['DATA_CTRL']['addr'], self.MCP['DATA_CTRL']['bank']), (self.MCP['CTRL_LO']['addr'], self.MCP['CTRL_LO']['bank']),
                               (self.MCP['CTRL_HI'  ]['addr'], self.MCP['CTRL_HI'  ]['bank'])]:
                bus_value = self.mcp23s17s.read_bus(addr, bank) 
                for i in range(8):
                    lookup_key = '{:d}_{:d}_{:d}'.format(addr, bank, i)
                    signal_name = lookup[lookup_key][0]
                    signal_value = int (bus_value & lookup[lookup_key][1] > 0)
                    signals[signal_name] = signal_value
            return signals # returns a dict of {signal: value, ....}
 
    def wait_z80(self, option):
        if option == 'on':
            self.mcp23s17s.write_bus(self.MCP['WAIT']['addr'], self.MCP['WAIT']['bank'], self.ACTIVE_ALL,   self.MCP['WAIT']['iodir'])
            self.wait_state = True
        if option == 'off':
            self.mcp23s17s.write_bus(self.MCP['WAIT']['addr'], self.MCP['WAIT']['bank'], self.INACTIVE_ALL, self.MCP['WAIT']['iodir'])
            self.wait_state = True
        
    def ctrl_z80(self, option):
        if self.debug:
            print('DEBUG: {} Z80'.format(option))
        pin_map = {'reset': self.RESET_PIN, 'int': self.INT_PIN, 'nmi': self.NMI_PIN}
        gpio = pin_map[option]
        
        pin = Pin(gpio, Pin.OUT, value=ACTIVE)
        pin.value(INACTIVE)
        _ = Pin(gpio, Pin.IN, pull=Pin.PULL_UP) # input mode with weak pullup

    
    def single_step(self, options):
        if options[0] == 'on':
            jump_address = int(options[1])
            self.single_step = True
            save_bytes = []

            self.bus_control('grab')
            for addr in (0x0000, 0x0001, 0x0002):            # save first three bytes of memory
                save_bytes.append( self.read_memory(addr) )
            self.write_memory(0x0000, 0xC3)                  # write jump instruction to 'address' in first 3 bytes
            self.write_memory(0x0001, jump_address & 0x00FF) # write jump address high byte
            self.write_memory(0x0002, jump_address >> 8)     # write jump address low  byte
            self.bus_control('release')   

            self.reset_z80()                                 # start execution from above set address
            self.wait_z80('on')                              # check this is fast enough to pause execution...
            address = self.read_z80_bus('addr')
            data    = self.read_z80_bus('data')

            self.bus_control('grab')
            for addr in (0x0000, 0x0001, 0x0002):           # re-instate original value in first 3 bytes
                self.write_memory(0x0000, save_bytes[addr])
            self.bus_control('release')  
            save_bytes = []
            return address, data

        if options[0] == 'off':
            self.wait_z80('off') 
            return 0, 0

        self.wait_z80('off') # probable timing problem here with how many instructions will execute between off and on
        self.wait_z80('on')
        address = self.read_z80_bus('addr')
        data    = self.read_z80_bus('data')
        return address, data
    