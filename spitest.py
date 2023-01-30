from machine import Pin, SPI
import time

SPI_PORT     = const(1)
SPI_CS_GPIO  = const(13)
SPI_SCK      = const(14)
SPI_MOSI     = const(15)
SPI_MISO     = const(12)
SPI_BAUDRATE = const(1000)
INACTIVE  = const(1)
ACTIVE    = const(0)
MCP_RESET_GPIO= const(22)
    

mcp_reset_pin = Pin(MCP_RESET_GPIO, Pin.OUT, value=INACTIVE) # reset MCP23S17 chips
mcp_reset_pin.value(ACTIVE)
_ = Pin(MCP_RESET_GPIO, Pin.IN, pull=Pin.PULL_UP)
        
        
cs_pin = Pin(SPI_CS_GPIO, Pin.OUT)
spi = SPI(SPI_PORT, baudrate=SPI_BAUDRATE, polarity=0, phase=0, bits=8, firstbit=SPI.MSB, \
                       sck=Pin(SPI_SCK), mosi=Pin(SPI_MOSI), miso=Pin(SPI_MISO))
cs_pin.value(ACTIVE)
spi.write(bytes([0b01000000, 0b00001010, 0b01101000,])  )
cs_pin.value(INACTIVE)
cs_pin.value(ACTIVE)
spi.write(bytes([0b01000000, 0b00001011, 0b01101000,])  )
cs_pin.value(INACTIVE)


cs_pin.value(ACTIVE)
spi.write(bytes([0b01000010, 0b00000001, 0b11100010,])  )
cs_pin.value(INACTIVE)
cs_pin.value(ACTIVE)
spi.write(bytes([0b01000010, 0b00010101, 0b01101011,])  )
cs_pin.value(INACTIVE)


print('done')
