import math

class generator:
    temperature: float
    speed: float
    desired_speed: float
    power_output: float
    heat_output: float
    cooling: bool
    cooling_output: float
    mass:float = 100.0
    acceleration:float = 10.0
    overheated: bool = False

    def __init__(self):
        self.temperature = 15
        self.speed = 0
        self.desired_speed = 20
        self.power_output = 0
        self.heat_output = 15
        self.cooling = False
        self.cooling_output = 10
        self.max_temperature = 75


    def update(self):
        delta_v = self.desired_speed - self.speed
        if self.overheated or delta_v < 0:
            self.speed -= min(delta_v, 2)
        else:
            self.speed += min(delta_v, 10)

        self.speed = max(min(self.speed, 100), 0)

        self.power_output = self.speed * 5
        self.heat_output = self.speed
        
        if self.cooling:
            self.temperature = self.temperature + (self.cooling_output - self.temperature)/10
            self.power_output -= 100
        else:
            self.temperature = self.temperature + (self.heat_output - self.temperature)/10
        
        if self.temperature > self.max_temperature:
            self.overheated = True

        if self.overheated and self.temperature < 20:
            self.overheated = False
