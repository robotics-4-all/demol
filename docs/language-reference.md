# DeMoL Language Reference

The DeMoL DSL is built using the [textX](http://textx.github.io/textX/) framework and provides a declarative approach to modeling IoT devices.

## Grammar Structure

The grammar is modular and split into **4 interconnected files** located in `demol/grammar/`:

| File               | Purpose                           | Key Concepts                        |
| ------------------ | --------------------------------- | ----------------------------------- |
| `device.tx`        | Main device model definition      | DeviceModel, Connect                |
| `component.tx`     | Board & peripheral hardware specs | Board, Sensor, Actuator, Pins       |
| `communication.tx` | Message broker configurations     | AMQPBroker, MQTTBroker, RedisBroker |
| `common.tx`        | Common utilities & types          | AttributeSet, VALUE, Imports        |

## Core Concepts

The language is built around these fundamental concepts:

- **Device** - Complete IoT device definition with metadata and configuration
- **Board** - Microcontroller/SBC hardware (ESP32, Raspberry Pi, etc.)
- **Peripheral** - External sensors and actuators (BME680, SRF04, etc.)
- **Connect** - Defines how peripherals connect to boards (power + data + remote)
- **SmartConnect** - Automatic pin assignment for peripherals (no manual wiring)
- **MessageBroker** - Communication infrastructure (MQTT, AMQP, Redis)
- **Network** - WiFi configuration

**File Extensions:**
- `.dev` - Device models (complete IoT device definitions)
- `.hwd` - Hardware component models (boards and peripherals)

## Device Model Structure

Every `.dev` file follows this structure:

```
DEVICE DeviceName WITH description="Device description", author="author_name", os=raspbian;

NETWORK[WiFi] WITH ssid="WiFi_SSID", password="password";

BROKER[MQTT] BrokerName WITH host="mqtt.example.com", port=1883, auth.username="user", auth.password="pass";

USE BoardModelName;
USE PeripheralModel1(InstanceName1), PeripheralModel2(InstanceName2);

CONNECT InstanceName1 WITH
    POWER
        board_pin -- peripheral_pin,
        board_pin2 -- peripheral_pin2
    DATA
        gpio[mode="output"] board_pin -- peripheral_pin
    @ "device/sensor/topic";
```

### Device Configuration

Describes the device and target platform using the `DEVICE` statement:

```
DEVICE SmartSensor WITH description="Environmental monitoring sensor", author="developer_name", os=raspbian;
```

**Target Operating Systems:**
- `raspbian` - For Raspberry Pi devices
- `riotos` - For embedded systems (ESP32, ESP8266, etc.)
- `freertos`, `arduino`, `esp-idf`, `esp-idf-rtos` - Other embedded platforms

### Network Configuration

WiFi network settings using the `NETWORK` statement:

```
NETWORK[WiFi] WITH ssid="IoT_Network", password="secure_password";
```

### Hardware Components

Specifies the hardware composition using `USE` statements:

```
USE RaspberryPi_4B_4GB;
USE BME680[EnvSensor] WITH poll_period = 5, SonarSRF04[DistanceSensor];
USE WS2812[StatusLED];
```

**Features:**
- `USE <BoardName>;` defines the main board.
- `USE <Peripheral>[<Name>];` defines peripherals.
- Board references are resolved from the global repository in `demol/builtin_models/boards/`
- Peripheral models are loaded from `demol/builtin_models/peripherals/`
- Supports multi-file imports using FQN (Fully Qualified Names)
- Named peripheral instances for easy reference in connections
- **Attributes can be overridden** using `WITH` syntax

### Attributes in Components

Peripheral attributes can be customized when declaring instances:

```
USE BME680[EnvSensor] WITH
    poll_period = 5,
    filter_size = 7
;

USE SonarSRF04[DistanceSensor] WITH
    max_distance = 300
;
```

**Key Points:**
- Attributes override peripheral default values
- Use `WITH` keyword after the instance name
- Comma-separated attribute assignments after `WITH`
- Comma-separated peripheral instances in the peripherals list
- Only override attributes you need to change
- Supports lists and dictionaries: `colors = ['0xFF0000', '0x00FF00']` or `config = {timeout = 5000}`

## Hardware Components

### Board Models

Boards are defined in `.hwd` files and describe microcontroller/SBC specifications using the `Board[Type] name` syntax:

```
BOARD[RPI] RaspberryPi_4B_4GB WITH
    OP
        vcc=5V,
        ioVcc=3V3,
        energy=1.4 W, 7.6 W, 3.5 W,  // min, max, avg power consumption
        memory.flash=16 gb,
        memory.ram=4 gb,
        cpu.family=PiArmCortex,
        cpu.freq=1500 mhz,
        cpu.fpu=true,
        wifi.name=RPi4_WiFi,
        wifi.version=5,
        wifi.bands=[2.4GHz, 5GHz],
        bluetooth=BT5
    PORTS
        spi=2,
        i2c=2,
        uart=2,
        gpio=28
    PINS
        power_5v[5V] @ 2,
        gnd_1[GND] @ 6,
        p_21[gpio,sda-1] @ 40,
        p_22[gpio,scl-1] @ 38
;
```

**Board Types:** `RPI` (Raspberry Pi), `ESP` (ESP32/ESP8266), `ARDUINO`

**Pin Syntax:**
- `name [type] @ number` - Power pins (VCC, GND)
- `name [funcs] @ number` - Digital/IO pins with functions

**Pin Functions:** `gpio`, `adc`, `dac`, `pwm-<channel>`, `sda-<bus>`, `scl-<bus>`, `mosi-<bus>`, `miso-<bus>`, `sck-<bus>`, `cs-<bus>`, `tx-<bus>`, `rx-<bus>`

**Power Types:** `GND`, `3V3`, `5V`, `12V`

### Peripheral Models (Sensors)

Sensors use the `Sensor[Type] name` syntax where Type indicates the sensor category and its message schema:

```
SENSOR[Env] BME680 WITH
    OP
        vcc=5V,
        ioVcc=3V3,
        energy=0.01 mW, 39.6 mW, 3 mW  // min, max, avg power consumption
    PINS
        vcc[5V] @ 1,
        gnd[GND] @ 5,
        sda[sda-0] @ 2,
        scl[scl-0] @ 3
    TEMPLATES
        raspbian="bme680.py.tmpl",
        riotos="bme680.c.tmpl"
    DEPENDENCIES
        raspbian = [
            {package="bme680", version=">=1.0.5", source="pip"},
            {package="libgpiod-dev", source="apt"}
        ]
    ATTRIBUTES
        poll_period[int] = 10,
        humidity_oversample[int] = 2,
        temperature_oversample[int] = 8,
        filter_size[int] = 3
;
```

**Dependency Specification:**
Peripherals can define their software dependencies per target OS. Dependencies can be simple strings (package names) or structured objects:
- **Simple String**: `raspbian=["gpiozero"]` (defaults to `pip` and latest version)
- **Structured Object**: `{package="name", version="spec", source="pip|apt"}`
  - `version`: Supports comparison operators like `>=2.0`, `<3.0`, `==1.2.3`, etc.
  - `source`: Specifies the package manager (`pip` for Python, `apt` for system packages).

**Available Sensor Types:** `Distance`, `Temperature`, `Humidity`, `Gas`, `Env`, `AirQuality`, `Light`, `UV`, `Sound`, `Acceleration`, `Gyroscope`, `Magnetometer`, `IMU`, `Tracker`, `Proximity`, `Motion`, `Presence`, `ADC`, `Current`, `Voltage`, `Power`, `Flow`, `Level`, `Weight`, `Force`, `Vibration`, `Camera`, `RFID`, `Fingerprint`, `GPS`, `Color`

For complete sensor type documentation and message schemas, see [Sensors & Actuators Reference](sensors-actuators.md).

### Peripheral Models (Actuators)

Actuators use the `Actuator[Type] name` syntax:

```
ACTUATOR[ServoController] PCA9685 WITH
    OP
        vcc=5V,
        ioVcc=5V
    PINS
        GND_1[GND] @ 1,
        SCL_1[scl-0] @ 2,
        SDA_1[sda-0] @ 3,
        VCC_1[5V] @ 4
    ATTRIBUTES
        num_servos[int] = 16,
        frequency[int] = 50
;
```

**Available Actuator Types:** `MotorController`, `ServoController`, `Relay`, `Switch`, `Led`, `LedArray`, `NeoPixel`, `Display`, `LCD`, `OLED`, `Buzzer`, `Speaker`, `Stepper`, `DCMotor`, `Pump`, `Valve`, `Heater`, `Cooler`, `Fan`

For complete actuator type documentation and command schemas, see [Sensors & Actuators Reference](sensors-actuators.md).

### Units

- **Memory:** `b`, `kb`, `mb`, `gb`
- **Frequency:** `hz`, `khz`, `mhz`, `ghz`
- **Distance:** `mm`, `cm`, `m`
- **Power:** `uW`, `mW`, `W`

## Connections

Connections define how peripherals connect to the board through power and IO pins.

### GPIO Connection

```
CONNECT DistanceSensor WITH
    POWER
        gnd_1 -- gnd,
        power_5v -- vcc
    DATA
        gpio[mode="output"] p_13 -- trigger,
        gpio[mode="input"] p_14 -- echo
    @ "sensors/distance";
```

### I2C Connection

```
CONNECT EnvSensor WITH
    POWER
        gnd_1 -- GND,
        power_5v -- VCC
    DATA
        i2c[slave_address=0x76] sda p_21 -- sda, scl p_22 -- scl
    @ "sensors/environment";
```

### SPI Connection

```
CONNECT DisplayModule WITH
    POWER
        gnd_1 -- GND,
        power_3v3 -- VCC
    DATA
        spi[bus_speed=1000000, mode=0] mosi p_23 -- mosi, miso p_19 -- miso, sck p_18 -- sck, cs p_5 -- cs;
```

### UART Connection

```
CONNECT GPSModule WITH
    POWER
        gnd_1 -- GND,
        power_5v -- VCC
    DATA
        uart[baudrate=115200] tx p_1 -- RXD, rx p_3 -- TXD
    @ "sensors/gps";
```

**Note:** UART connections require TX-RX and RX-TX crossover (board TX connects to peripheral RX, and vice versa).

### SmartConnect

SmartConnect automatically resolves pin assignments for peripherals, eliminating the need for manual pin-to-pin wiring. The resolver analyzes peripheral pin requirements and board pin availability to allocate power and data connections automatically.

```
SMARTCONNECT EnvSensor @ "sensors/environment";
SMARTCONNECT DistanceSensor @ "sensors/distance";
```

SmartConnect supports all protocols (GPIO, I2C, SPI, UART, PWM) and handles:
- Automatic power pin allocation (VCC + GND)
- Protocol-aware data pin matching (e.g., SDA/SCL for I2C)
- Pin conflict avoidance with manual connections
- GPIO mode inference from peripheral pin metadata

Use `demol generate pinmap` to inspect the resolved pin assignments. See [Semantic Validation](semantic-validation.md) for SmartConnect validation rules.

### Remote Topics

The `@` symbol in connections specifies the MQTT/AMQP/Redis topic for this peripheral:

```
CONNECT MySensor WITH
    POWER ...
    DATA ...
    @ "device/sensor/data";  // optional
```

**Auto-generated Topics:** If `@` is omitted, topics may be auto-generated based on device and peripheral names.

## Message Brokers

DeMoL supports three message broker types:

### MQTT Broker

```
BROKER[MQTT] MyMqttBroker WITH
    host="mqtt.example.com",
    port=1883,
    ssl=False,
    basePath="/mqtt",  // optional
    webPath="/ws",  // optional
    webPort=8080,  // optional
    auth.username="sensor_client",
    auth.password="secure_pass";
```

### AMQP Broker

```
BROKER[AMQP] MyAmqpBroker WITH
    host="rabbitmq.example.com",
    port=5672,
    vhost="/",  // optional
    topicExchange="amq.topic",  // optional
    rpcExchange="amq.rpc",  // optional
    ssl=False,
    auth.username="guest",
    auth.password="guest";
```

### Redis Broker

```
BROKER[Redis] MyRedisBroker WITH
    host="redis.example.com",
    port=6379,
    db=0,  // optional
    ssl=False,
    auth.username="default",
    auth.password="redis_pass";
```

**Authentication Methods:**
- **Username/Password:** `auth.username="user", auth.password="pass"`
- **API Key:** `auth.key="api_key_value"`

## Complete Example

Here's a comprehensive device model demonstrating multiple peripherals, network configuration, and remote communication:

```
DEVICE MultiPeriphDevice WITH
    description="A complex Raspberry Pi 5 system with multiple sensors and actuators",
    author="Antigravity",
    os=raspbian;

USE RaspberryPi_5_8GB;

USE BME680(EnvSensor),
    SRF05(DistanceSensor),
    WS2812(StatusLed),
    TCRT5000(LineTracker),
    TactileButton(UserButton);

NETWORK[WiFi] WITH
    ssid="MyHomeWiFi",
    password="securepassword";

BROKER[MQTT] MyBroker WITH
    host="broker.hivemq.com",
    port=1883,
    auth.username="myuser",
    auth.password="mypassword";

// Environmental Sensor (I2C)
CONNECT EnvSensor WITH
    POWER
        GND_1 -- gnd,
        power_5v_a -- vcc
    DATA
        i2c[slave_address=0x76] sda GPIO2 -- sda, scl GPIO3 -- scl
    @ "sensors/environment";

// Ultrasonic Distance Sensor (GPIO)
CONNECT DistanceSensor WITH
    POWER
        GND_2 -- GND,
        power_5v_a -- VCC
    DATA
        gpio[mode="input"] GPIO24 -- echo,
        gpio[mode="output"] GPIO23 -- trigger
    @ "sensors/distance";

// RGB LED Ring (GPIO)
CONNECT StatusLed WITH
    POWER
        GND_3 -- GND,
        power_5v_b -- VCC
    DATA
        gpio[mode="output"] GPIO18 -- DIN
    @ "actuators/status_led";

// Line Tracker (GPIO)
CONNECT LineTracker WITH
    POWER
        GND_4 -- GND,
        power_5v_b -- VCC
    DATA
        gpio[mode="input"] GPIO4 -- D0
    @ "sensors/line_tracker";

// User Input Button (GPIO)
CONNECT UserButton WITH
    POWER
        GND_5 -- gnd,
        power_5v_a -- state
    DATA
        gpio[mode="input", pullup=true] GPIO17 -- state
    @ "sensors/user_button";
```

## Supported Sensors & Actuators

DeMoL supports **35 sensor types** and **23 actuator types** covering a wide range of IoT applications:

### Sensor Categories

- **Environmental**: Temperature, Humidity, Pressure, Gas, Env, AirQuality, Light, UV, Sound
- **Motion & Position**: Distance, Proximity, Motion, Presence, Acceleration, Gyroscope, Magnetometer, IMU, Tracker
- **Specialized**: ADC, Current, Voltage, Power, Flow, Level, Weight, Force, Vibration
- **Smart**: Camera, RFID, Fingerprint, GPS, Color

### Actuator Categories

- **Basic**: MotorController, ServoController, Relay, Switch
- **Display & Light**: Led, LedArray, NeoPixel, Display, LCD, OLED
- **Sound**: Buzzer, Speaker
- **Advanced**: Stepper, DCMotor, Pump, Valve, Heater, Cooler, Fan

### Message Schemas

Each sensor and actuator type has a defined message schema for standardized communication:

**Example Sensor Message (Environmental):**
```json
{
  "temperature": 23.5,
  "humidity": 65.2,
  "pressure": 1013.25,
  "gas": 450.0,
  "timestamp": 1638360000000
}
```

**Example Actuator Command (NeoPixel):**
```json
{
  "leds": [
    {"index": 0, "r": 255, "g": 0, "b": 0},
    {"index": 1, "r": 0, "g": 255, "b": 0}
  ],
  "brightness": 128,
  "mode": "static",
  "timestamp": 1638360000000
}
```

For complete documentation of all sensor and actuator types with their message schemas, see [Sensors & Actuators Reference](sensors-actuators.md).
