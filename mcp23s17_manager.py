from micropython import const
from machine import Pin, SPI
from sys import byteorder
import sys

class MCP23S17s:
# Controller for 3x MCP23S17 chips. Lots of inline code for speed of execution.

    INACTIVE      = const(1)
    ACTIVE        = const(0)
    CTRL_RD       = const(0b01000001)   # format of control byte for read
    CTRL_WR       = const(0b01000000)   # format of control byte for write
    IOCON_DEFAULT = const(0b01101000) # enable mirror interrupts, disable seqential, enable HAEN
    IODIR_READ    = const(0b11111111) # all pins to read
    IODIR_WRITE   = const(0b00000000) # all pins to write
    MCP_RESET_GPIO= const(22)
    
    SPI_PORT      = const(1)
    SPI_CS_GPIO   = const(13)
    SPI_SCK       = const(14)
    SPI_MOSI      = const(15)
    SPI_MISO      = const(12)
    SPI_BAUDRATE  = const(1000)
    

    # MCP23S17 registers (from microchip datasheet https://ww1.microchip.com/downloads/en/devicedoc/20001952c.pdf)
    IODIRA   = const(0x00); IODIRB   = const(0x01); IPOLA    = const(0x02); IPOLB    = const(0x03)
    GPINTENA = const(0x04); GPINTENB = const(0x05); DEFVALA  = const(0x06); DEFVALB  = const(0x07)
    INTCONA  = const(0x08); INTCONB  = const(0x09); IOCONA   = const(0x0A); IOCONB   = const(0x0B) 
    GPPUA    = const(0x0C); GPPUB    = const(0x0D); INTFA    = const(0x0E); INTFB    = const(0x0F)
    INTCAPA  = const(0x10); INTCAPB  = const(0x11); GPIOA    = const(0x12); GPIOB    = const(0x13)
    OLATA    = const(0x14); OLATB    = const(0x15)
    

    def __init__(self, debug=False):
        self.debug = debug
        if self.debug:
            print('DEBUG: mcp23s17 manager debug mode=on, init start')
        mcp_reset_pin = Pin(MCP_RESET_GPIO, Pin.OUT, value=INACTIVE) # pico was resetting mcps sometimes with glitchs
        mcp_reset_pin.value(ACTIVE)
        self.cs_pin = Pin(SPI_CS_GPIO, Pin.OUT)
        self.spi = SPI(id=SPI_PORT, baudrate=SPI_BAUDRATE, polarity=0, phase=0, bits=8, firstbit=SPI.MSB, \
                                    sck=Pin(SPI_SCK), mosi=Pin(SPI_MOSI), miso=Pin(SPI_MISO))
        
        # configure both chips with HAEN enabled, mirrored interrupts, seq disabled
        self.cs_pin.value(ACTIVE); self.spi.write( bytes([CTRL_WR, IOCONA, IOCON_DEFAULT]) ); self.cs_pin.value(INACTIVE)
        self.cs_pin.value(ACTIVE); self.spi.write( bytes([CTRL_WR, IOCONB, IOCON_DEFAULT]) ); self.cs_pin.value(INACTIVE)

 
    def read_bus(self, chip, bank):
        self.cs_pin.value(ACTIVE); self.spi.write( bytes([CTRL_WR | (chip <<1), IODIRA + bank, IODIR_READ]) ); self.cs_pin.value(INACTIVE)
        self.cs_pin.value(ACTIVE); self.spi.write( bytes([CTRL_RD | (chip <<1), GPIOA  + bank]) ); data = self.spi.read(1); self.cs_pin.value(INACTIVE)
        data = int.from_bytes(data, byteorder)
        if self.debug:
            print('DEBUG: READ MCP23S17 CHIP:{}, BANK:{}: VALUE:{:08b}, IODIR:{:08b} '.format(chip, bank, data, IODIR_READ))
        return data

    def write_bus(self, chip, bank, data, iodir=IODIR_READ):
        self.cs_pin.value(ACTIVE); self.spi.write( bytes([CTRL_WR | (chip <<1), IODIRA + bank, iodir]) ); self.cs_pin.value(INACTIVE)
        if iodir != IODIR_READ:
            self.cs_pin.value(ACTIVE); self.spi.write( bytes([CTRL_WR | (chip <<1), OLATA  + bank, data]) );  self.cs_pin.value(INACTIVE)
        if self.debug:
            print('DEBUG: WRITE MCP23S17 CHIP:{}, BANK:{}: VALUE:{:08b}, IODIR:{:08b} '.format(chip, bank, data, iodir))


    def read_register(self, chip, register):
        self.cs_pin.value(ACTIVE); self.spi.write( bytes([CTRL_RD | (chip <<1), register]) ); self.cs_pin.value(INACTIVE)
        self.cs_pin.value(ACTIVE); data = self.spi.read(); self.cs_pin.value(INACTIVE)
        
        if self.debug:
            print('DEBUG: MCP23S17 READ REGISTER CHIP:{}: REG:{}, VALUE:{:08b}'.format(chip, register, data))
        return data

    def write_register(self, chip, register, data, mask=None):
        data = data & mask if mask else data
        if mask: # if setting bits in mask then need to read register first, then OR register value with data
            self.cs_pin.value(ACTIVE); self.spi.write( bytes([CTRL_RD | (chip <<1), register]) ); self.cs_pin.value(INACTIVE)
            current = self.spi.read(bytes=1) | data 
        
        self.cs_pin.value(ACTIVE); self.spi.write( bytes([CTRL_WR | (chip <<1), register, data]) ); self.cs_pin.value(INACTIVE)     # put IODIR back to all read
        if self.debug:
            print('DEBUG: MCP23S17 WRITE REGISTER CHIP:{}: REG:{}, VALUE:{:08b}, IODIR:{:08b}'.format(chip, register, data, mask if mask else 0xFF))

