class Pin: # test harness class for debugging - to be deleted
    OUT = const(1)

    def __init__(self, pin, direction=0, debug=False):
        self.pin = pin
        self.debug = debug
        if self.debug:
            print('DEBUG: CREATED PICO PIN {} WITH DIRECTION'.format(self.pin, direction))

    def value(self, val):
        if self.debug:
            print('DEBUG: SET PICO PIN {} to VALUE {}'.format(self.pin, val))

class SPI: # test harness class for debugging - to be deleted
    MSB = const(1)
    def __init__(self, port, baudrate, polarity, phase, bits, firstbit, sck, mosi, miso, debug=False):
        self.debug = debug

    def write(self, value):
        if self.debug:
            print('DEBUG: SPI WRITE {:08b}'.format(value))

    def read(self, bytes=1):
        from random import randint
        data = randint(0, 0xFF)
        if self.debug:
            print('DEBUG: SPI READ {:08b}'.format(data))
        return 



from micropython import const 

class MCP23S17s:
# Controller for 3x MCP23S17 chips. Lots of inline code for speed of execution.

    RD       = const(1)
    WR       = const(0)
    INACTIVE = const(1)
    ACTIVE   = const(0)
    CTRL_BYTE     = const(0b01000000) # basic format of control byte
    IOCON_DEFAULT = const(0b01001000) # enable mirror interrupts, enabling HAEN
    IODIR_READ    = const(0b11111111) # all pins to read
    IODIR_WRITE   = const(0b00000000) # all pins to write

    # MCP23S17 registers (from microchip datasheet https://ww1.microchip.com/downloads/en/devicedoc/20001952c.pdf)
    IODIRA   = const(0x00); IODIRB   = const(0x01); IPOLA    = const(0x02); IPOLB    = const(0x03)
    GPINTENA = const(0x04); GPINTENB = const(0x05); DEFVALA  = const(0x06); DEFVALB  = const(0x07)
    INTCONA  = const(0x08); INTCONB  = const(0x09); IOCONA   = const(0x0A); IOCONB   = const(0x0B) 
    GPPUA    = const(0x0C); GPPUB    = const(0x0D); INTFA    = const(0x0E); INTFB    = const(0x0F)
    INTCAPA  = const(0x10); INTCAPB  = const(0x11); GPIOA    = const(0x12); GPIOB    = const(0x13)
    OLATA    = const(0x14); OLATB    = const(0x15)

    def __init__(self, spi, cs_pin, chips=3, debug=False):
        self.debug = debug
        if self.debug:
            print('DEBUG: mcp23s17 manager debug mode=on')
        self.spi = spi
        self.cs_pin  = cs_pin
        for chip in range(chips): # configure i/o with HAEN enabled, and set IODIR to all bits in read mode
            spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(IOCONA); spi.write(IOCON_DEFAULT)
            spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(IOCONB); spi.write(IOCON_DEFAULT)
            spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(IODIRA); spi.write(IODIR_READ)
            spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(IODIRB); spi.write(IODIR_READ)
        self.cs_pin.value(INACTIVE)
 
    def read_bus(self, chip, bank, mask=None):
        cs_pin.value(ACTIVE); 
        spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(IODIRA + bank); spi.write(IODIR_READ) # ensure IODIR is all read mode
        spi.write(CTRL_BYTE | (chip <<1) | RD); spi.write(GPIOA  + bank); data = spi.read(bytes=1)
        cs_pin.value(INACTIVE)
        data = data & mask if mask else data
        if self.debug:
            print('DEBUG: MCP23S17 RECV CHIP:{}, BANK:{}: VALUE:{:02x}, MASK:{08b} '.format(chip, bank, data, mask if mask else 0xFF))
        return data

    def write_bus(self, chip, bank, data, mask=IODIR_READ):
        cs_pin.value(ACTIVE)
        spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(IODIRA + bank); spi.write(~mask)       # to write set IODIR to NOT of mask
        spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(GPIOA  + bank); spi.write(data)        # write data
        spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(IODIRA + bank); spi.write(IODIR_READ)  # put IODIR back to all read
        cs_pin.value(INACTIVE)
        if self.debug:
            print('DEBUG: MCP23S17 SEND CHIP:{}, BANK:{}: VALUE:{:02x}, MASK:{08b} '.format(chip, bank, data, mask))

    def read_register(self, chip, register, mask=None):
        cs_pin.value(ACTIVE)
        spi.write(CTRL_BYTE | (chip <<1) | RD); spi.write(register); data = spi.read(bytes=1)
        cs_pin.value(INACTIVE)
        data = data & mask if mask else data
        if self.debug:
            print('DEBUG: MCP23S17 READ REGISTER CHIP:{}: REG:{}, VALUE:{:08b}, MASK:{08b}'.format(chip, register, data, mask if mask else 0xFF))
        return data

    def write_register(self, chip, register, data, mask=None):
        data = data & mask if mask else data
        cs_pin.value(ACTIVE)
        if mask: # if setting bits in mask then need to read register first, then OR register value with data
            spi.write(CTRL_BYTE | (chip <<1) | RD); spi.write(register); current = spi.read(bytes=1)   
            data = current | data
        spi.write(CTRL_BYTE | (chip <<1) | WR); spi.write(register); spi.write(data)
        cs_pin.value(INACTIVE)
        if self.debug:
            print('DEBUG: MCP23S17 WRITE REGISTER CHIP:{}: REG:{}, VALUE:{:08b}, MASK:{08b}'.format(chip, register, data, mask if mask else 0xFF))
