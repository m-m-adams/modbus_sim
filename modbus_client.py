import time
from pymodbus.client.tcp import ModbusTcpClient

# Connect to the Modbus TCP server
client = ModbusTcpClient('localhost', port=5502)
print(client.read_device_information().information)

while True:
    # Read the values from the Modbus registers
    target_temp = client.read_holding_registers(address=0, count=1, slave=0).registers[0]

    current_temp = client.read_holding_registers(address=56, count=1).registers[0]

    # Should check for errors here... i.e.
    cold = (target_temp < current_temp)

    #set coil 1 of slave 1 (heater) on to turn on heat
    client.write_coil(0, cold, slave=1)

    # Print the values
    #print("Coils:", coils.bits)
    #print("Discrete Inputs:", discrete_inputs.bits)
    print("Target Temp:", target_temp)
    print("Current Temp:", current_temp)

    client.write_register(address=0, value=22)
    time.sleep(5)
client.close()