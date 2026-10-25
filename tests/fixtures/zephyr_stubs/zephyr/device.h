#ifndef ZEPHYR_DEVICE_H_STUB
#define ZEPHYR_DEVICE_H_STUB

struct device;

#define DEVICE_DT_GET(node_id) ((struct device *)0)
#define DT_INST(n, compat) (n)
#define DT_ALIAS(alias)     alias

int device_is_ready(const struct device *dev);

#endif
