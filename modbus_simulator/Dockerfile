FROM ubuntu:latest

RUN apt-get update
RUN apt-get install python

ADD generator.py /home/generator.py
ADD modbus_server.py /home/modbus_server.py

CMD ["/home/modbus_server.py"]
ENTRYPOINT [ "python" ]