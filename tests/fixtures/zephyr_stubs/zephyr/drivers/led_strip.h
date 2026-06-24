#ifndef ZEPHYR_DRIVERS_LED_STRIP_H_STUB
#define ZEPHYR_DRIVERS_LED_STRIP_H_STUB

#include <zephyr/device.h>

struct led_rgb {
    unsigned char r;
    unsigned char g;
    unsigned char b;
};

int led_strip_update_rgb(const struct device *dev, struct led_rgb *pixels,
                         unsigned int count);

#endif
