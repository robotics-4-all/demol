#ifndef ZEPHYR_DRIVERS_PWM_H_STUB
#define ZEPHYR_DRIVERS_PWM_H_STUB

#include <zephyr/device.h>

struct pwm_dt_spec {
    const struct device *dev;
    unsigned int channel;
    unsigned int period;
    int flags;
};

#define PWM_DT_SPEC_GET(node_id) ((struct pwm_dt_spec){0})

int pwm_is_ready_dt(const struct pwm_dt_spec *spec);
int pwm_set_usec_dt(const struct pwm_dt_spec *spec, uint32_t period, uint32_t pulse);

#endif
