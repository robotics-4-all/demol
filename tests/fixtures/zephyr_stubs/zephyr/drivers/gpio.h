#ifndef ZEPHYR_DRIVERS_GPIO_H_STUB
#define ZEPHYR_DRIVERS_GPIO_H_STUB

#include <zephyr/device.h>

struct gpio_dt_spec {
    const struct device *port;
    unsigned int pin;
    unsigned int flags;
};

#define GPIO_DT_SPEC_GET(node_id, prop) ((struct gpio_dt_spec){0})

#define GPIO_INPUT              0x01
#define GPIO_OUTPUT             0x02
#define GPIO_OUTPUT_INIT_LOW    0x04
#define GPIO_OUTPUT_INIT_HIGH   0x08
#define GPIO_INT_EDGE_TO_ACTIVE 0x10
#define GPIO_INT_DEBOUNCE       0x20

int gpio_is_ready_dt(const struct gpio_dt_spec *spec);
int gpio_pin_configure_dt(const struct gpio_dt_spec *spec, int flags);
int gpio_pin_set_dt(const struct gpio_dt_spec *spec, int value);
int gpio_pin_interrupt_configure_dt(const struct gpio_dt_spec *spec, int flags);
int gpio_add_callback(const struct device *port, void *cb);

struct gpio_callback;
void gpio_init_callback(void *cb, void *handler, int mask);

#endif
