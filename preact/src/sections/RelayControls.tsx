import { useEffect, useState } from 'preact/hooks';
import { Section } from '../components/Section';
import { AutomateDialog } from '../components/AutomateDialog';
import { Relay, RelayStateValue, RelayForceState, RelayConfig } from '../types';
import { fetchGpioOptions, fetchRelayConfig, postRelayConfig } from '../api';

/**
 * Internal relay count tracking for this component.
 */
let RELAY_COUNT = 0;

const parseRelayStateValue = (value: number): RelayStateValue => {
  const force = value % 10;
  const auto = Math.floor(value / 10);
  return { force, auto } as RelayStateValue;
};

const getRelayStateValue = (current: RelayStateValue): number =>
  current.auto * 10 + current.force;

/**
 * This is the order:
 * force off -> force on -> force x -> force off -> etc...
 * So do not modify the tens digit, just the ones digit (force digit).
 */
const getNextRelayStateValue = (current: number): number => {
  const { force, auto } = parseRelayStateValue(current);
  const nextForce = ((force + 1) % 3) as RelayForceState;
  return getRelayStateValue({ force: nextForce, auto });
};

export const RelayControls = () => {
  const [relayConfigs, setRelayConfigs] = useState<RelayConfig[] | 'loading'>(
    'loading',
  );

  const [gpioOptions, setGpioOptions] = useState<number[] | 'loading'>(
    'loading',
  );
  const [updating, setUpdating] = useState<boolean>(false);
  const [adding, setAdding] = useState<boolean>(false);
  const [newRelay, setNewRelay] = useState<Partial<RelayConfig>>({});

  const [automateDialogRelay, setAutomateDialogRelay] = useState<Relay | null>(
    null,
  );

  useEffect(() => {
    fetchRelayConfig().then((json) => {
      RELAY_COUNT = json.count;
      setRelayConfigs(json.relays);
    });
  }, []);

  const refreshGpioOptions = async () => {
    setGpioOptions('loading');
    const options = await fetchGpioOptions();
    setGpioOptions(options);
  };
  useEffect(() => {
    refreshGpioOptions();
  }, []);

  // Function to update the entire relay configuration
  const updateEntireConfig = async (updatedConfigs: RelayConfig[]) => {
    setUpdating(true);
    const response = await postRelayConfig(updatedConfigs);
    setUpdating(false);

    if (!response.ok) {
      alert(`Failed to update relay config: ${response.statusText}`);
    }

    // Refresh the config after update
    await fetchRelayConfig();
  };

  // Helper function to update a single relay property
  const updateRelayProperty = async (
    label: string,
    updates: Partial<
      Pick<
        RelayConfig,
        | 'pin'
        | 'label'
        | 'rule'
        | 'defaultValue'
        | 'isInverted'
        | 'currentValue'
      >
    >,
  ) => {
    if (relayConfigs === 'loading') return;

    const updatedConfigs = relayConfigs.map((config) =>
      config.label === label ? { ...config, ...updates } : config,
    );

    await updateEntireConfig(updatedConfigs);

    await fetchRelayConfig();
  };

  const addRelay = async () => {
    if (newRelay.pin === undefined || relayConfigs === 'loading') return;
    setAdding(true);
    try {
      // Generate default label if none provided
      const label =
        newRelay.label?.trim() || `Relay ${relayConfigs.length + 1}`;

      // Create new relay config
      const relayPayload: RelayConfig = {
        pin: -1,
        isInverted: false,
        label,
        currentValue: 0, // Will be set to defaultValue by backend
        defaultValue: 0,
        rule: '["NOP"]',
        ...newRelay,
      };

      // Add to existing config
      const updatedConfigs = [...relayConfigs, relayPayload];
      await updateEntireConfig(updatedConfigs);

      await refreshGpioOptions();
      setNewRelay({});
    } finally {
      setAdding(false);
    }
  };

  return (
    <Section
      className={`RelayForm ${relayConfigs === 'loading' ? 'loading' : ''}`}
      title="Relay Controls"
    >
      {relayConfigs === 'loading' && <div>Loading...</div>}
      {relayConfigs !== 'loading' && (
        <>
          {relayConfigs.length === 0 && (
            <div style={{ padding: '0.5rem 0' }}>No relays configured.</div>
          )}
          {relayConfigs.map((config) => {
            const relay: Relay = config.label as Relay;
            const value = config.currentValue;
            const state = parseRelayStateValue(value);
            const label = config.label;
            const isLoading = updating || adding;

            let stateClasses = 'loading';

            stateClasses = `auto_${state.auto} force_${state.force}`;

            return (
              <div
                key={relay}
                className={`ToggleSwitch ${stateClasses}`}
                onClick={() =>
                  !isLoading &&
                  updateRelayProperty(label, {
                    currentValue: getNextRelayStateValue(value),
                  })
                }
              >
                <div
                  className={'AutomateButton'}
                  onClick={(ev) => {
                    ev.stopPropagation();
                    setAutomateDialogRelay(relay);
                  }}
                >
                  ⛭
                </div>
                {label}
              </div>
            );
          })}

          <div style={{ marginTop: '1rem' }}>
            <h4>Add Relay</h4>
            <div
              style={{
                display: 'flex',
                gap: '0.5rem',
                alignItems: 'center',
                flexWrap: 'wrap',
              }}
            >
              <select
                value={newRelay.pin == null ? '' : newRelay.pin}
                onChange={(e) =>
                  setNewRelay({
                    ...newRelay,
                    pin:
                      e.currentTarget.value === ''
                        ? null
                        : parseInt(e.currentTarget.value, 10),
                  })
                }
              >
                <option value="">Select GPIO</option>
                {gpioOptions !== 'loading' &&
                  gpioOptions.map((p) => (
                    <option key={p} value={p}>
                      GPIO {p}
                    </option>
                  ))}
              </select>
              <input
                type="text"
                placeholder="Label (optional)"
                value={newRelay.label}
                onChange={(e) =>
                  setNewRelay({ ...newRelay, label: e.currentTarget.value })
                }
                style={{ minWidth: '120px' }}
              />
              <label
                style={{
                  display: 'flex',
                  gap: '0.25rem',
                  alignItems: 'center',
                }}
              >
                <input
                  type="checkbox"
                  checked={newRelay.isInverted}
                  onChange={(e) =>
                    setNewRelay({
                      ...newRelay,
                      isInverted: e.currentTarget.checked,
                    })
                  }
                />
                Inverted
              </label>
              <button
                disabled={adding || newRelay.pin == null}
                onClick={addRelay}
              >
                {adding ? 'Adding...' : 'Add Relay'}
              </button>
            </div>
          </div>

          {automateDialogRelay && (
            <AutomateDialog
              isOpen={true}
              label={
                relayConfigs.find(
                  (config) => config.label === automateDialogRelay,
                )?.label || ''
              }
              initialRule={
                relayConfigs.find(
                  (config) => config.label === automateDialogRelay,
                )?.rule || '["NOP"]'
              }
              onLabelChange={async (newLabel: string) =>
                updateRelayProperty(automateDialogRelay, {
                  label: newLabel,
                })
              }
              onRuleSubmit={async (rule: string) => {
                updateRelayProperty(automateDialogRelay, { rule });
              }}
              onClose={() => setAutomateDialogRelay(null)}
            />
          )}
        </>
      )}
    </Section>
  );
};
