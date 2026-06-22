from textx.exceptions import TextXSemanticError
import pytest

# ============================================================================
# I2C Connection Tests (validate_i2c_connection)
# ============================================================================


def test_i2c_valid(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680[MySensor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MySensor WITH
        POWER vcc -- power_5v_a, gnd -- GND_1
        DATA
            i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3;
    """
    with pytest.warns(UserWarning):
        device_mm.model_from_str(model_str)


def test_i2c_invalid_address_range(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680[MySensor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MySensor WITH
        POWER vcc -- power_5v_a, gnd -- GND_1
        DATA
            i2c[slave_address=0x80] sda sda -- GPIO2, scl scl -- GPIO3;
    """
    with pytest.raises(TextXSemanticError, match="out of valid range"):
        device_mm.model_from_str(model_str)


def test_i2c_missing_function(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680[MySensor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MySensor WITH
        POWER vcc -- power_5v_a, gnd -- GND_1
        DATA
            // GPIO4 is not SDA
            i2c[slave_address=0x76] sda sda -- GPIO4, scl scl -- GPIO3;
    """
    with pytest.raises(TextXSemanticError, match="does not have SDA"):
        device_mm.model_from_str(model_str)


def test_i2c_invalid_bus_speed(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680[MySensor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MySensor WITH
        POWER vcc -- power_5v_a, gnd -- GND_1
        DATA
            i2c[slave_address=0x76, bus_speed=0] sda sda -- GPIO2, scl scl -- GPIO3;
    """
    with pytest.raises(TextXSemanticError, match="must be a positive integer"):
        device_mm.model_from_str(model_str)


def test_i2c_deprecated_name(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680[MySensor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MySensor WITH
        POWER vcc -- power_5v_a, gnd -- GND_1
        DATA
            i2c[name="dep", slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3;
    """
    with pytest.raises(TextXSemanticError, match="Property 'name' is deprecated"):
        device_mm.model_from_str(model_str)


# ============================================================================
# SPI Connection Tests (validate_spi_connection)
# ============================================================================

# Assuming we have an SPI peripheral (e.g. RFID RC522, but not in builtins? Let's check builtins)
# Builtins: srf04, srf05, hcsr04 (GPIO), ws2812 (GPIO), adafruit_adc_diff (I2C?), bme680 (I2C),
# mpl3115a2 (I2C), pca9685 (I2C), tcrt5000 (GPIO), tfmini (UART/I2C), vl53l1x (I2C), ws281x (GPIO)
# Need to check if any builtin uses SPI.
# If not, we might need to mock one or use a generic one if available.
# Let's assume we can define one inline or use a mock.
# Actually, we can define a mock peripheral in the test string if we could...
# but USE requires a file.
# We can use a dummy peripheral definition if we had one.
# Or we can just try to connect a known I2C peripheral as SPI and see if it fails on pin check first?
# No, it checks peripheral pins too.
# Let's skip SPI tests if no SPI peripheral is available, or create a temporary .hwd file.


@pytest.fixture
def spi_peripheral_file(tmp_path):
    p = tmp_path / "spi_test.hwd"
    p.write_text("""
    SENSOR[Test] SPISensor WITH
        OP vcc=3V3
        PINS
            vcc[3V3] @ 1, gnd[GND] @ 2,
            mosi[mosi] @ 3, miso[miso] @ 4, sck[sck] @ 5, cs[cs] @ 6
    ;
    """)
    return str(p)


# NOTE: The current test setup loads builtins from the repo path.
# Loading a temp file might be tricky with `USE` if it's not in the repo path.
# However, `get_device_mm` registers a global repo for `*.hwd` in `demol/builtin_models/peripherals`.
# We might not be able to easily inject a new peripheral without putting it there.
# Alternative: Use `tfmini` if it supports SPI? (It's usually UART/I2C).
# Let's check `demol/builtin_models/peripherals` content again.
# Only `adafruit_adc_diff` might be SPI? (ADS1x15 is I2C, MCP3008 is SPI).
# Let's check `adafruit_adc_diff.hwd`.
