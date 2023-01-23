class MCP23S17:
    def __init__(self, qwe):
        pass
    

class Buscontrol:
    def __init__(self, debug):
        self.ctrl = MCP23S17(0)
        self.addr = MCP23S17(1)
        self.data = MCP23S17(2)
        self.debug = debug
        
    def read_loc(self, address):
        return randint(0, 255)

    def write_loc(self, address, data):
        pass


if __name__ == '__main__':
    print('Run Bus Control')
    