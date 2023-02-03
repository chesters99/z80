from micropython import const
from machine import Pin, SPI
from sys import byteorder
from collections import OrderedDict

class BUS: # Controller for 2x MCP23S17 chips and Pico GPIO line signals
    LO            = const(0)
    HI            = const(1)
    CTRL_RD       = const(0b01000001) # format of control byte for read
    CTRL_WR       = const(0b01000000) # format of control byte for write
    IOCON_DEFAULT = const(0b01101000) # enable mirror interrupts, disable seqential, enable HAEN
    IODIR_READ    = const(0b11111111)

    # Pico Pins & SPI
    MCP_RESET    = const(22)
    SPI_PORT     = const(1)
    SPI_CS       = const(13)
    SPI_SCK      = const(14)
    SPI_MOSI     = const(15)
    SPI_MISO     = const(12)
    SPI_BAUDRATE = const(50000000) # 62 Mhz is max on breadboard
    
    # MCP23S17 registers (from microchip datasheet https://ww1.microchip.com/downloads/en/devicedoc/20001952c.pdf)
    IODIRA   = const(0x00); IODIRB   = const(0x01); IPOLA   = const(0x02); IPOLB   = const(0x03)
    GPINTENA = const(0x04); GPINTENB = const(0x05); DEFVALA = const(0x06); DEFVALB = const(0x07)
    INTCONA  = const(0x08); INTCONB  = const(0x09); IOCONA  = const(0x0A); IOCONB  = const(0x0B) 
    GPPUA    = const(0x0C); GPPUB    = const(0x0D); INTFA   = const(0x0E); INTFB   = const(0x0F)
    INTCAPA  = const(0x10); INTCAPB  = const(0x11); GPIOA   = const(0x12); GPIOB   = const(0x13)
    OLATA    = const(0x14); OLATB    = const(0x15)

    LOOKUP = OrderedDict({
        'ADDR_LO' : [0, 0, 0b00000000], # format chip, bank, iodir mask
        'ADDR_HI' : [0, 1, 0b00000000],
        'DATA'    : [1, 0, 0b00000000],
        'CTRL'    : [1, 1, 0b00000000],
        'BUSRQ'   : [1, 1, 0b11111110],
        'BUSAK'   : [1, 1, 0b11111101],
        'WAIT'    : [1, 1, 0b11111011],
        'M1'      : [1, 1, 0b11110111],
        'MREQ'    : [1, 1, 0b11101111],
        'IOREQ'   : [1, 1, 0b11011111],
        'RD'      : [1, 1, 0b10111111],
        'WR'      : [1, 1, 0b01111111],
        'RESET': 26, 'NMI':27, 'INT':28})
    

    def __init__(self, debug=False):
        self.debug = debug
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
            input('doing {}'.format(signal))
            _ = Pin(gpio, Pin.IN, pull=Pin.PULL_UP) # input mode with weak pullup
            if self.debug:
                print('DEBUG: SET SIGNAL:{} PIN:{}: VALUE:{:08b}'.format(signal, gpio))
        else:
            iodir = IODIR_READ
            signals = signal.split(',')
            for signal in signals: # handle multiple signals e.g. 'WR,MREQ'
                chip, bank, iodir1 = self.LOOKUP[signal]
                iodir = iodir & iodir1
                
            self.cs.value(LO)
            self.spi.write( bytes([CTRL_WR | (chip <<1), OLATA +bank, data]) )
            self.cs.value(HI)
            self.cs.value(LO)
            self.spi.write( bytes([CTRL_WR | (chip <<1), IODIRA+bank, iodir]) )
            self.cs.value(HI)
            if self.debug:
                print('DEBUG: WROTE MCP23S17 CHIP:{}, BANK:{}: VALUE:{:08b} IODIR:{:08b}'.format(chip, bank, data, iodir))

    def read(self, signal):
        if signal in ('RESET', 'NMI','INT'):
            gpio = self.LOOKUP[option]
            pin = Pin(gpio, Pin.IN)
            data = pin.value()
            if self.debug:
                print('DEBUG: READ SIGNAL:{} PIN:{}: VALUE:{:08b}'.format(signal, gpio, data))
        else:
            iodir = IODIR_READ
            signals = signal.split(',')
            for signal in signals: # handle multiple signals e.g. 'RD,MREQ'
                chip, bank, iodir1 = self.LOOKUP[signal]
                iodir = iodir & iodir1
            self.cs.value(LO)
            self.spi.write( bytes([CTRL_WR | (chip <<1), IODIRA+bank, IODIR_READ]) )
            self.cs.value(HI)
            self.cs.value(LO)
            self.spi.write( bytes([CTRL_RD | (chip <<1), GPIOA +bank]) )
            data = self.spi.read(1)
            self.cs.value(HI)
            data = int.from_bytes(data, byteorder) & (0b11111111 - iodir)
            if self.debug:
                print('DEBUG: READ MCP23S17 CHIP:{}, BANK:{}: IODIR:{:08b}  VALUE:{:08b}, '.format(chip, bank, iodir, data))
        return data

    def tristate(self, bus_name=None):
        bus_names = [bus_name,] if bus_name else ('ADDR_HI','ADDR_LO', 'DATA', 'CTRL')
        for bus_name in bus_names:
            chip, bank, _ = self.LOOKUP[bus_name]
            self.cs.value(LO)
            self.spi.write( bytes([CTRL_WR | (chip <<1), IODIRA+bank, IODIR_READ]) )
            self.cs.value(HI)
