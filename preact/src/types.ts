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
};

/**
 * Full relay configuration response
 */
export type RelayConfigDto = {
  count: number;
  relays: RelayConfig[];
};
