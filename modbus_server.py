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

num_temps = 7



def read_temperature(register: ModbusSlaveContext, temp):

    temps = register.getValues(4, 1, num_temps)
    print(temps)
    new_temp = int(random.normalvariate(temp, 0.5))
    new_temp = max(0, new_temp)
    
    temps.append(new_temp)

    register.setValues(4, 1, temps[1:num_temps+1])
    
def update_temperature(register: ModbusSlaveContext, current_temperature: float):

    target_temp = register.getValues(3, 0, 1)[0]
    print(f'target temp is {target_temp}, current is {current_temperature}')
    current_temperature = current_temperature + (target_temp - current_temperature)/5
    return current_temperature

async def updating_writer(a: ModbusServerContext):
    current_temperature = 0
    while True:
        await asyncio.sleep(1)
        print(f'temp is {current_temperature}')
        s: ModbusSlaveContext = a[0]
        read_temperature(s, current_temperature)
        print(f'updating temperature')
        current_temperature = update_temperature(s, current_temperature)
    


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
    input_registers.setValues(1, temperature_values)
    holding_registers.setValues(1,[22])

    # Define the Modbus slave context
    slave_context = ModbusSlaveContext(
        di=discrete_inputs,
        co=coils,
        hr=holding_registers,
        ir=input_registers
    )
    context = ModbusServerContext(slaves=slave_context, single=True)
    
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
    task = asyncio.create_task(updating_writer(context))
    
    await StartAsyncTcpServer(context=context, identity=identity, address=("localhost", 5502))


if __name__ == "__main__":
    asyncio.run(run_updating_server())