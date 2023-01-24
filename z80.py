
# RC2014 (SC126) Z80 Bus Controller
# Graham Chester Jan-2023
# main program is menu options and functions to firstly validate user selections, secondly call bus manager functions, and finally output to user
# BusManager class contains state and methods to perform functions such as reading from memory by calling mcp23s17_manager
# mcp23s17_manager class contains state of the 3 bus transciever chips and calls Pico SPI bus functions to communicate

import sys
from collections import OrderedDict
from micropython import const
from mcp23s17 import Pin, SPI 
from bus_manager import BusManager

SPI_PORT        = const(1)
SPI_CHIP_SELECT = const(13)
SPI_SCK         = const(14)
SPI_MOSI        = const(15)
SPI_MISO        = const(12)
SPI_BAUDRATE    = const(1000000)

# start main functions
def read_memory(command, options): # suspend Z80 and read from Z80 memory
    if len(options) not in (1,2):
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    start_address  = int(options[0])
    if start_address < 0 or start_address + len(options[1:]) > 0xFFFF:
        raise ValueError('address less than zero or > 65536')
    length = 1 if len(options) == 1 else int(options[1])

    bytes_per_line = const(16)
    mgr.bus_control('grab')
    if length < bytes_per_line: # print single column if not too much to dump else print 16 on a line
        for i, address in enumerate(range(start_address, start+length)):
            val = mgr.read_memory(address)
            print("{:04X} {:02X} {:s}".format(start_address, val, chr(val if 0x20 <= val <= 0x7E  else 0x2E) ))
    else:
        data = []
        length = ((length + 15) & (-16)) # round bytes to display up to next multiple of 16
        for i,address in enumerate(range(start_address, start_address+length)):
            data.append( mgr.read_address(start_address) )
            if (i+1) % bytes_per_line == 0 and i > 0:                
                print('{:04X} '.format(start + i-bytes_per_line+1),
                      ''.join(['{:02X} '.format(val) for val in data]),
                      ''.join([chr(val if 0x20 <= val <= 0x7E  else 0x2E) for val in data]) )
                data = []
    mgr.bus_control('release')
            
def write_memory(command, options): # suspend Z80 and write to Z80 memory
    if len(options) < 2:
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    start_address = int(options[0])
    if start_address < 0 or start_address + len(options[1:]) > 0xFFFF:
        raise ValueError('address less than zero or address + data length > 0xFFFF')
    data = [int(i) for i in options[1:]]
    if min(data) < 0 or max(data) > 255:
        raise ValueError('byte value outside 0 to 255')
    
    mgr.bus_control('grab')
    print('writing memory address 0x{:04X}: '.format(start_address), end='')
    for i, value in enumerate(data):
        mgr.write_memory(start_address+i, value)
        print('0x{:02X} '.format(value), end='')
    mgr.bus_control('release')
    print()
    
def read_io_device(command, options): # suspend Z80 and write to a z80 i/o device
    if len(options) != 1:
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    io_address = int(options[0])
    if not (0 <= io_address <= 255): 
        raise ValueError('i/o address less than zero > 255')
    mgr.bus_control('grab')
    data = mgr.readio(io_address)
    mgr.bus_control('release')
    print('Read i/o address {:02x}: {:2x}'.format(io_address, data))

def write_io_device(command, options): # suspend Z80 and write to a z80 i/o device
    if len(options) != 2:
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    io_address = int(options[0])
    data       = int(options[1])
    mgr.bus_control('grab')
    mgr.write_io(io_address, data)
    mgr.bus_control('release')
    print('Wrote i/o address {:02x}: {:2x}'.format(io_address, data))

def read_z80_bus(command, options): # sneaky read of a given bus without suspending z80
    if len(options) != 1 or options[0] not in ('addr','data','ctrl'):
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])

    values = mgr.read_z80_bus(options[0])
    if options[0] == 'addr':
        print('Address: {:04X}'.format(values))
    if options[0] == 'data':
        print('Address: {:02X}'.format(values))
    if options[0] == 'ctrl':
        print(values)    

def single_step(command, options): # single step from a given address
    if len(options) != 1:
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    address = int(options[1])

    mgr.single_step('on', address)
    while true:
        reply = input('press <enter> to step, x <enter> to run as normal')
        if reply.lower() == 'x':
            break
        data, address = mgr.single_step()
        print('{:04X}: {:02X} '.format(address, data))
    mgr.single_step('off')

def reset_z80(command, options): # reset z80 
    if len(options) != 1 or options[0] !='confirm':
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    print('resetting z80')
    mgr.reset_z80()

def wait_z80(command, options): # put z80 in/out of wait state so values from read_z80_bus are decent
    if len(options) !=1 or option[0] not in ('on','off'):
        raise ValueError('error: usage is '+command+' '+commands[commmand][params])
    mgr.wait_z80(option[0])
    print('Z80 wait state now {}'.format(options[0]))

def help_menu(command, options):
    for command in commands.items():
        print(command[0], command[1]['desc'] + ' ' + command[1]['params'])
        

# main processing
commands = OrderedDict({
    'rd': {'desc': 'read from',               'params': '<start_address> <num of bytes(optional)>', 'function': read_memory     },
    'wd': {'desc': 'write  to',               'params': '<start_address> <value> ...',              'function': write_memory    },
    'ri': {'desc': 'read i/o port',           'params': '<i/o port address>',                       'function': read_io_device  },
    'wi': {'desc': 'write i/o port',          'params': '<i/o port address> <data>...',             'function': write_io_device },
    'rb': {'desc': 'read a bus',              'params': '<addr/data/ctrl>',                         'function': read_z80_bus    },
    'ss': {'desc': 'single step mode',        'params': '<start address>',                          'function': single_step     },
    'zw': {'desc': 'put z80 into wait state', 'params': '<on/off>',                                 'function': wait_z80        },
    'zr': {'desc': 'reset/reboot Z80',        'params': '"confirm"',                                'function': reset_z80       },
    'h':  {'desc': 'this help menu',          'params': 'no parameters',                            'function': help_menu       },
    'q':  {'desc': 'quit program',            'params': 'no parameters',                            'function': sys.exit        }})

cs_pin = Pin(SPI_CHIP_SELECT, Pin.OUT, debug=False)
spi = SPI(SPI_PORT, baudrate=SPI_BAUDRATE, polarity=1, phase=1, bits=8, firstbit=SPI.MSB, \
                    sck=Pin(SPI_SCK), mosi=Pin(SPI_MOSI), miso=Pin(SPI_MISO))
mgr = BusManager(spi, cs_pin, debug=False);

while True:
    user_input = input('Enter command (h for help): ').lower().split()
    command = user_input[0] if len(user_input) > 0 else None
    if command not in commands:
        print('invalid command, enter h for help')
        continue
    function = commands[command]['function']
    try:
        function(command, user_input[1:])
    except ValueError as e:
        print(e)
