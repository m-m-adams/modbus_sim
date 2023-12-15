import random
import logging
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.server.async_io import StartTcpServer

# Enable logging (makes it easier to debug if something goes wrong)
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

# Define the Modbus registers
coils = ModbusSequentialDataBlock(1, [False] * 100)
discrete_inputs = ModbusSequentialDataBlock(1, [False] * 100)
holding_registers = ModbusSequentialDataBlock(1, [0] * 100)
input_registers = ModbusSequentialDataBlock(1, [0] * 100)

temperature_values = [random.randint(4, 15) for _ in range(7)]
holding_registers.setValues(1, temperature_values)
print("temperature_values:", temperature_values)


# Define the Modbus slave context
slave_context = ModbusSlaveContext(
    di=discrete_inputs,
    co=coils,
    hr=holding_registers,
    ir=input_registers
)

# Define the Modbus server context
server_context = ModbusServerContext(slaves=slave_context, single=True)

# Start the Modbus TCP server
StartTcpServer(context=server_context, address=("localhost", 5502))