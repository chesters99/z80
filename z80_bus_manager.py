# RC2014 (SC126) Z80 Bus Manager 
# Graham Chester Jan-2023
# main program is menu options and functions to validate user selections, then call bus manager functions, and then to output to user
# BusManager class contains state and methods for interaction with Pico, and MCP23S17 chips

import sys, time
from collections import OrderedDict
from micropython import const
from bus_manager import BusManager
from secrets import secrets

# start main functions
def read_memory(user_input): # suspend Z80 and read from Z80 memory
    if len(user_input) not in (2, 3):
        raise ValueError('error: usage is '+user_input[0]+' '+commands[user_input[0]]['params'])
    start_address  = int(user_input[1])
    length = 1 if len(user_input) == 2 else int(user_input[2])
    if start_address < 0 or start_address + len(user_input[2:]) > 65535:
        raise ValueError('address less than zero or > 65535')

    mgr.control('grab')
    if length < 16: # print single column if not too much to dump else print 16 on a line
        for i, address in enumerate(range(start_address, start_address+length)):
            val = mgr.read(address, request='memory')
            print("{:04X} {:02X} {:s}".format(start_address, val, chr(val if 0x20 <= val <= 0x7E  else 0x2E) ))
    else:
        data = []
        length = ((length + 15) & (-16)) # round bytes to display up to next multiple of 16
        for i,address in enumerate(range(start_address, start_address+length)):
            data.append( mgr.read(address, request='memory') )
            if (i+1) % 16 == 0 and i > 0:                
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
        mgr.write(start_address+i, value, request='memory')
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
    print('Read i/o address 0x{:02x}: 0x{:02x}'.format(io_address, data))

def write_io_device(user_input): # suspend Z80 and write to a z80 i/o device
    if len(user_input) < 3:
        raise ValueError('error: usage is '+user_input[0]+' '+commands[user_input[0]]['params'])
    io_address = int(user_input[1])
    
    mgr.control('grab')
    print('Write i/o address 0x{:02x}: '.format(io_address))
    for data in user_input[2:]:
        mgr.write(io_address, int(data), request='io')
        print('0x{:02X} '.format(int(data)), end='')
    mgr.control('release')

def single_step(user_input):
    if len(user_input) != 1:
        raise ValueError('error: usage is '+user_input[0]+' '+commands[user_input[0]]['params'])
    
    mgr.m1_interrupt('on')    
    while True:        
        address = (mgr.read_bus('ADDR_H2') << 16) + (mgr.read_bus('ADDR_H1') << 8) + mgr.read_bus('ADDR_LO')
        data    =  mgr.read_bus('DATA')
        print('{:04X}: {:02X} '.format(address, data))
        mgr.m1_interrupt('clear')
        reply = input('Press <enter> to step, q <enter> to exit single step: ')
        if reply.lower() == 'q':
            break
    mgr.m1_interrupt('off')
    
def read_z80_bus(user_input): # sneaky read of a given bus without suspending z80
    if len(user_input) != 2 or user_input[1] not in ('addr','data','ctrl'):
        raise ValueError('error: usage is '+user_input[0]+' '+commands[user_input[0]]['params'])

    if user_input[1] == 'addr':
        address = (mgr.read_bus('ADDR_H2') << 16) + (mgr.read_bus('ADDR_H1') << 8) + mgr.read_bus('ADDR_LO')
        print('Address bus: 0x{:04X}'.format(address))
    elif user_input[1] == 'data':
        data = mgr.read_bus('DATA')
        print('Data bus: 0x{:02X}'.format(data))
    elif user_input[1] == 'ctrl':
        print('Ctrl pins: ', end='')
        for signal in ('BUSRQ','BUSAK','HALT','MREQ','IORQ','RD','WR','RESET','NMI','INT'):
            print('{}: {}'.format(signal,  mgr.read_signal(signal)), end=', ')
        print()   
    
def ctrl_z80(user_input): 
    if len(user_input) != 2 or user_input[1] not in ('reset', 'int', 'nmi'):
        raise ValueError('error: usage is '+user_input[0]+' '+commands[user_input[0]]['params'])
    print('{} Z80'.format(user_input[1]))
    mgr.write_signal(user_input[1].upper(), 1)
    mgr.write_signal(user_input[1].upper(), 0)
    mgr.write_signal(user_input[1].upper(), 1)


def z80_internet(user_input):
    uart = connect_uart()
    print(uart)
    uart.write(chr(26)+chr(26)) # in case z80 is stuck on prior read from aux
    
    print('Entering internet mode, waiting for z80 request, press ctrl-C to exit')
    try:
        _ = connect_wlan()
    except KeyboardInterrupt:
        print('Exiting internet mode: cant connect')
        return
   
    while True: 
        try:
            print('Waiting for z80 request')
            while True:
                if uart.any():
                    url = uart.read()
                    url = url.decode('utf-8').strip('\r\n')
                    break
                else:
                    time.sleep(1)
                    
            print('Getting from internet:', url)
            if not (url.startswith('https://') or url.startswith('http://')):
                url = 'https://' + url
            response = urequests.get(url, timeout=5)
            print('Status=', response.status_code)
            if response.status_code != 200:
                print('Error {response.status_code}, waiting...')
                uart.write(chr(26))
                break
            
            try:
                data = response.text
                data = data.replace('\r','').replace('\n','').replace('>', '>\r\n')
            except MemoryError as e:
                print('Error: webpage too large to process, exiting')
                uart.write('ERROR: webpage too large'+chr(26))
                continue
            
            chunk_size = 20
            for index in range(len(data) / chunk_size +1):
                chunk = data[index*chunk_size: (index+1) *chunk_size]
                uart.write(chunk)
                time.sleep(0.05) # 0.0007 - logic analyser flow control test!!
                
            uart.write(chr(26)) # to trigger z80 read from aux:
            print('Done!')
        except KeyboardInterrupt:
            print('Exiting internet mode: ctrl-c pressed')
            return
        
def z80_print(user_input):
    if len(user_input) == 1:
        printer, port = '192.168.1.218', 9100
    elif len(user_input) == 3:
        printer, port = user_input[1], user_input[2]
    else:
        raise ValueError('error: usage is '+user_input[0]+' '+commands[user_input[0]]['params'])
    print(f'Entering wifi printer mode printer {printer}, port {port}, press ctrl-C to exit')
    print('Trying to connect to printer...')
    uart = connect_uart()
    
    try: # connect to router
        _ = connect_wlan()
    except KeyboardInterrupt:
        machine.reset()
        print('Cant connect to router, exiting')
        return
    
    try: # connect to printer
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect((printer, port))
    except:
        print('Cant connect to {printer}, {port}, exiting')
        return
            
    while True: # loop until ctrl-c is pressed
        try:
            while True:
                if uart.any():
                    data = uart.read()
                    data = data.decode('utf_8')
                    conn.write(data)
#                     print(data)
                else:
                    time.sleep(1)

        except KeyboardInterrupt:
            conn.write(chr(12)) # form feed to ensure print page is ejected
            conn.close()
            print('Exiting print mode: ctrl-c pressed')
            return


def help_menu(user_input):
    for command in commands.items():
        print(command[0], command[1]['desc'] + ' ' + command[1]['params'])
        

# main processing
commands = OrderedDict({
    'rd'  : {'desc': 'read data from',      'params': '<start_address> <bytes(optional)>', 'function': read_memory     },
    'wd'  : {'desc': 'write data to',       'params': '<start_address> <value> ...',       'function': write_memory    },
    'ri'  : {'desc': 'read i/o port',       'params': '<i/o port address>',                'function': read_io_device  },
    'wi'  : {'desc': 'write i/o port',      'params': '<i/o port address> <data>...',      'function': write_io_device },
    'rb'  : {'desc': 'read a bus',          'params': '<addr/data/ctrl>',                  'function': read_z80_bus    },
    'ss'  : {'desc': 'single step mode',    'params': ': no parameters',                   'function': single_step     },
    'zc'  : {'desc': 'control Z80',         'params': '<reset/int/nmi>',                   'function': ctrl_z80        },
    'zi'  : {'desc': 'z80 internet access', 'params': ': no parameters',                   'function': z80_internet    },
    'zp'  : {'desc': 'z80 printer link',    'params': ': no parameters',                   'function': z80_print       },
    'h'   : {'desc': 'this help menu',      'params': ': no parameters',                   'function': help_menu       },
    'q'   : {'desc': 'quit program',        'params': ': no parameters',                   'function': sys.exit        }})

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
