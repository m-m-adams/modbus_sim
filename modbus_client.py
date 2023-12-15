import random
import logging
import time
from pymodbus.client.tcp import ModbusTcpClient
from pymodbus import mei_message

# Connect to the Modbus TCP server
client = ModbusTcpClient('localhost', port=5502, slave=0)
print(client.connect())

print(client.read_device_information().information)
# Read the values from the Modbus registers
holding_registers = client.read_holding_registers(address=1, count=1)

input_registers = client.read_input_registers(address=1, count=7)

# Should check for errors here... i.e.


# Print the values
#print("Coils:", coils.bits)
#print("Discrete Inputs:", discrete_inputs.bits)
print("Holding Registers:", holding_registers.registers)
print("Input Registers:", input_registers.registers)

client.write_register(address=0, value=35)
print(client.read_holding_registers(address=0, count=1).registers)
client.close()