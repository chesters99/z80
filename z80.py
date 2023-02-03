# RC2014 (SC126) Z80 Bus Controller
# Graham Chester Jan-2023
# main program is menu options and functions to firstly validate user selections, secondly call bus manager functions, and finally output to user
# BusManager class contains state and methods to perform functions such as reading from memory by calling mcp23s17_manager
# mcp23s17_manager class contains state of the 3 bus transciever chips and calls Pico SPI bus functions to communicate

import sys, time
from collections import OrderedDict
from micropython import const
from bus_manager import BusManager


# start main functions
def read_memory(user_input): # suspend Z80 and read from Z80 memory
    if len(user_input) not in (2, 3):
        raise ValueError('error: usage is '+user_input[0]+' '+commands[user_input[0]]['params'])
    start_address  = int(user_input[1])
    if start_address < 0 or start_address + len(user_input[2:]) > 65535:
        raise ValueError('address less than zero or > 65535')
    length = 1 if len(user_input) == 2 else int(user_input[2])
    bytes_per_line = const(16)
    mgr.control('grab')
    if length < bytes_per_line: # print single column if not too much to dump else print 16 on a line
        for i, address in enumerate(range(start_address, start_address+length)):
            val = mgr.read(address)
            print("{:04X} {:02X} {:s}".format(start_address, val, chr(val if 0x20 <= val <= 0x7E  else 0x2E) ))
    else:
        data = []
        length = ((length + 15) & (-16)) # round bytes to display up to next multiple of 16
        for i,address in enumerate(range(start_address, start_address+length)):
            data.append( mgr.read(start_address) )
            if (i+1) % bytes_per_line == 0 and i > 0:                
                print('{:04X} '.format(start_address + i-bytes_per_line+1),
                      ''.join(['{:02X} '.format(val) for val in data]),
                      ''.join([chr(val if 0x20 <= val <= 0x7E  else 0x2E) for val in data]) )
                data = []
    mgr.control('release')
            
def write_memory(user_input): # suspend Z80 and write to Z80 memory
    if len(user_input) < 3:
        raise ValueError('error: usage is '+user_input[0]+' '+commands[user_input[0]]['params'])
    start_address = int(user_input[1])
    if start_address < 0 or start_address + len(user_input[2:]) > 65536:
        raise ValueError('address less than zero or address + data length > 65535')
    data = [int(i) for i in user_input[2:]]
    if min(data) < 0 or max(data) > 255:
        raise ValueError('byte value outside 0 to 255')
    
    mgr.control('grab')
    print('writing memory address 0x{:04X}: '.format(start_address), end='')
    for i, value in enumerate(data):
        mgr.write(start_address+i, value)
        print('0x{:02X} '.format(value), end='')
    mgr.control('release')
    print()
    
def read_io_device(user_input): # suspend Z80 and write to a z80 i/o device
    if len(user_input) != 2:
        raise ValueError('error: usage is '+user_input[0]+' '+commands[user_input[0]]['params'])
    io_address = int(user_input[1])
    if not (0 <= io_address <= 255): 
        raise ValueError('i/o address less than zero > 255')
    mgr.control('grab')
    data = mgr.read(io_address, request='io')
    mgr.control('release')
    print('Read i/o address {:02x}: {:2x}'.format(io_address, data))

def write_io_device(user_input): # suspend Z80 and write to a z80 i/o device
    if len(user_input) != 3:
        raise ValueError('error: usage is '+user_input[0]+' '+commands[user_input[0]]['params'])
    io_address, data = int(user_input[2]), nt(user_input[3])
    mgr.control('grab')
    mgr.write(io_address, data, request='io')
    mgr.control('release')
    print('Wrote i/o address {:02x}: {:2x}'.format(io_address, data))

def read_z80_bus(user_input): # sneaky read of a given bus without suspending z80
    if len(user_input) != 2 or options[2] not in ('addr','data','ctrl'):
        raise ValueError('error: usage is '+user_input[0]+' '+commands[user_input[0]]['params'])

    values = mgr.read_z80_bus(user_input[1])
    if options[0] == 'addr':
        print('Address: {:04X}'.format(values))
    if options[0] == 'data':
        print('Address: {:02X}'.format(values))
    if options[0] == 'ctrl':
        for key, value in values.items():
            print('{}: {}'.format(key, value), end=', ')
        print()   

def single_step(user_input): # single step from a given address
    if len(user_input) != 2:
        raise ValueError('error: usage is '+user_input[0]+' '+commands[user_input[0]]['params'])
    address = int(user_input[2])

    while true:
        reply = input('press <enter> to step, q <enter> to exit single step')
        if reply.lower() == 'q':
            break
        data, address = mgr.single_step()
        print('{:04X}: {:02X} '.format(address, data))
        

def ctrl_z80(user_input): 
    if len(user_input) != 2 or user_input[1] not in ('reset', 'int', 'nmi', 'waiton', 'waitoff'):
        raise ValueError('error: usage is '+user_input[0]+' '+commands[user_input[0]]['params'])
    print('{} z80'.format(user_input[1]))
    mgr.ctrl_z80(user_input[1].upper())

def help_menu(user_input):
    for command in commands.items():
        print(command[0], command[1]['desc'] + ' ' + command[1]['params'])
        

# main processing
commands = OrderedDict({
    'rd'  : {'desc': 'read data from',          'params': '<start_address> <num of bytes(optional)>', 'function': read_memory       },
    'wd'  : {'desc': 'write data to',           'params': '<start_address> <value> ...',              'function': write_memory      },
    'ri'  : {'desc': 'read i/o port',           'params': '<i/o port address>',                       'function': read_io_device    },
    'wi'  : {'desc': 'write i/o port',          'params': '<i/o port address> <data>...',             'function': write_io_device   },
    'rb'  : {'desc': 'read a bus',              'params': '<addr/data/ctrl>',                         'function': read_z80_bus      },
    'ss'  : {'desc': 'single step mode',        'params': '<start address>',                          'function': single_step       },
    'zc'  : {'desc': 'control Z80',             'params': '<reset/int/nmi/waiton/waitoff>',           'function': ctrl_z80          }, 
    'h'   : {'desc': 'this help menu',          'params': 'no parameters',                            'function': help_menu         },
    'q'   : {'desc': 'quit program',            'params': 'no parameters',                            'function': sys.exit          }})

mgr = BusManager(debug=True);

while True:
    user_input = input('Enter command (h for help): ').lower().split()
    if len(user_input) ==0:
        continue
    elif user_input[0] not in commands:
        print('invalid command, enter h for help')
        continue
     
    try:
        function = commands[ user_input[0] ]['function']        
        function(user_input)
    except (ValueError, RuntimeError) as e:
        print(e)
