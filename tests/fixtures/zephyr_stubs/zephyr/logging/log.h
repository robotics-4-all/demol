/* Minimal stub for the Zephyr logging API.
 *
 * Used by the constraint runtime (constraint.c) for `LOG_WRN` calls and
 * by the MQTT skeleton header declarations. Only the symbols referenced
 * by generated T16 + constraint code are stubbed.
 */
#ifndef DEMOL_STUB_ZEPHYR_LOGGING_LOG_H
#define DEMOL_STUB_ZEPHYR_LOGGING_LOG_H

#define LOG_WRN(...) ((void)0)
#define LOG_ERR(...) ((void)0)
#define LOG_INF(...) ((void)0)
#define LOG_DBG(...) ((void)0)

#endif /* DEMOL_STUB_ZEPHYR_LOGGING_LOG_H */
