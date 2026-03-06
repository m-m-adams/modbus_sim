FROM ubuntu:latest

RUN apt update -y
RUN apt install python3 python3-pip -y
RUN pip3 install pymodbus==3.8.5 twisted --break-system-packages
ADD generator.py /home/generator.py
ADD modbus_server.py /home/modbus_server.py
CMD ["--hostname", "0.0.0.0", "--port", "502"]
ENTRYPOINT ["python3", "/home/modbus_server.py"]