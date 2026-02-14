# Supported Sensors and Actuators

DeMoL supports a comprehensive range of IoT sensors and actuators based on industry standards and common smart home, industrial automation, and environmental monitoring applications.

## Sensor Types (35 Types)

All sensors use the syntax: `SENSOR[Type] ComponentName`

### Environmental Sensors

| Type | Description | Message Schema | Common Uses |
|------|-------------|----------------|-------------|
| `Temperature` | Temperature sensors | `{ "value": float, "unit": "C\|F\|K", "timestamp": int }` | Climate control, HVAC |
| `Humidity` | Relative humidity sensors | `{ "value": float, "unit": "%", "timestamp": int }` | Weather stations, greenhouses |
| `Pressure` | Barometric pressure sensors | `{ "value": float, "unit": "Pa\|hPa\|bar", "timestamp": int }` | Weather prediction, altitude |
| `Gas` | Gas detection sensors | `{ "type": string, "concentration": float, "unit": "ppm", "timestamp": int }` | Air quality, safety monitoring |
| `Env` | Multi-parameter environmental | `{ "temperature": float, "humidity": float, "pressure": float, "gas": float, "timestamp": int }` | Comprehensive environmental monitoring |
| `AirQuality` | Air quality index sensors | `{ "aqi": int, "pm25": float, "pm10": float, "co2": float, "timestamp": int }` | Indoor air quality monitoring |
| `Light` | Ambient light sensors | `{ "lux": float, "timestamp": int }` | Automatic lighting, displays |
| `UV` | UV radiation sensors | `{ "index": float, "intensity": float, "timestamp": int }` | Sun exposure monitoring |
| `Sound` | Sound level sensors | `{ "level": float, "unit": "dB", "frequency": float, "timestamp": int }` | Noise monitoring, smart home |

### Motion & Position Sensors

| Type | Description | Message Schema | Common Uses |
|------|-------------|----------------|-------------|
| `Distance` | Ultrasonic/ToF distance | `{ "distance": float, "unit": "cm\|m", "timestamp": int }` | Proximity detection, robotics |
| `Proximity` | Binary proximity detection | `{ "value": bool, "distance": float, "timestamp": int }` | Object detection, automation |
| `Motion` | PIR motion sensors | `{ "value": bool, "timestamp": int }` | Security, auto-lighting |
| `Presence` | Presence detection | `{ "value": bool, "count": int, "timestamp": int }` | Occupancy sensing, smart buildings |
| `Acceleration` | Accelerometers | `{ "x": float, "y": float, "z": float, "unit": "m/s²", "timestamp": int }` | Vibration, orientation |
| `Gyroscope` | Angular velocity sensors | `{ "x": float, "y": float, "z": float, "unit": "rad/s\|deg/s", "timestamp": int }` | Orientation, stabilization |
| `Magnetometer` | Magnetic field sensors | `{ "x": float, "y": float, "z": float, "unit": "µT", "heading": float, "timestamp": int }` | Compass, navigation |
| `IMU` | Inertial Measurement Unit | `{ "accel": {x,y,z}, "gyro": {x,y,z}, "mag": {x,y,z}, "timestamp": int }` | Drones, robotics, VR/AR |
| `Tracker` | Position tracking | `{ "x": float, "y": float, "z": float, "velocity": float, "timestamp": int }` | Asset tracking, logistics |

### Specialized Sensors

| Type | Description | Message Schema | Common Uses |
|------|-------------|----------------|-------------|
| `ADC` | Analog-to-Digital Converter | `{ "channel": int, "value": int, "voltage": float, "timestamp": int }` | Generic analog sensing |
| `Current` | Current measurement | `{ "current": float, "unit": "mA\|A", "timestamp": int }` | Power monitoring, battery |
| `Voltage` | Voltage measurement | `{ "voltage": float, "unit": "V", "timestamp": int }` | Power monitoring, batteries |
| `Power` | Power consumption | `{ "power": float, "unit": "W\|kW", "voltage": float, "current": float, "timestamp": int }` | Energy monitoring |
| `Flow` | Fluid flow sensors | `{ "rate": float, "unit": "L/min\|m³/h", "total": float, "timestamp": int }` | Water/gas metering |
| `Level` | Liquid level sensors | `{ "level": float, "unit": "cm\|%", "full": bool, "timestamp": int }` | Tank monitoring |
| `Weight` | Load cells, weight sensors | `{ "weight": float, "unit": "g\|kg", "timestamp": int }` | Scales, inventory |
| `Force` | Force sensors | `{ "force": float, "unit": "N", "timestamp": int }` | Robotics, testing |
| `Vibration` | Vibration sensors | `{ "amplitude": float, "frequency": float, "timestamp": int }` | Predictive maintenance |

### Smart Sensors

| Type | Description | Message Schema | Common Uses |
|------|-------------|----------------|-------------|
| `Camera` | Image/video capture | `{ "image": string, "format": "jpeg\|png", "width": int, "height": int, "timestamp": int }` | Surveillance, vision systems |
| `RFID` | RFID tag readers | `{ "tag_id": string, "tag_type": string, "rssi": int, "timestamp": int }` | Access control, inventory |
| `Fingerprint` | Biometric fingerprint | `{ "match": bool, "confidence": float, "user_id": string, "timestamp": int }` | Security, authentication |
| `GPS` | GPS positioning | `{ "latitude": float, "longitude": float, "altitude": float, "speed": float, "satellites": int, "timestamp": int }` | Navigation, tracking |
| `Color` | Color sensors | `{ "r": int, "g": int, "b": int, "hex": string, "timestamp": int }` | Sorting, quality control |

## Actuator Types (23 Types)

All actuators use the syntax: `ACTUATOR[Type] ComponentName`

### Basic Actuators

| Type | Description | Command Schema | Common Uses |
|------|-------------|----------------|-------------|
| `MotorController` | DC motor controllers | `{ "motor_id": int, "speed": float, "direction": "cw\|ccw\|brake", "timestamp": int }` | Robotics, automation |
| `ServoController` | Servo motor controllers | `{ "servo_id": int, "angle": float, "speed": float, "timestamp": int }` | Robotics, pan-tilt |
| `Relay` | Electromechanical relays | `{ "state": "on\|off", "channel": int, "timestamp": int }` | Power switching, automation |
| `Switch` | Electronic switches | `{ "state": bool, "channel": int, "timestamp": int }` | General switching |

### Display & Light Actuators

| Type | Description | Command Schema | Common Uses |
|------|-------------|----------------|-------------|
| `Led` | Single LED | `{ "state": bool, "brightness": int, "timestamp": int }` | Status indicators |
| `LedArray` | LED arrays/strips | `{ "pattern": string, "brightness": int, "color": string, "timestamp": int }` | Lighting, signage |
| `NeoPixel` | Addressable RGB LEDs | `{ "leds": [{index, r, g, b}], "brightness": int, "mode": string, "timestamp": int }` | Decorative lighting, displays |
| `Display` | Generic displays | `{ "text": string, "line": int, "column": int, "timestamp": int }` | Information display |
| `LCD` | LCD displays | `{ "text": string, "row": int, "col": int, "backlight": bool, "timestamp": int }` | Character displays |
| `OLED` | OLED displays | `{ "text": string, "x": int, "y": int, "font": string, "clear": bool, "timestamp": int }` | Graphical displays |

### Sound Actuators

| Type | Description | Command Schema | Common Uses |
|------|-------------|----------------|-------------|
| `Buzzer` | Piezo buzzers | `{ "frequency": int, "duration": int, "pattern": string, "timestamp": int }` | Alerts, notifications |
| `Speaker` | Audio speakers | `{ "audio": string, "volume": int, "format": string, "timestamp": int }` | Audio playback, voice |

### Advanced Actuators

| Type | Description | Command Schema | Common Uses |
|------|-------------|----------------|-------------|
| `Stepper` | Stepper motor controllers | `{ "steps": int, "direction": string, "speed": int, "acceleration": int, "timestamp": int }` | Precision positioning, 3D printers |
| `DCMotor` | DC motor drivers | `{ "speed": float, "direction": string, "acceleration": float, "timestamp": int }` | Wheeled robots, fans |
| `Pump` | Fluid pumps | `{ "state": bool, "flow_rate": float, "duration": int, "timestamp": int }` | Irrigation, liquid handling |
| `Valve` | Solenoid valves | `{ "state": "open\|closed", "position": float, "timestamp": int }` | Fluid control, HVAC |
| `Heater` | Heating elements | `{ "state": bool, "temperature": float, "power": float, "timestamp": int }` | Temperature control |
| `Cooler` | Cooling systems | `{ "state": bool, "speed": int, "target_temp": float, "timestamp": int }` | Thermal management |
| `Fan` | Cooling fans | `{ "state": bool, "speed": int, "pwm": int, "timestamp": int }` | Ventilation, cooling |

## Message Schema Conventions

All message schemas include a `timestamp` field (Unix epoch in milliseconds) for temporal ordering and synchronization.

### Common Units

- **Temperature**: `C` (Celsius), `F` (Fahrenheit), `K` (Kelvin)
- **Distance**: `mm`, `cm`, `m`, `km`
- **Pressure**: `Pa`, `hPa`, `bar`, `psi`
- **Power**: `µW`, `mW`, `W`, `kW`
- **Current**: `µA`, `mA`, `A`
- **Voltage**: `V`, `mV`
- **Frequency**: `Hz`, `kHz`, `MHz`, `GHz`
- **Flow**: `L/min`, `m³/h`, `gal/min`
- **Weight**: `g`, `kg`, `lb`

### Message Types

- **Sensor Messages** (Publisher): Sensors publish data to topics
- **Actuator Commands** (Subscriber): Actuators subscribe to command topics
- **Bidirectional** (Both): Some devices support both publishing status and receiving commands

## Example Usage

### Environmental Sensor
```
SENSOR[Env] BME680 WITH
    OP
        vcc=5V,
        ioVcc=3V3,
        energy=0.01 mW, 39.6 mW, 3 mW
    PINS
        vcc[5V] @ 1,
        gnd[GND] @ 5,
        sda[sda-0] @ 2,
        scl[scl-0] @ 3
    ATTRIBUTES
        poll_period[int] = 10,
        gas_status[str] = "ENABLE_GAS_MEAS"
;
```

### Addressable LED Actuator
```
ACTUATOR[NeoPixel] WS2812 WITH
    OP
        vcc=5V
    PINS
        VCC[5V] @ 1,
        GND[GND] @ 2,
        DIN[gpio,mosi-0] @ 3
    ATTRIBUTES
        num_leds[int] = 12,
        color_format[str] = "GRB",
        brightness[float] = 0.5
;
```

## Adding Custom Types

To add new sensor or actuator types:

1. Update `demol/grammar/component.tx`
2. Add the type to `SensorType` or `ActuatorType` enum
3. Define the message schema in your documentation
4. Create `.hwd` model files for specific components
5. Validate with: `python scripts/validate_builtin_models.py`
