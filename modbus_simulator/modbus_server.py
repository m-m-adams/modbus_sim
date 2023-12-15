import random
import logging
import asyncio
import math
import generator
import argparse
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.server.async_io import StartTcpServer, StartAsyncTcpServer
from twisted.internet.task import LoopingCall

# Enable logging (makes it easier to debug if something goes wrong)
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)
hot = 75
cold = 5
num_temps = 7
class Heater:
    heat_steps = 2
    on_last_time = False
    def __init__(self, s: ModbusServerContext):
        self.generator = generator.Generator()
        self.ctx_temp: ModbusSlaveContext = s[0]
        self.ctx_cooling: ModbusSlaveContext = s[1]
        self.ctx_generator: ModbusSlaveContext = s[2]

    def read_temperature(self,):
        temps = self.ctx_temp.getValues(3, 50, num_temps)
        new_temp = self.generator.get_temp()
        logging.log(logging.INFO, f'temp is {new_temp}')
        new_temp = int(max(0, new_temp))
        temps.append(new_temp)
        self.ctx_temp.setValues(3, 50, temps[1:num_temps+1])
        

    def update_cooling(self):
        on = self.ctx_cooling.getValues(1,0)[0]
        
        if on:
            #set coil 2 on to indicate heat running
            self.ctx_cooling.setValues(1,2,[True]) 
            self.ctx_cooling.setValues(3, 1, [2])
        running = self.ctx_cooling.getValues(1,2,1)[0]
        self.generator.cooling = bool(running)
        logging.log(logging.INFO, f'cooling is switched {"on" if on else "off"} and {"running" if running else "not running"}')
        if running:
            r = self.ctx_cooling.getValues(3, 1)[0] - 1
            if r >= 1:
                self.ctx_cooling.setValues(6, 1, [r-1])
            else:
                self.ctx_cooling.setValues(1,2,[False]) 

        else:
            self.ctx_cooling.setValues(1,2,[False]) 

    def update_generator(self):
        desired_speed = self.ctx_generator.getValues(3, 1, 1)
        desired_power = self.ctx_generator.getValues(3, 2, 1)
        self.generator.desired_speed = desired_speed[0]

        output_power = self.generator.power_output
        self.ctx_generator.setValues(6,3,[output_power])

        speed = self.generator.speed
        self.ctx_generator.setValues(6,4,[speed])
        logging.log(logging.INFO, f"speed is {speed}, desired is {desired_speed[0]}")
        logging.log(logging.INFO, f"power is {output_power}, desired is {desired_power[0]}")



    async def updating_writer(self):

        while True:
            await asyncio.sleep(1)
            self.read_temperature()
            #self.turn_heat_on()
            self.update_cooling()

            self.update_generator()
            #physical simulation
            self.generator.update()
    


async def run_updating_server(hostname="localhost", port=5502):
    # ----------------------------------------------------------------------- # 
    # initialize your data store
    # ----------------------------------------------------------------------- # 
    
    # Define the Modbus registers
    coils = ModbusSequentialDataBlock(1, [False] * 100)
    discrete_inputs = ModbusSequentialDataBlock(1, [False] * 100)
    holding_registers = ModbusSequentialDataBlock(1, [0] * 100)
    input_registers = ModbusSequentialDataBlock(1, [0] * 100)
    temperature_values = [random.randint(4, 15) for _ in range(num_temps)]
    holding_registers.setValues(50, temperature_values)
    holding_registers.setValues(1,[22])

    # Define the Modbus slave context
    sensor_slave_context = ModbusSlaveContext(
        di=discrete_inputs,
        co=coils,
        hr=holding_registers,
        ir=input_registers
    )
    heater_coils = ModbusSequentialDataBlock(1, [False] * 100)
    heater_holding = ModbusSequentialDataBlock(1, [0] * 100)
    heater_holding.setValues(1, [10])
    heater_slave_context = ModbusSlaveContext(
        co=heater_coils,
        hr=holding_registers
    )

    generator_coils = ModbusSequentialDataBlock(1, [False] * 100)
    generator_holding = ModbusSequentialDataBlock(1, [0] * 100)
    generator_holding.setValues(2, 25)
    generator_slave_context = ModbusSlaveContext(
        co=generator_coils,
        hr=generator_holding
    )

    context = ModbusServerContext(slaves={0:sensor_slave_context, 1:heater_slave_context, 2:generator_slave_context}, single=False)
    
    # ----------------------------------------------------------------------- # 
    # initialize the server information
    # ----------------------------------------------------------------------- # 
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'TestModbusServer'
    identity.ProductCode = '1337'
    identity.ProductName = 'Simple fake Server'

    
    # ----------------------------------------------------------------------- # 
    # run the server you want
    # ----------------------------------------------------------------------- # 

    heater = Heater(context)
    task = asyncio.create_task(heater.updating_writer())
    
    await StartAsyncTcpServer(context=context, identity=identity, address=(hostname, port))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--hostname", nargs='?', type=str, default="localhost")
    parser.add_argument("--port", nargs='?', type=int, default=5502)
    args = parser.parse_args()
    logging.log(logging.INFO, f"starting at {args.hostname}:{args.port}")
    asyncio.run(run_updating_server(args.hostname, args.port))