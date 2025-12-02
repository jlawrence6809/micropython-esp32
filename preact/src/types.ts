/**
 * Helper to create nominal (opaque) types in TypeScript.
 * Usage:
 *   type MyNominal = Nominal<string, 'MyNominal'>;
 */
export type Nominal<T, Name extends string> = T & { readonly __nominal: Name };

/**
 * A relay is identified by its label string.
 */
export type Relay = Nominal<string, 'Relay'>;

/**
 * Relay configuration as returned by the new /relay-config endpoint
 *
 * value: the actual current state of the relay (true = on, false = off)
 * auto: whether in auto mode (true) or manual/forced mode (false)
 * defaultValue: the default value (on/off) to use on boot
 * defaultAuto: the default mode (auto/manual) to use on boot
 */
export type RelayConfig = {
  pin: number;
  isInverted: boolean;
  label: string;
  value: boolean; // Current state (on/off) - determines button color
  auto: boolean; // true = auto mode (rule-driven), false = manual (forced)
  defaultValue: boolean; // default state on boot
  defaultAuto: boolean; // default mode on boot (true = auto, false = manual)
  rule: string;
  last_error?: string | null; // Runtime error from last rule evaluation
};

/**
 * Full relay configuration response
 */
export type RelayConfigDto = {
  count: number;
  relays: RelayConfig[];
};

/**
 * Sensor pin configuration
 */
export type SensorPins = {
  i2c_scl: number;
  i2c_sda: number;
  ds18b20: number;
  photo_sensor: number;
  light_switch: number;
  reset_switch: number;
};

/**
 * Sensor configuration response from /api/sensor-config
 */
export type SensorConfigResponse = {
  sensor_pins: SensorPins;
  available_pins: number[];
  adc1_pins: number[];
};

/**
 * Sensor data response from /api/sensors
 */
export type SensorData = {
  temperature: number | null;
  humidity: number | null;
  light_level: number | null;
  switch_state: boolean;
  reset_switch_state: boolean;
  time_seconds: number;
};
