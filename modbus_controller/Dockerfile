FROM ubuntu:latest

RUN apt update -y
RUN apt install python3 python3-pip -y
RUN pip3 install pymodbus twisted
ADD modbus_client.py /home/modbus_client.py
CMD ["--hostname", "localhost", "--port", "5502"]
ENTRYPOINT ["python3", "/home/modbus_client.py"]