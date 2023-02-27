from micropython import const
from machine import UART, SPI, Pin
from sys import byteorder
import network, socket, urequests

# Pico GPIO Pins
UART_TX   = const(0) # Z80 serial port 2
UART_RX   = const(1) # Z80 serial port 2
UART_CTS  = const(2) # Z80 serial port 2
UART_RTS  = const(3) # Z80 serial port 2
I2C0_SDA  = const(4) # i2c display (future)
I2C0_SCL  = const(5) # i2c display (future)
MCP_RESET = const(6) # reset mcp23S17 chips
unused1   = const(7)
unused2   = const(8)
unused3   = const(9)
unused4   = const(10)
unused5   = const(11)
Z80_BUSAK = const(12)
Z80_HALT  = const(13)
Z80_BUSRQ = const(14)
Z80_NMI   = const(15)
SPI_MISO  = const(16) # MCP23S17 SPI port
SPI_CS    = const(17) # MCP23S17 SPI port
SPI_SCK   = const(18) # MCP23S17 SPI port
SPI_MOSI  = const(19) # MCP23S17 SPI port
Z80_IORQ  = const(20)
Z80_RD    = const(21)
Z80_WR    = const(22)
Z80_MREQ  = const(26)
Z80_INT   = const(27)
Z80_RESET = const(28)

# MCP23S17 & Z80 related constants
Z80_BAUDRATE  = const(115200)
SPI_PORT      = const(0)
SPI_BAUDRATE  = const(5000000) # 9 Mhz is max on breadboard
LO            = const(0)
HI            = const(1)
CTRL_RD       = const(0b01000001) # format of control byte for read
CTRL_WR       = const(0b01000000) # format of control byte for write
IOCON_DEFAULT = const(0b00101000) # disable sequential mode, enable HAEN, INT polarity active low
IODIR_READ    = const(0b11111111)
IODIR_WRITE   = const(0b00000000)
ADDR_H2_MASK  = const(0b00001111)

# MCP23S17 registers (from microchip datasheet https://ww1.microchip.com/downloads/en/devicedoc/20001952c.pdf)
IODIRA   = const(0x00); IODIRB   = const(0x01); IPOLA   = const(0x02); IPOLB   = const(0x03)
GPINTENA = const(0x04); GPINTENB = const(0x05); DEFVALA = const(0x06); DEFVALB = const(0x07)
INTCONA  = const(0x08); INTCONB  = const(0x09); IOCONA  = const(0x0A); IOCONB  = const(0x0B) 
GPPUA    = const(0x0C); GPPUB    = const(0x0D); INTFA   = const(0x0E); INTFB   = const(0x0F)
INTCAPA  = const(0x10); INTCAPB  = const(0x11); GPIOA   = const(0x12); GPIOB   = const(0x13)
OLATA    = const(0x14); OLATB    = const(0x15)

# -------------------  functions for internet access and Pico to Z80 comms ---------------------
def connect_wlan():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(secrets['ssid'], secrets['password'])
    while wlan.isconnected() == False:
        print('Waiting for wlan connection ctrl-c to quit...')
        time.sleep(2)
    ip = wlan.ifconfig()[0]
    print(f'Connected to router: my ip={ip}')
    return ip

def connect_uart():
    uart = UART(0, baudrate=Z80_BAUDRATE, tx=Pin(UART_TX), rx=Pin(UART_RX), cts=Pin(UART_CTS), rts=Pin(UART_RTS), flow=UART.RTS | UART.CTS)
    uart.init(bits=8, parity=None, stop=1)
    return uart

# -------------------  Class contains state and methods to interact with Pico, and MCP23S17 chips ---------------------

class BusManager:    
    LOOKUP = {                      # chips 0 and 1 are mcp23s17: format=[chip, bank]
        'ADDR_LO' : [0, 0],         # A0 -> A7
        'ADDR_H1' : [0, 1],         # A8 -> A15
        'DATA'    : [1, 0],         # D0 -> D7
        'ADDR_H2' : [1, 1],         # A16, A17, A18, A19, NC, NC, WAIT, M1
        'BUSAK'   : [2, Z80_BUSAK], # chip 2 is Pico Z80 signals: format=[chip, GPIO pin(s)]
        'HALT'    : [2, Z80_HALT ],
        'BUSRQ'   : [2, Z80_BUSRQ],
        'NMI'     : [2, Z80_NMI  ],
        'IORQ'    : [2, Z80_IORQ ],
        'RD'      : [2, Z80_RD   ],
        'WR'      : [2, Z80_WR   ],
        'MREQ'    : [2, Z80_MREQ ],
        'INT'     : [2, Z80_INT  ],
        'RESET'   : [2, Z80_RESET],
        'MREQ_RD' : [3, (Z80_MREQ, Z80_RD)], # chip 3 is multiple Pico Z80 signals (for performance/convenience)
        'MREQ_WR' : [3, (Z80_MREQ, Z80_WR)],
        'IORQ_RD' : [3, (Z80_IORQ, Z80_RD)],
        'IORQ_WR' : [3, (Z80_IORQ, Z80_WR)],
         }
   
    def __init__(self, debug=False):
        self.debug = debug
        self.got_bus = False
        if self.debug:
            print('DEBUG: mcp23s17 manager debug mode=on, init start, SPI baudrate={:.2f}mhz'.format(SPI_BAUDRATE/1e6))
            
        mcp_reset = Pin(MCP_RESET, Pin.OUT, value=HI)
        mcp_reset.value(LO)
        mcp_reset.value(HI)
        
        for key, value in self.LOOKUP.items():
            if value[0] == 2: # if Z80 signal then put active low pins in input mode with weak pullup
            _ = Pin(value[1], Pin.IN, pull=Pin.PULL_UP)

        self.cs  = Pin(SPI_CS, Pin.OUT)
        self.spi = SPI(id=SPI_PORT,baudrate=SPI_BAUDRATE,polarity=0,phase=0,bits=8,firstbit=SPI.MSB,sck=Pin(SPI_SCK),mosi=Pin(SPI_MOSI),miso=Pin(SPI_MISO))
        self.cs.value(LO); self.spi.write( bytes([CTRL_WR, IOCONA, IOCON_DEFAULT]) ); self.cs.value(HI) # enable HAEN, disable Sequential
        self.tristate() # all busses in tristate with weak pull up

# -------------------------- methods to control mcp23s17 and Pico --------------------------
    def read_bus(self, bus):
        chip, bank = self.LOOKUP[bus]
        self.cs.value(LO); self.spi.write( bytes([CTRL_WR|(chip<<1), IODIRA+bank, IODIR_READ]) ); self.cs.value(HI)
        self.cs.value(LO); self.spi.write( bytes([CTRL_RD|(chip<<1), GPIOA+bank]) ); data = self.spi.read(1); self.cs.value(HI)
        data = int.from_bytes(data, byteorder) if bus != 'ADDR_H2' else int.from_bytes(data & (IODIR_READ-ADDR_H2_MASK), byteorder) # mask off non-address bits
        if self.debug:
            print('DEBUG: READ MCP23S17 SIGNAL {}, CHIP:{}, BANK:{}, DATA:{:08b}'.format(signal, chip, bank, data))
        return data

    def write_bus(self, bus, data):
        if not self.got_bus:
            raise RuntimeError('ERROR: Trying to write to Z80 bus {} without BUSAK low') # maybe remove this when all working
        chip, bank = self.LOOKUP[signal]
        iodir = IODIR_WRITE if bus != 'ADDR_H2' else ADDR_H2_MASK # ensure WAIT and M1 are always read
        self.cs.value(LO); self.spi.write( bytes([CTRL_WR|(chip<<1), IODIRA+bank, iodir]) ); self.cs.value(HI)
        if self.debug:
            print('DEBUG: WROTE MCP23S17 SIGNAL: {}, CHIP:{}, BANK:{}, IODIR:{:08b}'.format(signal, chip, bank, iodir))
        self.cs.value(LO); self.spi.write( bytes([CTRL_WR|(chip <<1), OLATA+bank, data ]) ); self.cs.value(HI)
        if self.debug:
            print('DEBUG: WROTE MCP23S17 SIGNAL: {}, CHIP:{}, BANK:{}, DATA:{:08b}'.format(signal, chip, bank, data))
            
    def read_signal(self, signal):    
        chip, pin = self.LOOKUP[signal]
        data = Pin(pin, Pin.IN).value()
        if self.debug:
            print('DEBUG: READ PICO SIGNAL:{}, PIN:{}, VALUE:{:08b}'.format(signal, pin, data))
        return data
    
    def write_signal(self, signal, data):
        if not self.got_bus and signals[0] not in ('BUSRQ', 'RESET', 'NMI', 'INT'):
            raise RuntimeError('ERROR: Trying to write to Z80 bus {} without BUSAK low') # maybe remove this when all working
        chip, pin = self.LOOKUP[signal]
        if isinstance(pins, list): # reads and writes to memory or io need two signals setting to same value
            _ = Pin(pin[0], Pin.OUT, value=data)
            _ = Pin(pin[1], Pin.OUT, value=data)
        else:
            _ = Pin(pin, Pin.OUT, value=data)
        if self.debug:
            print('DEBUG: WRITE PICO SIGNAL:{}, PIN:{}, VALUE:{:08b}'.format(signal, pin, data))
        
    def tristate(self, bus_name=None):
        bus_names = [bus_name,] if bus_name else ('ADDR_H2','ADDR_H1','ADDR_LO', 'DATA')
        for bus_name in bus_names: # reset address and data busses to read mode (tristate) with weak pullup
            chip, bank = self.LOOKUP[bus_name]
            self.cs.value(LO); self.spi.write( bytes([CTRL_WR | (chip <<1), GPPUAA+bank, 0xFF]) );       self.cs.value(HI)
            self.cs.value(LO); self.spi.write( bytes([CTRL_WR | (chip <<1), IODIRA+bank, IODIR_READ]) ); self.cs.value(HI)

        for _, value in self.LOOKUP.items(): # reset Z80 control signals to input mode with weak pullup
            if value[0] == 2:
            _ = Pin(value[1], Pin.IN, pull=Pin.PULL_UP)

    def m1_interrupt(self, action):
        chip, bank = self.LOOKUP[signal]
        if action == 'on':
#             self.cs.value(LO)
#             self.spi.write( bytes([CTRL_WR | (chip <<1), INTCONA +bank, mask]) )  # interrupt if signal changes
#             self.cs.value(HI)            
#             self.cs.value(LO)
#             self.spi.write( bytes([CTRL_WR | (chip <<1), DEFVALA +bank, mask]) )  # from value mask
#             self.cs.value(HI)
            self.cs.value(LO); self.spi.write( bytes([CTRL_WR | (chip <<1), GPINTENA+bank, mask]) ); self.cs.value(HI)  # enable interrupt on mask signal     
        elif action == 'off':
            self.cs.value(LO); self.spi.write( bytes([CTRL_WR | (chip <<1), GPINTENA+bank, 0]) ); self.cs.value(HI)     # disable interrupts
        elif action == 'clear':
            self.cs.value(LO); self.spi.write( bytes([CTRL_RD | (chip <<1), GPIOA + bank]) ); _ = self.spi.read(1); self.cs.value(HI) # clear interrupt  
        if self.debug:
            print('DEBUG: MCP23S17 INTERRUPT on {} set to {}'.format(signal, action))


# -------------------------- methods to control Z80 buses and signals --------------------------
    def control(self, option): # grab and release control of Z80 buses
        if option == 'grab':
            self.write_signal('BUSRQ', LO) 
            if self.read_signal('BUSAK') != LO: # check if Z80 released buses
                raise RuntimeError('ERROR: Couldnt grab bus, Z80 not responding')
            self.got_bus = True
        elif option == 'release':
            self.tristate()
            self.got_bus = False
        if self.debug:
            print('DEBUG: bus manager {} Z80 bus'.format(option))

    def read(self, address, request): # read from Z80 memory or i/o
        if not self.got_bus:
            raise RuntimeError('Trying to access bus without BUSAK low active') # protect against program bugs
        if request == 'io':
            self.write_bus('ADDR_LO', address & 0x00FF) 
            self.write_signal('IORQ_RD', LO)
        else:
            self.write_bus('ADDR_H2', address >> 16)
            self.write_bus('ADDR_H1', address >> 8)
            self.write_bus('ADDR_LO', address & 0x00FF) 
            self.write_signal('MREQ_RD', LO)
        data = self.read_bus('DATA')
        return data
        
    def write(self, address, data):   # write to Z80 memory or i/o 
        if not self.got_bus:
            raise RuntimeError('Trying to access bus without BUSAK low active') # protect against program bugs
        if request == 'io':
            self.write_bus('ADDR_LO', address & 0x00FF)
            self.write_bus('DATA', data)
            self.write_signal('IORQ_WR', LO)
        else:
            self.write_bus('ADDR_H2', address >> 16)
            self.write_bus('ADDR_H1', address >> 8)
            self.write_bus('ADDR_LO', address & 0x00FF)
            self.write_bus('DATA', data)
            self.write_signal('MREQ_RD', LO)      
 
 