from machine import Pin, SPI
import time

MCP_RESET = const(6) # reset mcp23S17 chips
SPI_MISO  = const(16) # MCP23S17 SPI port
SPI_CS    = const(17) # MCP23S17 SPI port
SPI_SCK   = const(18) # MCP23S17 SPI port
SPI_MOSI  = const(19) # MCP23S17 SPI port
SPI_PORT      = const(0)
SPI_BAUDRATE  = const(2000000) # 3 Mhz is max for reliability on breadboard
LO            = const(0)
HI            = const(1)
CTRL_RD       = const(0b01000001) # format of control byte for read
CTRL_WR       = const(0b01000000) # format of control byte for write
IOCON_DEFAULT = const(0b00101000) # disable sequential mode, enable HAEN, INT polarity active low

# MCP23S17 registers (from microchip datasheet https://ww1.microchip.com/downloads/en/devicedoc/20001952c.pdf)
IODIRA   = const(0x00); IODIRB   = const(0x01); IPOLA   = const(0x02); IPOLB   = const(0x03)
GPINTENA = const(0x04); GPINTENB = const(0x05); DEFVALA = const(0x06); DEFVALB = const(0x07)
INTCONA  = const(0x08); INTCONB  = const(0x09); IOCONA  = const(0x0A); IOCONB  = const(0x0B) 
GPPUA    = const(0x0C); GPPUB    = const(0x0D); INTFA   = const(0x0E); INTFB   = const(0x0F)
INTCAPA  = const(0x10); INTCAPB  = const(0x11); GPIOA   = const(0x12); GPIOB   = const(0x13)
OLATA    = const(0x14); OLATB    = const(0x15)
    

mcp_reset = Pin(MCP_RESET, Pin.OUT, value=HI)
mcp_reset.value(LO)
mcp_reset.value(HI)

cs  = Pin(SPI_CS, Pin.OUT)
spi = SPI(id=SPI_PORT,baudrate=SPI_BAUDRATE,polarity=0,phase=0,bits=8,firstbit=SPI.MSB,sck=Pin(SPI_SCK),mosi=Pin(SPI_MOSI),miso=Pin(SPI_MISO))
cs.value(LO);
spi.write( bytes([CTRL_WR, IOCONA, IOCON_DEFAULT]) );
cs.value(HI) # enable HAEN, disable Sequential

buff1 = bytes([CTRL_RD, IOCONA])
cs.value(LO);
spi.write(buff1);
buff2 = spi.read(1)
cs.value(HI)
print(['{:08b}'.format(b) for b in bytes([CTRL_WR,IOCONA,IOCON_DEFAULT])])
print(['{:08b}'.format(b) for b in buff1] , ['{:08b}'.format(b) for b in buff2])
