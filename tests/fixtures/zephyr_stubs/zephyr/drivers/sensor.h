#ifndef ZEPHYR_DRIVERS_SENSOR_H_STUB
#define ZEPHYR_DRIVERS_SENSOR_H_STUB

struct sensor_value {
    int val1;
    int val2;
};

#define SENSOR_CHAN_AMBIENT_TEMP 1
#define SENSOR_CHAN_PRESS        2
#define SENSOR_CHAN_HUMIDITY     3
#define SENSOR_CHAN_LIGHT       4

int sensor_sample_fetch(const struct device *dev);
int sensor_channel_get(const struct device *dev, int chan, struct sensor_value *val);
double sensor_value_to_double(const struct sensor_value *val);

#endif
