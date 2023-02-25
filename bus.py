from micropython import const
from machine import Pin, SPI
from sys import byteorder
from collections import OrderedDict

class BUS: # Controller for 2x MCP23S17 chips and Pico GPIO line signals
    LO            = const(0)
    HI            = const(1)
    CTRL_RD       = const(0b01000001) # format of control byte for read
    CTRL_WR       = const(0b01000000) # format of control byte for write
    IOCON_DEFAULT = const(0b00101000) # disable sequential mode, enable HAEN
    IODIR_READ    = const(0b11111111)

    # Pico Pins & SPI
    MCP_RESET    = const(15)
    SPI_PORT     = const(0)
    SPI_CS       = const(17)
    SPI_SCK      = const(18)
    SPI_MOSI     = const(19)
    SPI_MISO     = const(16)
    SPI_BAUDRATE = const(8000000) # 9 Mhz is max on breadboard
    
    # MCP23S17 registers (from microchip datasheet https://ww1.microchip.com/downloads/en/devicedoc/20001952c.pdf)
    IODIRA   = const(0x00); IODIRB   = const(0x01); IPOLA   = const(0x02); IPOLB   = const(0x03)
    GPINTENA = const(0x04); GPINTENB = const(0x05); DEFVALA = const(0x06); DEFVALB = const(0x07)
    INTCONA  = const(0x08); INTCONB  = const(0x09); IOCONA  = const(0x0A); IOCONB  = const(0x0B) 
    GPPUA    = const(0x0C); GPPUB    = const(0x0D); INTFA   = const(0x0E); INTFB   = const(0x0F)
    INTCAPA  = const(0x10); INTCAPB  = const(0x11); GPIOA   = const(0x12); GPIOB   = const(0x13)
    OLATA    = const(0x14); OLATB    = const(0x15)

    LOOKUP = OrderedDict({     # format chip, bank, iodir mask
        'ADDR_LO' : [0, 0, 0b11111111], 
        'ADDR_HI' : [0, 1, 0b11111111],
        'DATA'    : [1, 0, 0b11111111],
        'CTRL'    : [1, 1, 0b11111111],
        'IOREQ'   : [1, 1, 0b00000001],
        'RD'      : [1, 1, 0b00000010],
        'WR'      : [1, 1, 0b00000100], # WAIT is connected to CTRL MCP23S17 INTB pin
        'MREQ'    : [1, 1, 0b00001000],
        'BUSRQ'   : [1, 1, 0b00010000],
        'M1'      : [1, 1, 0b00100000],
        'BUSAK'   : [1, 1, 0b01000000],
        'HALT'    : [1, 1, 0b10000000],
        'RD-MREQ' : [1, 1, 0b00001010],
        'WR-MREQ' : [1, 1, 0b00001100],
        'RD-IOREQ': [1, 1, 0b00000011],
        'WR-IOREQ': [1, 1, 0b00000101],
        'RESET':7, 'NMI':6, 'INT':5}) # simple pico signal pins
    

    def __init__(self, debug=False):
        self.debug = debug
        self.got_bus = False
        if self.debug:
            print('DEBUG: mcp23s17 manager debug mode=on, init start, SPI baudrate={:.2f}mhz'.format(SPI_BAUDRATE/1e6))
        for pin in (self.LOOKUP['RESET'], self.LOOKUP['NMI'], self.LOOKUP['INT']) :
            _ = Pin(pin, Pin.IN, pull=Pin.PULL_UP) # Put Z80 active low pins in input mode with weak pullup

        mcp_reset = Pin(MCP_RESET, Pin.OUT, value=LO)
        mcp_reset.value(HI)
        
        self.cs = Pin(SPI_CS, Pin.OUT)
        self.spi = SPI(id=SPI_PORT, baudrate=SPI_BAUDRATE, polarity=0, phase=0, bits=8, firstbit=SPI.MSB, \
                                    sck=Pin(SPI_SCK), mosi=Pin(SPI_MOSI), miso=Pin(SPI_MISO))
        
        # configure both chips with HAEN enabled, mirrored interrupts, seq disabled
        self.cs.value(LO)
        self.spi.write( bytes([CTRL_WR, IOCONA, IOCON_DEFAULT]) )
        self.cs.value(HI)
        self.cs.value(LO);
        self.spi.write( bytes([CTRL_WR, IOCONB, IOCON_DEFAULT]) )
        self.cs.value(HI)

    def write(self, signal, data=None):
        if signal in ('RESET', 'NMI', 'INT'):
            gpio = self.LOOKUP[option]
            pin = Pin(gpio, Pin.OUT, value=LO)
            if self.debug:
                input('DEBUG: doing {}'.format(signal))
            _ = Pin(gpio, Pin.IN, pull=Pin.PULL_UP) # input mode with weak pullup
            if self.debug:
                print('DEBUG: SET  SIGNAL:{} PIN:{}: VALUE:{:08b}'.format(signal, gpio))
        else:
            chip, bank, iodir = self.LOOKUP[signal]
            if self.got_bus: # if we have control of bus, dont drop BUSRQ
                iodir = iodir | self.LOOKUP['BUSRQ'][2]
            self.cs.value(LO)
            self.spi.write( bytes([CTRL_WR | (chip <<1), OLATA +bank, data]) )
            self.cs.value(HI)
            self.cs.value(LO)
            self.spi.write( bytes([CTRL_WR | (chip <<1), IODIRA+bank, IODIR_READ - iodir]) )
            self.cs.value(HI)
            if self.debug:
                print('DEBUG: WROTE MCP23S17 CHIP:{}, BANK:{}: IODIR:{:08b}, DATA:{:08b}'.format(chip, bank, IODIR_READ - iodir, data))

    def read(self, signal):
        if signal in ('RESET', 'NMI','INT'):
            gpio = self.LOOKUP[option]
            pin = Pin(gpio, Pin.IN)
            data = pin.value()
            if self.debug:
                print('DEBUG: READ SIGNAL:{} PIN:{}: VALUE:{:08b}'.format(signal, gpio, data))
        else:
            chip, bank, mask = self.LOOKUP[signal]
            iodir = IODIR_READ if not self.got_bus else IODIR_READ - self.LOOKUP['BUSRQ'][2] # if we have control of bus, dont drop BUSRQ
            self.cs.value(LO)
            self.spi.write( bytes([CTRL_WR | (chip <<1), IODIRA+bank, iodir]) )
            self.cs.value(HI)
            self.cs.value(LO)
            self.spi.write( bytes([CTRL_RD | (chip <<1), GPIOA +bank]) )
            data = self.spi.read(1)
            self.cs.value(HI)
            data = int.from_bytes(data, byteorder) & mask 
            if self.debug:
                print('DEBUG: READ  MCP23S17 CHIP:{}, BANK:{}: IODIR:{:08b}, DATA:{:08b}'.format(chip, bank, iodir, data))
        return data

    def tristate(self, bus_name=None):
        bus_names = [bus_name,] if bus_name else ('ADDR_HI','ADDR_LO', 'DATA', 'CTRL')
        for bus_name in bus_names:
            chip, bank, _ = self.LOOKUP[bus_name]
            self.cs.value(LO)
            self.spi.write( bytes([CTRL_WR | (chip <<1), IODIRA+bank, IODIR_READ]) )
            self.cs.value(HI)

    def interrupt(self, signal, action):
        chip, bank, mask = self.LOOKUP[signal]
        if action == 'on':
            self.spi.write( bytes([CTRL_WR | (chip <<1), INTCONA +bank, mask]) )  # interrupt if signal changes
            self.spi.write( bytes([CTRL_WR | (chip <<1), DEFVALA +bank, mask]) )  # from value mask
            self.spi.write( bytes([CTRL_WR | (chip <<1), GPINTENA+bank, mask]) )  # enable interrupt on mask signal
        elif action == 'off':
            self.spi.write( bytes([CTRL_WR | (chip <<1), GPINTENA+bank, 0]) )     # disable interrupt
        elif action == 'clear':
            self.spi.write( bytes([CTRL_RD | (chip <<1), GPIOA + bank]) )         # clear interrupt
            
        if self.debug:
            print('DEBUG: MCP23S17 INTERRUPT on {} set to {}'.format(signal, action))
            
