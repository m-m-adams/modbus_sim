import random
import logging
import asyncio
import math
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.server.async_io import StartTcpServer, StartAsyncTcpServer
from twisted.internet.task import LoopingCall

# Enable logging (makes it easier to debug if something goes wrong)
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)
hot = 75
cold = 5
num_temps = 7
class Heater:
    heat_steps = 10
    on_last_time = False
    def __init__(self, s_temp: ModbusSlaveContext, s_heat: ModbusSlaveContext, temperature:float):
        self.current_temperature = temperature
        self.ctx_temp = s_temp
        self.ctx_heat = s_heat

    def read_temperature(self,):
        temps = self.ctx_temp.getValues(3, 50, num_temps)
        new_temp = (random.normalvariate(self.current_temperature, 0.25))
        logging.log(logging.DEBUG, f'temp is {new_temp}')
        new_temp = int(max(0, new_temp))
        temps.append(new_temp)

        self.ctx_temp.setValues(3, 50, temps[1:num_temps+1])
        
    def turn_heat_on(self):

        target_temp = self.ctx_temp.getValues(3, 1, 1)[0]
        current_temp = self.ctx_temp.getValues(3, 56, 1)[0]
        logging.log(logging.DEBUG, f'target temp is {target_temp}, current is {current_temp}')
        amount = (target_temp > current_temp)
        #set coil 1 of slave 1 (heater) on to turn on heat
        self.ctx_heat.setValues(1, 0, [amount])
        

    def heat(self):
        on = self.ctx_heat.getValues(1,0)[0]
        
        if on:
            #set coil 2 on to indicate heat running
            self.ctx_heat.setValues(1,2,[True]) 
            self.ctx_heat.setValues(3, 1, [2])
        running = self.ctx_heat.getValues(1,2,1)[0]
        logging.log(logging.DEBUG, f'heat is switched {"on" if on else "off"} and {"running" if running else "not running"}')
        if running:
            r = self.ctx_heat.getValues(3, 1)[0] - 1
            if r >= 1:
                self.ctx_heat.setValues(6, 1, [r-1])
                self.current_temperature = self.current_temperature + (hot - self.current_temperature)/10
            else:
                self.ctx_heat.setValues(1,2,[False]) 

        else:
            self.ctx_heat.setValues(1,2,[False]) 
            self.current_temperature = self.current_temperature + (cold - self.current_temperature)/15


    async def updating_writer(self):

        while True:
            await asyncio.sleep(1)
            self.read_temperature()
            #self.turn_heat_on()
            self.heat()
    


async def run_updating_server():
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
    heater_holding = ModbusSequentialDataBlock(1, [False] * 100)
    heater_holding.setValues(1, [10])
    heater_slave_context = ModbusSlaveContext(
        co=heater_coils,
        hr=holding_registers
    )
    context = ModbusServerContext(slaves={0:sensor_slave_context, 1:heater_slave_context}, single=False)
    
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
    time = 5  # 5 seconds delay
    heater = Heater(context[0], context[1], 22.5)
    task = asyncio.create_task(heater.updating_writer())
    
    await StartAsyncTcpServer(context=context, identity=identity, address=("localhost", 5502))


if __name__ == "__main__":
    asyncio.run(run_updating_server())