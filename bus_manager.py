from micropython import const
from collections import OrderedDict
import time
from bus import BUS
from machine import Pin

class BusManager:  
    HI = const(0b11111111)
    LO = const(0b00000000)
    

    def __init__(self, debug=False):
        self.debug       = debug
        self.bus         = BUS(debug=self.debug)
        if self.debug:
            print('DEBUG: bus manager debug mode on')

    def control(self, option):
        if option == 'grab':
            self.bus.got_bus = True
            self.bus.write('BUSRQ', LO)
            if self.debug:
                input('DEBUG: Requested bus')
            self.bus.got_bus = (self.bus.read('BUSAK') == self.LO)
            if not self.bus.got_bus:
                self.bus.write('BUSRQ', HI)
                raise RuntimeError('ERROR: Couldnt grab bus, Z80 not responding')
            if self.debug:
                input('DEBUG: Got bus')
        elif option == 'release':
            self.bus.got_bus = False
            self.bus.write('BUSRQ', HI)
        else:
            raise ValueError('Can only grab or release bus')
        if self.debug:
            print('DEBUG: bus manager {} Z80 bus'.format(option))

    def read(self, address, request='memory'):
        if not self.bus.got_bus:
            raise RuntimeError('Trying to access bus without BUSAK low active') # protect against program bugs
        signal = 'IOREQ' if request == 'io' else 'MREQ'
        self.bus.write('ADDR_HI', address >> 8)
        self.bus.write('ADDR_LO', address &0x00FF)
        if request == 'io':
            self.bus.write('RD-IOREQ', LO)
        else:
            self.bus.write('RD-MREQ',  LO)
        if self.debug:
            input('DEBUG: about to read - press enter to continue'.format(request))            
        data = self.bus.read('DATA')
        self.bus.tristate()
        return data
        

    def write(self, address, data, request='memory'):
        if not self.bus.got_bus:
            raise RuntimeError('Trying to access bus without BUSAK low active') # protect against program bugs
        self.bus.write('ADDR_HI', address >> 8)
        self.bus.write('ADDR_LO', address & 0x00FF)
        self.bus.write('DATA', data)
        if request == 'io':
            self.bus.write('WR-IOREQ', LO)
        else:
            self.bus.write('WR-MREQ',  LO)
        if self.debug:
            input('DEBUG: wrote {} - press enter to continue'.format(request))
        self.bus.tristate()
    
    def read_bus(self, bus_name):
        if bus_name == 'addr':
            addr_hi = self.bus.read('ADDR_HI') << 8
            addr_lo = self.bus.read('ADDR_LO')
            return addr_hi + addr_lo
        if bus_name == 'data':
            return self.bus.read('DATA')

        if bus_name == 'ctrl':
            bus_value = self.bus.read('CTRL')
            signals = OrderedDict()
            for signal in ('BUSRQ','BUSAK','HALT','M1','MREQ','IOREQ','RD','WR'):
                signals[signal] = 0 if bus_value & self.bus.LOOKUP[signal][2] == 0 else 1
            return signals
        
    def ctrl_z80(self, option):
        if self.debug:
            print('DEBUG: {} Z80'.format(option))

        gpio = self.bus.LOOKUP[option]
        pin = Pin(gpio, Pin.OUT, value=LO)
        if self.debug:
            input('DEBUG: doing {}'.format(option))
        pin.value(HI)
        _ = Pin(gpio, Pin.IN, pull=Pin.PULL_UP) # input mode with weak pullup
