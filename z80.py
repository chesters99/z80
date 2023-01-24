class Pin: # test harness class for debugging - to be deleted
    OUT = const(1)
    def __init__(self, pin, debug=False):
        self.pin = pin
        self.debug = debug

    def set(self, value):
        if self.debug:
            print('DEBUG: SET PICO PIN {} to VALUE {}'.format(self.pin, value))

class SPI: # test harness class for debugging - to be deleted
    def __init__(self, debug=False):
        self.debug = debug

    def write(self, value):
        if self.debug:
            print('DEBUG: SPI WRITE {:08b}'.format(value))

    def read(self, bytes=1)
        from random import randint
        data = randint(0, 0xFF)
        if self.debug:
            print('DEBUG: SPI READ {:08b}'.format(data))
        return 


# start mcp23s17_manager.py ####################
#from micropython import const 
#from machine import Pin, SPI 

class MCP23S17s:
# controller for MCP23S17 chips. Lots of inline code for speed of execution.

    RD       = const(1)
    WR       = const(0)
    ACTIVE   = const(0)
    INACTIVE = const(1)
    CTRL_BYTE     = const(0b01000000)
    IOCON_DEFAULT = const(0b01001000) # enable mirror interrupts, enabling HAEN
    IODIR_READ    = const(0b11111111) # all pins to read
    IODIR_WRITE   = const(0b00000000) # all pins to write

    # MCP23S17 registers (from microchip datasheet https://ww1.microchip.com/downloads/en/devicedoc/20001952c.pdf)
    IODIRA   = 0x00; IODIRB   = 0x01; IPOLA    = 0x02; IPOLB    = 0x03
    GPINTENA = 0x04; GPINTENB = 0x05; DEFVALA  = 0x06; DEFVALB  = 0x07
    INTCONA  = 0x08; INTCONB  = 0x09; IOCONA   = 0x0A; IOCONB   = 0x0B; 
    GPPUA    = 0x0C; GPPUB    = 0x0D; INTFA    = 0x0E; INTFB    = 0x0F
    INTCAPA  = 0x10; INTCAPB  = 0x11; GPIOA    = 0x12; GPIOB    = 0x13
    OLATA    = 0x14; OLATB    = 0x15

    def __init__(self, spi, cs, chips=3, banks=2, debug=False):
        self.debug = debug
        if self.debug:
            print('DEBUG: mcp23s17 manager debug mode=on')
        self.spi = spi
        self.cs  = cs
        self.cs.value(ACTIVE)
        for chip in chips:
            spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(IOCONA); spi.write(IOCON_DEFAULT) # configure i/o with HAEN enabled
            spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(IOCONB); spi.write(IOCON_DEFAULT) # configure i/o with HAEN enabled
            for bank in banks:
                spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(IODIRA); spi.write(IODIR_READ) # ensure IODIR is read
                spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(IODIRB); spi.write(IODIR_READ) # ensure IODIR is read
        self.cs.value(INACTIVE)
 
    def read_bus(self, chip, bank, mask=None):
        cs.value(ACTIVE); 
        spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(IODIRA+ bank); spi.write(IODIR_READ) # ensure IODIR is read
        spi.write(CTRL_BYTE | (chip <<1) | RD); spi.write(GPIOA + bank); data = spi.read(bytes=1)
        cs.value(INACTIVE)
        data = data & mask if mask else data
        if self.debug:
            print('DEBUG: MCP23S17 RECV CHIP:{}, BANK:{}: VALUE:{:02x} '.format(chip, bank, data))
        return data

    def write_bus(self, chip, bank, data, mask=IODIR_READ):
        cs.value(ACTIVE)
        spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(IODIRA+ bank); spi.write(~mask)       # set IODIR to NOT of mask
        spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(GPIOA + bank); spi.write(data)        # write data
        spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(IODIRA+ bank); spi.write(IODIR_READ)  # put IODIR back to all read
        cs.value(INACTIVE)
        if self.debug:
            print('DEBUG: MCP23S17 SEND CHIP:{}, BANK:{}: VALUE:{:02x} '.format(chip, bank, data))

    def read_register(self, chip, register, mask=None):
        cs.value(ACTIVE)
        spi.write(CTRL_BYTE | (chip <<1) | RD); spi.write(register); data = spi.read(bytes=1)
        cs.value(INACTIVE)
        data = data & mask if mask else data
        if self.debug:
            print('DEBUG: MCP23S17 READ REGISTER CHIP:{}: REG:{}, VALUE:{:08b} '.format(chip, register, data))
        return data

    def write_register(self, chip, register, data, mask=None):
        data = data & mask if mask else data
        cs.value(ACTIVE)
        if mask: # if setting bits in mask then need to read register first, then OR register value with data
            spi.write(CTRL_BYTE | (chip <<1) | RD); spi.write(register); current = spi.read(bytes=1)   
            data = current | data
        spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(register); spi.write(data)
        cs.value(INACTIVE)
        if self.debug:
            print('DEBUG: MCP23S17 WRITE REGISTER CHIP:{}: REG:{}, VALUE:{:08b} '.format(chip, register, data))

# end mcp23s17.py ################


# start bus_manager.py ##############
#from micropython import const
#from collections import OrderedDict
#import mcp23s17_manager

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
        'DATA_CTRL': {'addr':1, 'bank':1}, # some control lines on the data chip
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

    def __init__(self, spi, cs, debug=False):
        self.debug          = debug
        self.got_bus        = False
        self.wait_state     = False
        self.single_step    = False
        self.save_ss_addresses = []
        self.mcp23s17s = MCP23S17s(spi=spi, cs=cs, debug=False)
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
        elif if option[0] == 'release':
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

    def read_z80_bus(self, bus_name):adfafasdasdas make this one generalised method
        if not self.got_bus:
            raise RunTimeException('Trying to access bus without BUSAK high') # protect against program bugs
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
        if options[0] = 'on':
            self.mcp23s17s.write_bus(MCP23S17['WAIT']['addr'], MCP23S17['WAIT']['bank'], ACTIVE_ALL,   MCP23S17_ctrl['WAIT']['mask'])
            self.wait_state = True
        if options[0] = 'off':
            self.mcp23s17s.write_bus(MCP23S17['WAIT']['addr'], MCP23S17['WAIT']['bank'], INACTIVE_ALL,   MCP23S17_ctrl['WAIT']['mask'])
            self.wait_state = True
        
    def reset_z80(self):
        self.mcp23s17s.write_bus(MCP23S17['RESET']['addr'], MCP23S17['RESET']['bank'], ACTIVE_ALL,   MCP23S17_ctrl['RESET']['mask'])
        self.mcp23s17s.write_bus(MCP23S17['RESET']['addr'], MCP23S17['RESET']['bank'], INACTIVE_ALL, MCP23S17_ctrl['RESET']['mask'])

    
    def single_step(self, options[0]):
        if options[0] = 'on':
            self.bus_control('grab')
            jump_address = int(options[1])
            self.single_step = True
            self.save_buff[0] = self.read_memory(0x0000)
            self.save_buff[1] = self.read_memory(0x0001)
            self.save_buff[2] = self.read_memory(0x0002)
            self.write_memory(0x0000, 0xC3)             # write jump instruction to 'address' in first 3 bytes
            self.write_memory(0x0001, address & 0x00FF) # write jump address high byte
            self.write_memory(0x0002, address >> 8)     # write jump address low  byte
            self.bus_control('release')   
            self.reset_z80()                            # start execution from above set address
            self.wait_z80('on')                         # check this is fast enough to pause execution...
            address = self.read_z80_bus('addr')
            data    = self.read_z80_bus('data')
            return address, data

        if options[0] = 'off':
            self.wait_z80('off') 
            return 0,0

        self.wait_z80('off') # could be a timing problem here with how many instructions are execution between off and on
        self.wait_z80('on')
        address = self.read_z80_bus('addr')
        data    = self.read_z80_bus('data')
        return address, data
      
# end bus_manager.py ####################



# RC2014 (SC126) Z80 Bus Controller
# Graham Chester Jan-2023
# main program is menu options and functions to validate user selections, call bus manager functions, and output to user
# BusManager class contains state and methods to perform functions such as reading from memory by calling mcp23s17_manager
# mcp23s17_manager class contains state of the 3 bus transciever chips and calls Pico SPI bus functions to communicate

import sys
from collections import OrderedDict
from micropython import const
#import bus_manager

SPI_PORT = 1
SPI_CHIP_SELECT_PIN = const(13)
SPI_SCK_PIN         = const(14)
SPI_MOSI_PIN        = const(15)
SPI_MISO_PIN        = const(12)

# start main functions
def read_memory(command, options):
    if len(options) not in (1,2):
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    start_address  = int(options[0])
    if start_address < 0 or start_address + len(options[1:]) > 0xFFFF:
        raise ValueError('address less than zero or > 65536')
    length = 1 if len(options) == 1 else int(options[1])

    bytes_per_line = const(16)
    bus.bus_control('grab')
    if length < bytes_per_line: # print single column if not too much to dump else print 16 on a line
        for i, address in enumerate(range(start_address, start+length)):
            val = bus.read_memory(address)
            print("{:04X} {:02X} {:s}".format(start_address, val, chr(val if 0x20 <= val <= 0x7E  else 0x2E) ))
    else:
        data = []
        length = ((length + 15) & (-16)) # round bytes to display up to next multiple of 16
        for i,address in enumerate(range(start_address, start_address+length)):
            data.append( bus.read_address(start_address) )
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
    if start_address < 0 or start_address + len(options[1:]) > 0xFFFF:
        raise ValueError('address less than zero or address + data length > 0xFFFF')
    data = [int(i) for i in options[1:]]
    if min(data) < 0 or max(data) > 255:
        raise ValueError('byte value outside 0 to 255')
    
    bus.bus_control('grab')
    print('writing memory address 0x{:04X}: '.format(start_address), end='')
    for i, value in enumerate(data):
        bus.write_memory(start_address+i, value)
        print('0x{:02X} '.format(value), end='')
    bus.bus_control('release')
    print()
    
def read_io_device(command, options):
    if len(options) != 1:
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    io_address = int(options[0])
    if not (0 <= io_address <= 255): 
        raise ValueError('i/o address less than zero > 255')
    bus.bus_control('grab')
    data = bus.readio(io_address)
    bus.bus_control('release')
    print('Read i/o address {:02x}: {:2x}'.format(io_address, data))

def write_io_device(command, options):
    if len(options) != 2:
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    io_address = int(options[0])
    data       = int(options[1])
    bus.bus_control('grab')
    bus.write_io(io_address, data)
    bus.bus_control('release')
    print('Wrote i/o address {:02x}: {:2x}'.format(io_address, data))

def read_z80_bus(command, options):
    if len(options) != 1 or options[0] not in ('addr','data','ctrl'):
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])

    values = bus.read_z80_bus(options[0])
    if options[0] == 'addr':
        print('Address: {:04X}'.format(values))
    if options[0] == 'data':
        print('Address: {:02X}'.format(values))
    if options[0] == 'ctrl':
        print(values)    

def single_step(command, options):
    if len(options) != 1:
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    address = int(options[1])

    bus.single_step('on', address)
    while true:
        reply = input('press <enter> to step, x <enter> to run as normal')
        if reply.lower() == 'x':
            break
        data, address = bus.single_step()
        print('{:04X}: {:02X} '.format(address, data))
    bus.single_step('off')

def reset_z80(command, options):
    if len(options) != 1 or options[0] !='confirm':
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    print('resetting z80')
    bus.reset_z80()

def wait_z80(command, options):
    if len(options) !=1 or option[0] not in ('on','off'):
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    bus.wait_z80(option[0])
    print('Z80 wait state now {}'.format(options[0]))

def help_menu(command, options):
    for command in commands.items():
        print(command[0], command[1]['desc'] + ' ' + command[1]['params'])
        

# main processing
commands = OrderedDict({
    'rd': {'desc': 'read from',               'params': '<start_address> <num of bytes(optional)>', 'function': read_mem        },
    'wd': {'desc': 'write  to',               'params': '<start_address> <value> ...',              'function': write_mem       },
    'ri': {'desc': 'read i/o port',           'params': '<i/o address>',                            'function': read_io_device  },
    'wi': {'desc': 'write i/o port',          'params': '<i/o address> <data>...',                  'function': write_io_device },
    'rc': {'desc': 'read bus',                'params': '<addr/data/ctrl>',                         'function': read_z80_bus    },
    'wc': {'desc': 'write ctrl bus',          'params': '<control bit> = <0 or 1>',                 'function': write_z80_bus   },
    'ss': {'desc': 'single step mode',        'params': '<start address>',                          'function': single_step     },
    'zw': {'desc': 'put z80 into wait state', 'params': 'no parameters',                            'function': wait_z80        },
    'zr': {'desc': 'reset Z80',               'params': '"confirm"',                                'function': reset_z80       },
    'h':  {'desc': 'this help menu',          'params': 'no parameters',                            'function': help_menu       },
    'q':  {'desc': 'quit program',            'params': 'no parameters',                            'function': sys.exit        }}

spi = SPI(SPI_PORT, baudrate=1000000, polarity=1, phase=1, bits=8, firstbit=SPI.MSB, sck=machine.Pin(SPI_SCK_PIN), mosi=machine.Pin(SPI_MOSI_PIN), miso=machine.Pin(SPI_MISO_PIN))
cs  = Pin(SPI_CHIP_SELECT_PIN, Pin.OUT)
bus = BusManager(spi=spi, cs=cs, debug=False);

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
