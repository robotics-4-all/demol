from demol.transformations.json_demol import demol_to_json, json_to_demol
from demol.lang.device import get_device_mm


def _build_model(demol_str: str):
    mm = get_device_mm()
    mm.skip_semantics = True
    return mm.model_from_str(demol_str)


def test_json_to_demol_basic():
    """Test basic device model generation."""
    json_data = {
        "device": {"name": "TestDevice", "description": "A test device", "author": "Tester", "os": "raspbian"},
        "board": {"name": "RaspberryPi_5_8GB"},
        "network": {"type": "WiFi", "ssid": "test_ssid", "password": "test_pass"},
        "broker": {"type": "MQTT", "name": "MyBroker", "host": "localhost", "port": 1883},
        "peripherals": [{"name": "LedGeneric", "instanceName": "Led1"}],
        "connections": [
            {
                "fromName": "Led1",
                "toName": "RaspberryPi_5_8GB",
                "type": "gpio",
                "props": {"mode": "output"},
                "mappings": [{"fromPin": "vin", "toPin": "GPIO18"}],
            },
            {
                "fromName": "Led1",
                "toName": "RaspberryPi_5_8GB",
                "type": "power",
                "mappings": [{"fromPin": "gnd", "toPin": "GND_1"}, {"fromPin": "vcc", "toPin": "power_3v3_a"}],
            },
        ],
    }

    demol_str = json_to_demol(json_data)

    # Verify the generated string contains key elements
    assert "DEVICE TestDevice WITH" in demol_str
    assert 'description="A test device"' in demol_str
    assert 'author="Tester"' in demol_str
    assert "os=raspbian" in demol_str
    assert "USE RaspberryPi_5_8GB;" in demol_str
    assert 'NETWORK [WiFi] WITH ssid="test_ssid", password="test_pass";' in demol_str
    assert 'BROKER [MQTT] MyBroker WITH host="localhost", port=1883;' in demol_str

    # Verify it parses back
    mm = get_device_mm()
    model = mm.model_from_str(demol_str)
    assert model.metadata.name == "TestDevice"


def test_json_to_demol_peripherals():
    """Test peripheral generation."""
    json_data = {
        "device": {"name": "PTest", "os": "raspbian"},
        "board": {"name": "RaspberryPi_5_8GB"},
        "network": {"type": "WiFi", "ssid": "s", "password": "p"},
        "broker": {"type": "MQTT", "name": "B", "host": "h", "port": 1883},
        "peripherals": [
            {"name": "BME680", "instanceName": "EnvSensor", "attributes": {"address": {"default": "0x76"}}},
            {"name": "LedGeneric", "instanceName": "StatusLed"},
        ],
    }

    demol_str = json_to_demol(json_data)

    assert (
        'USE BME680 [EnvSensor] WITH address="0x76", LedGeneric [StatusLed];' in demol_str
        or 'USE BME680 [EnvSensor] WITH address="0x76"' in demol_str
        and "LedGeneric [StatusLed]" in demol_str
    )


def test_json_to_demol_connections_horizontal_logic():
    """Test connection generation with horizontal pin logic."""
    json_data = {
        "device": {"name": "ConnectTest", "os": "raspbian"},
        "board": {"name": "RaspberryPi_5_8GB"},
        "network": {"type": "WiFi", "ssid": "s", "password": "p"},
        "broker": {"type": "MQTT", "name": "B", "host": "h", "port": 1883},
        "peripherals": [{"name": "BME680", "instanceName": "MyBME"}],
        "connections": [
            {
                "fromName": "MyBME",
                "toName": "RaspberryPi_5_8GB",
                "type": "power",
                "mappings": [
                    {"fromPin": "gnd", "toPin": "GND_1", "section": "power"},
                    {"fromPin": "vcc", "toPin": "power_3v3_a", "section": "power"},
                ],
            },
            {
                "fromName": "MyBME",
                "toName": "RaspberryPi_5_8GB",
                "type": "i2c",
                "props": {"slave_address": "0x76"},
                "mappings": [
                    {"function": "sda", "fromPin": "sda", "toPin": "GPIO2", "section": "data"},
                    {"function": "scl", "fromPin": "scl", "toPin": "GPIO3", "section": "data"},
                ],
            },
        ],
    }

    demol_str = json_to_demol(json_data)

    # Check POWER connection
    # Should be: gnd -- GND_1, vcc -- power_3v3_a
    assert "POWER gnd -- GND_1, vcc -- power_3v3_a" in demol_str

    # Check DATA connection
    # Should be: i2c[slave_address="0x76"] sda sda -- GPIO2, scl scl -- GPIO3
    # Note: json_demol might output props differently, let's check flexibility
    assert 'i2c [slave_address="0x76"]' in demol_str
    assert "sda sda -- GPIO2" in demol_str
    assert "scl scl -- GPIO3" in demol_str


def test_json_to_demol_gpio_connection():
    """Test GPIO connection generation."""
    json_data = {
        "device": {"name": "GPIOTest", "os": "raspbian"},
        "board": {"name": "RaspberryPi_5_8GB"},
        "network": {"type": "WiFi", "ssid": "s", "password": "p"},
        "broker": {"type": "MQTT", "name": "B", "host": "h", "port": 1883},
        "peripherals": [{"name": "LedGeneric", "instanceName": "MyLed"}],
        "connections": [
            {
                "fromName": "MyLed",
                "toName": "RaspberryPi_5_8GB",
                "type": "gpio",
                "props": {"mode": "output"},
                "mappings": [{"fromPin": "vin", "toPin": "GPIO18", "section": "data"}],
            }
        ],
    }

    demol_str = json_to_demol(json_data)

    assert 'gpio [mode="output"] vin -- GPIO18' in demol_str


def test_json_to_demol_uart_connection():
    """Test UART connection generation."""
    json_data = {
        "device": {"name": "UARTTest", "os": "raspbian"},
        "board": {"name": "RaspberryPi_5_8GB"},
        "network": {"type": "WiFi", "ssid": "s", "password": "p"},
        "broker": {"type": "MQTT", "name": "B", "host": "h", "port": 1883},
        "peripherals": [{"name": "TFMini", "instanceName": "Lidar"}],
        "connections": [
            {
                "fromName": "Lidar",
                "toName": "RaspberryPi_5_8GB",
                "type": "uart",
                "props": {"baudrate": 115200},
                "mappings": [
                    {"function": "tx", "fromPin": "RXD", "toPin": "GPIO14", "section": "data"},
                    {"function": "rx", "fromPin": "TXD", "toPin": "GPIO15", "section": "data"},
                ],
            }
        ],
    }

    demol_str = json_to_demol(json_data)

    assert "uart [baudrate=115200]" in demol_str
    assert "tx RXD -- GPIO14" in demol_str
    assert "rx TXD -- GPIO15" in demol_str


def test_demol_to_json_roundtrip():
    """JSON serialization then deserialization should produce an equivalent model."""
    model_str = """
    DEVICE RoundtripDev WITH description="rt", author="tester", os=raspbian;
    USE RaspberryPi_5_8GB;
    USE BME680 [EnvSensor];
    NETWORK [WiFi] WITH ssid="s", password="p";
    BROKER [MQTT] MyBroker WITH host="localhost", port=1883;
    CONNECT EnvSensor WITH
        POWER gnd -- GND_1, vcc -- power_5v_a
        DATA i2c [slave_address=0x77] sda sda -- GPIO2, scl scl -- GPIO3
        @ "dev.sensor.env";
    """
    model_a = _build_model(model_str)
    j = demol_to_json(model_a)
    demol_str = json_to_demol(j)
    model_b = _build_model(demol_str)
    assert model_b.metadata.name == "RoundtripDev"
    assert len(model_b.components.peripherals) == 1
    assert len(model_b.connections) == 1
