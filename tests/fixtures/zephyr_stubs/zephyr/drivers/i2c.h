#ifndef ZEPHYR_DRIVERS_I2C_H_STUB
#define ZEPHYR_DRIVERS_I2C_H_STUB

#include <zephyr/device.h>

struct i2c_dt_spec {
    const struct device *bus;
    unsigned int addr;
    unsigned int flags;
};

#define I2C_DT_SPEC_GET(node_id) ((struct i2c_dt_spec){0})

int i2c_write_dt(const struct i2c_dt_spec *spec, const uint8_t *buf, uint32_t num_bytes);
int i2c_read_dt(const struct i2c_dt_spec *spec, uint8_t *buf, uint32_t num_bytes);

#endif
