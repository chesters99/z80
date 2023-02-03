from micropython import const
import time
from bus import BUS
from machine import Pin

class BusManager:  
    HI = const(0b11111111)
    LO = const(0b00000000)
    

    def __init__(self, debug=False):
        self.debug       = debug
        self.got_bus     = False
        self.wait_state  = False
        self.single_step = False
        self.bus         = BUS(debug=self.debug)
        if self.debug:
            print('DEBUG: bus manager debug mode on')

    def control(self, option):
        if option == 'grab':
            self.bus.write('BUSRQ', LO)
            self.got_bus = (self.bus.read('BUSAK') == self.LO)
            if not self.got_bus:
                raise RuntimeError('ERROR: Couldnt grab bus, Z80 not responding')               
        elif option == 'release':
            self.bus.write('BUSRQ', HI)
            self.got_bus = False
        else:
            raise ValueError('Can only grab or release bus')
        if self.debug:
            print('DEBUG: bus manager {} Z80 bus'.format(option))

    def read(self, address, request='memory'):
        if not self.got_bus:
            raise RuntimeError('Trying to access bus without BUSAK low active') # protect against program bugs
        signal = 'IOREQ' if request == 'io' else 'MREQ'
        self.bus.write('ADDR_HI', address >> 8)
        self.bus.write('ADDR_LO', address &0x00FF)
        if request == 'io':
            self.bus.write('RD,IOREQ', LO)
        else:
            self.bus.write('RD,MREQ',  LO)
        data = self.bus.read('DATA')
        input('read {} - press enter to continue'.format(request))
        self.bus.tristate()
        return data
        

    def write(self, address, data, request='memory'):
        if not self.got_bus:
            raise RuntimeError('Trying to access bus without BUSAK low active') # protect against program bugs
        self.bus.write('ADDR_HI', address >> 8)
        self.bus.write('ADDR_LO', address & 0x00FF)
        self.bus.write('DATA', data)
        if request == 'io':
            self.bus.write('WR,IOREQ', LO)
        else:
            self.bus.write('WR,MREQ',  LO)
        input('wrote {} - press enter to continue'.format(request))
        self.bus.tristate()
    
    def read_bus(self, bus_name):
        if bus_name == 'addr':
            addr_hi = self.bus.read('ADDR_HI') << 8
            addr_lo = self.bus.read('ADDR_LO')
            return addr_hi + addr_lo
        if bus_name == 'data':
            return self.bus.read('DATA')

        if bus_name == 'ctrl':
            lookup = {'{:d}_{:d}_{:d}'.format(x[1]['addr'], x[1]['bank'], 7-'{:08b}'.format(x[1]['iodir']).find('1')): (x[0], x[1]['iodir'])  
                  for x in self.bus.LOOKUP.items() if x[0] not in ('RESET','NMI','INT') } # build lookup dict l{chip_bank_signalbit: (signalname, iodir), }
            signals = OrderedDict()
            bus_value = self.bus.read('CTRL') 
            for i in range(8):
                lookup_key = '{:d}_{:d}_{:d}'.format(addr, bank, i)
                signal_name = lookup[lookup_key][0]
                signal_value = int (bus_value & lookup[lookup_key][1] > 0)
                signals[signal_name] = signal_value
            return signals # returns a dict of {signal: value, ....}
        
    def ctrl_z80(self, option):
        if self.debug:
            print('DEBUG: {} Z80'.format(option))
        if option == 'WAITON':
            self.bus.write('WAIT', LO)
            self.wait_state = True
        elif option == 'WAITOFF':
            self.bus.write('WAIT', HI)
            self.wait_state = False       
        else:
            gpio = self.bus.LOOKUP[option]
            pin = Pin(gpio, Pin.OUT, value=LO)
            input('doing {}'.format(option))
            pin.value(HI)
            _ = Pin(gpio, Pin.IN, pull=Pin.PULL_UP) # input mode with weak pullup
