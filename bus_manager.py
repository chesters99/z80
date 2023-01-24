from micropython import const
from collections import OrderedDict
from mcp23s17 import MCP23S17s

class BusManager:  
    ACTIVE              = const(0) # Z80 ctrl lines are active low
    INACTIVE            = const(1)
    INACTIVE_ALL        = const(0b11111111)
    ACTIVE_ALL          = const(0b00000000)

    # MCP23S17 ctrl line configuraton
    MCP23S17 = OrderedDict({
        'ADDR_LO'  : {'addr':0, 'bank':0},
        'ADDR_HI'  : {'addr':0, 'bank':1},
        'DATA'     : {'addr':1, 'bank':0},
        'DATA_CTRL': {'addr':1, 'bank':1}, # 8 control lines are on the data chip
        'CTRL_LO'  : {'addr':2, 'bank':0},
        'CTRL_HI'  : {'addr':2, 'bank':1},

        'BUSRQ': {'addr':1, 'bank':1, 'mask': 0b00000001},
        'BUSAK': {'addr':1, 'bank':1, 'mask': 0b00000010},
        'WAIT' : {'addr':1, 'bank':1, 'mask': 0b00000100},
        'M1'   : {'addr':1, 'bank':1, 'mask': 0b00001000},
        'MREQ' : {'addr':1, 'bank':1, 'mask': 0b00010000},
        'IOREQ': {'addr':1, 'bank':1, 'mask': 0b00100000},
        'RD'   : {'addr':1, 'bank':1, 'mask': 0b01000000},
        'WR'   : {'addr':1, 'bank':1, 'mask': 0b10000000},
        
        'RESET': {'addr':2, 'bank':0, 'mask': 0b00000001},
        'HALT' : {'addr':2, 'bank':0, 'mask': 0b00000010},
        'INT'  : {'addr':2, 'bank':0, 'mask': 0b00000100},
        'NMI'  : {'addr':2, 'bank':0, 'mask': 0b00001000},
        'TX'   : {'addr':2, 'bank':0, 'mask': 0b00010000},
        'RX'   : {'addr':2, 'bank':0, 'mask': 0b00100000},
        'TX2'  : {'addr':2, 'bank':0, 'mask': 0b01000000},
        'RX2'  : {'addr':2, 'bank':0, 'mask': 0b10000000},
        
        'USER1': {'addr':2, 'bank':1, 'mask': 0b00000001},
        'USER2': {'addr':2, 'bank':1, 'mask': 0b00000010},
        'USER3': {'addr':2, 'bank':1, 'mask': 0b00000100},
        'USER4': {'addr':2, 'bank':1, 'mask': 0b00001000},
        'USER5': {'addr':2, 'bank':1, 'mask': 0b00010000},
        'USER6': {'addr':2, 'bank':1, 'mask': 0b00100000},
        'USER7': {'addr':2, 'bank':1, 'mask': 0b01000000},
        'USER8': {'addr':2, 'bank':1, 'mask': 0b10000000},})

    def __init__(self, spi, cs_pin, debug=False):
        self.debug          = debug
        self.got_bus        = False
        self.wait_state     = False
        self.single_step    = False
        self.mcp23s17s = MCP23S17s(spi=spi, cs_pin=cs_pin, debug=False)
        if self.debug:
            print('DEBUG: bus manager debug mode on')

    def bus_control(self, option):
        if len(options) !=1 or option[0] not in ('grab','release'):
            raise ValueError('Can only grab or release bus')
        if self.got_bus:
            print('Warning: cant grab bus as already grabbed, no action taken')
            return
 
        if option[0] == 'grab':
            self.mcp23s17s.write_bus(MCP23S17['BUSRQ']['addr'], MCP23S17['BUSRQ']['bank'], ACTIVE_ALL, MCP23S17_ctrl['BUSREQ']['mask'])
            while self.mcp23s17s.read_bus(MCP23S17['BUSAK']['addr'], MCP23S17['BUSAK']['bank']) & MCP23S17_ctrl['BUSAK']['mask'] == ACTIVE:
                print('Warning: bus manager waiting on BUSAK from Z80')
            self.got_bus = True
            if self.debug:
                print('DEBUG: bus manager grabbed Z80 bus')
        elif option[0] == 'release':
            self.mcp23s17s.write_bus(MCP23S17['BUSRQ']['addr'], MCP23S17['BUSRQ']['bank'], INACTIVE_ALL, MCP23S17_ctrl['BUSREQ']['mask'])
            self.got_bus = False
            if self.debug:
                print('DEBUG: bus manager released Z80 bus')

    def read_memory(self, address):
        if not self.got_bus:
            raise RunTimeException('Trying to access bus without BUSAK high') # protect against program bugs
        self.mcp23s17s.write_bus(MCP23S17['ADDR_LO']['addr'], MCP23S17['ADDR_LO']['bank'], address & 0x00FF)
        self.mcp23s17s.write_bus(MCP23S17['ADDR_HI']['addr'], MCP23S17['ADDR_HI']['bank'], address >> 8)
        self.mcp23s17s.write_bus(MCP23S17['RD'     ]['addr'], MCP23S17['RD'     ]['bank'], ACTIVE_ALL, MCP23S17['RD'  ]['mask'])
        self.mcp23s17s.write_bus(MCP23S17['MREQ'   ]['addr'], MCP23S17['MREQ'   ]['bank'], ACTIVE_ALL, MCP23S17['MREQ']['mask'])
        data = self.mcp23s17s.read_bus(MCP23S17['DATA']['addr'], MCP23S17['DATA']['bank'])
        self.mcp23s17s.write_bus(MCP23S17['MREQ'   ]['addr'], MCP23S17['MREQ']['bank'], INACTIVE_ALL) # set all z80 control lines inactive
        return data

    def write_memory(self, address, data):
        if not self.got_bus:
            raise RunTimeException('Trying to access bus without BUSAK high') # protect against program bugs
        self.mcp23s17s.write_bus(MCP23S17['ADDR_LO']['addr'], MCP23S17['ADDR_LO']['bank'], address & 0x00FF)
        self.mcp23s17s.write_bus(MCP23S17['ADDR_HI']['addr'], MCP23S17['ADDR_HI']['bank'], address >> 8)
        self.mcp23s17s.write_bus(MCP23S17['WR'  ]['addr'], MCP23S17['WR'  ]['bank'], ACTIVE_ALL, MCP23S17['WR'  ]['mask'])
        self.mcp23s17s.write_bus(MCP23S17['IOREQ']['addr'], MCP23S17['IOREQ']['bank'], ACTIVE_ALL, MCP23S17['IOREQ']['mask'])
        self.mcp23s17s.write_bus(MCP23S17['DATA']['addr'], MCP23S17['DATA']['bank'], data)
        self.mcp23s17s.write_bus(MCP23S17['IOREQ']['addr'], MCP23S17['IOREQ']['bank'], INACTIVE_ALL) # set all z80 bus control lines inactive

    def read_io(self, address):
        if not self.got_bus:
            raise RunTimeException('Trying to access bus without BUSAK high') # protect against program bugs
        self.mcp23s17s.write_bus(MCP23S17['ADDR_LO']['addr'], MCP23S17['ADDR_LO']['bank'], address & 0x00FF)
        self.mcp23s17s.write_bus(MCP23S17['RD'     ]['addr'], MCP23S17['RD'     ]['bank'], ACTIVE_ALL, MCP23S17['RD'  ]['mask'])
        self.mcp23s17s.write_bus(MCP23S17['IOREQ'   ]['addr'], MCP23S17['IOREQ'   ]['bank'], ACTIVE_ALL, MCP23S17['IOREQ']['mask'])
        data = self.mcp23s17s.read_bus(MCP23S17['DATA']['addr'], MCP23S17['DATA']['bank'])
        self.mcp23s17s.write_bus(MCP23S17['IOREQ'   ]['addr'], MCP23S17['IOREQ']['bank'], INACTIVE_ALL) # set all z80 control lines inactive
        return data

    def write_io(self, address, data):
        if not self.got_bus:
            raise RunTimeException('Trying to access bus without BUSAK high') # protect against program bugs
        self.mcp23s17s.write_bus(MCP23S17['ADDR_LO']['addr'], MCP23S17['ADDR_LO']['bank'], address & 0x00FF)
        self.mcp23s17s.write_bus(MCP23S17['WR'  ]['addr'], MCP23S17['WR'  ]['bank'], ACTIVE_ALL, MCP23S17['WR'  ]['mask'])
        self.mcp23s17s.write_bus(MCP23S17['MREQ']['addr'], MCP23S17['MREQ']['bank'], ACTIVE_ALL, MCP23S17['MREQ']['mask'])
        self.mcp23s17s.write_bus(MCP23S17['DATA']['addr'], MCP23S17['DATA']['bank'], data)
        self.mcp23s17s.write_bus(MCP23S17['MREQ']['addr'], MCP23S17['MREQ']['bank'], INACTIVE_ALL) # set all z80 bus control lines inactive

    def read_z80_bus(self, bus_name):
        if bus_name == 'addr':
            addr_hi = self.mcp23s17s.read_bus(MCP23S17['ADDR_HI']['addr'], MCP23S17['ADDR_HI']['bank']) << 8
            addr_lo = self.mcp23s17s.read_bus(MCP23S17['ADDR_LO']['addr'], MCP23S17['ADDR_LO']['bank'])
            return addr_hi + addr_lo

        if bus_name == 'data':
            data = self.mcp23s17s.read_bus(MCP23S17['DATA']['addr'], MCP23S17['DATA']['bank'])
            return data

        if bus_name == 'ctrl':
            lookup = {'{:d}_{:d}_{:d}'.format(x[1]['addr'], x[1]['bank'], 7-'{:08b}'.format(x[1]['mask']).find('1')): (x[0], x[1]['mask'])  
                  for x in MCP23S17.items() if 'ADDR' not in x[0] and 'DATA' not in x[0] and 'CTRL' not in x[0]} # build lookup dict like {chip_bank_signalbit: (signalname, mask), ...}
            signals = {}
            for addr, bank in [(MCP23S17['DATA_CTRL']['addr'], MCP23S17['DATA_CTRL']['bank']), (MCP23S17['CTRL_LO']['addr'], MCP23S17['CTRL_LO']['bank']),
                               (MCP23S17['CTRL_HI'  ]['addr'], MCP23S17['CTRL_HI'  ]['bank'])]:
                bus_value = self.mcp23s17s.read_bus(addr, bank) 
                for i in range(8):
                    lookup_key = '{:d}_{:d}_{:d}'.format(addr, bank, i)
                    signal_name = lookup[lookup_key][0]
                    signal_value = int (bus_value & lookup[lookup_key][1] > 0)
                    signals[signal_name] = signal_value
            return signals # returns a dict of {signal: value, ....}
 
    def wait_z80(self, option):
        if options[0] == 'on':
            self.mcp23s17s.write_bus(MCP23S17['WAIT']['addr'], MCP23S17['WAIT']['bank'], ACTIVE_ALL,   MCP23S17_ctrl['WAIT']['mask'])
            self.wait_state = True
        if options[0] == 'off':
            self.mcp23s17s.write_bus(MCP23S17['WAIT']['addr'], MCP23S17['WAIT']['bank'], INACTIVE_ALL,   MCP23S17_ctrl['WAIT']['mask'])
            self.wait_state = True
        
    def reset_z80(self):
        self.mcp23s17s.write_bus(MCP23S17['RESET']['addr'], MCP23S17['RESET']['bank'], ACTIVE_ALL,   MCP23S17_ctrl['RESET']['mask'])
        self.mcp23s17s.write_bus(MCP23S17['RESET']['addr'], MCP23S17['RESET']['bank'], INACTIVE_ALL, MCP23S17_ctrl['RESET']['mask'])

    
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
    