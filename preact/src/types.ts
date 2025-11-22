/**
 * Helper to create nominal (opaque) types in TypeScript.
 * Usage:
 *   type MyNominal = Nominal<string, 'MyNominal'>;
 */
export type Nominal<T, Name extends string> = T & { readonly __nominal: Name };

/*
 * Ones digit: force digit (0 = off, 1 = on, 2 = x/dont care)
 * 0 = off, 1 = on, 2 = x/dont care
 */
export type RelayForceState = 0 | 1 | 2;
/**
 * Tens digit: auto digit (0 = off, 1 = on)
 * 0 = off, 1 = on
 */
export type RelayAutoState = 0 | 1;

/**
 * Relay state value for use in the UI.
 */
export type RelayStateValue = {
  force: RelayForceState;
  auto: RelayAutoState;
};

/**
 * A relay is identified by its label string.
 */
export type Relay = Nominal<string, 'Relay'>;

/**
 * Relay configuration as returned by the new /relay-config endpoint
 */
export type RelayConfig = {
  pin: number;
  isInverted: boolean;
  label: string;
  currentValue: number;
  defaultValue: number;
  rule: string;
};

/**
 * Full relay configuration response
 */
export type RelayConfigDto = {
  count: number;
  relays: RelayConfig[];
};
