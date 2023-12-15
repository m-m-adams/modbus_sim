import time
import random
import logging
import argparse
from pymodbus.client.tcp import ModbusTcpClient



class GeneratorController:
    temperature: float
    target_temp: float
    speed: float
    desired_speed: float
    power_output: float
    desired_power: float
    cooling: bool
    overheated: bool = False
    max_temperature: bool = 75

    def __init__(self, client: ModbusTcpClient):
        self.client = client
        self.target_temp = 25
        self.desired_power = 300
        self.update()
        
    def read_temperatures(self):
        self.temperature = self.client.read_holding_registers(address=56, count=1, slave=0).registers[0]
        self.target_temp = self.client.read_holding_registers(address=0, count=1, slave=0).registers[0]
        cold = (self.target_temp < self.temperature)
        #set coil 1 of slave 1 (cooler) on to turn on air conditioning
        self.client.write_coil(0, cold, slave=1)
        self.cooling = cold

    def read_power(self):
        self.power_output = self.client.read_holding_registers(address=3, count=1, slave=2).registers[0]
        self.speed = self.client.read_holding_registers(address=4, count=1, slave=2).registers[0]
        power_req = self.desired_power
        if self.cooling:
            power_req += 100
        self.desired_speed = power_req / 5
        self.client.write_register(1, int(self.desired_speed), slave=2)
        self.client.write_register(2, int(self.desired_power), slave=2)

    def set_temperature(self):
        self.client.write_register(address=0, value=self.target_temp)
    
    def get_demand(self):
        increase = random.normalvariate(0, 15)
        if self.desired_power > 250:
            if increase > 0:
                increase /= 2
        elif increase < 0:
            increase /=2

        self.desired_power = self.desired_power + increase
        self.desired_power = max(min(self.desired_power, 500), 0)
        


    def update(self):
        self.read_temperatures()
        self.set_temperature()
        self.get_demand()
        self.read_power()
        logging.log(logging.INFO, f"desired power: {self.desired_power}\nactual power: {self.power_output}")

if __name__ == "__main__":
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--hostname", nargs='?', type=str, default="localhost")
    parser.add_argument("--port", nargs='?', type=int, default=502)
    args = parser.parse_args()
    logging.log(logging.INFO, f"connecting to {args.hostname}:{args.port}")
    # Connect to the Modbus TCP server
    client = ModbusTcpClient(args.hostname, port=args.port)
    logging.log(logging.INFO, client.read_device_information().information)
    controller = GeneratorController(client)


    while True:
        controller.update()
        time.sleep(5)
    client.close()