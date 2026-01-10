import bme680
import time
from .peripheral import Sensor
from .msg import EnvMessage


class BME680_EnvSensor(Sensor):
    """
    BME680 Environmental Sensor (Temperature, Humidity, Pressure, Gas)
    """
    _PRIMARY_ADDRESS = 0x76
    _SECONDARY_ADDRESS = 77
    _MAX_FREQUENCY = 180.0
    _FREQUENCY = 10.0

    def __init__(self):
        super().__init__(
            name="EnvSensor", 
            connections={'i2c': {'slave_address': '0x76', 'pins': {'sda': {'name': 'sda', 'id': None}, 'scl': {'name': 'scl', 'id': None}}}}, 
            attributes={'poll_period': 10, 'humidity_oversample': 2, 'pressure_oversample': 4, 'temperature_oversample': 8, 'filter_size': 3, 'gas_status': 'ENABLE_GAS_MEAS', 'heater_temp': 320, 'heater_duration': 150, 'heater_profile': 0}
        )
        self.sensor = None

    def initialize(self):
        """Initialize the sensor hardware"""
        try:
            self.sensor = bme680.BME680(self._PRIMARY_ADDRESS)
        except (RuntimeError, IOError):
            self.sensor = bme680.BME680(self._SECONDARY_ADDRESS)

        # Initializing parameters
        self.sensor.set_humidity_oversample(bme680.OS_2X)
        self.sensor.set_pressure_oversample(bme680.OS_4X)
        self.sensor.set_temperature_oversample(bme680.OS_8X)
        self.sensor.set_filter(bme680.FILTER_SIZE_3)

        self.sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)
        self.sensor.set_gas_heater_temperature(320)
        self.sensor.set_gas_heater_duration(150)
        self.sensor.select_gas_heater_profile(0)

    def read(self):
        """Read sensor data"""
        if self.sensor.get_sensor_data():
            data = {
                "temperature": self.sensor.data.temperature,
                "pressure": self.sensor.data.pressure,
                "humidity": self.sensor.data.humidity
            }
            if self.sensor.data.heat_stable:
                data["gas_resistance"] = self.sensor.data.gas_resistance
            else:
                data["gas_resistance"] = 0.0
            
            self.update_state_data(data)

    def disconnect(self):
        """Release hardware resources"""
        pass