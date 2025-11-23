import { useEffect, useState } from 'preact/hooks';
import { Section } from '../components/Section';
import { AutomateDialog } from '../components/AutomateDialog';
import { Relay, RelayConfig } from '../types';
import { fetchGpioOptions, fetchRelayConfig, postRelayConfig } from '../api';

/**
 * Internal relay count tracking for this component.
 */
let RELAY_COUNT = 0;

/**
 * Cycle through relay states:
 * Manual Off (value=false, auto=false) ->
 * Manual On (value=true, auto=false) ->
 * Auto (value=<rule result>, auto=true) ->
 * Manual Off ...
 */
const getNextRelayState = (
  current: Pick<RelayConfig, 'value' | 'auto'>,
): Pick<RelayConfig, 'value' | 'auto'> => {
  if (!current.auto && !current.value) {
    // Manual Off -> Manual On
    return { value: true, auto: false };
  } else if (!current.auto && current.value) {
    // Manual On -> Auto
    return { value: current.value, auto: true }; // Keep current value when switching to auto
  } else {
    // Auto -> Manual Off
    return { value: false, auto: false };
  }
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
      return;
    }

    // Refresh the config after update
    const json = await fetchRelayConfig();
    setRelayConfigs(json.relays);
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
        | 'value'
        | 'auto'
      >
    >,
  ) => {
    if (relayConfigs === 'loading') return;

    const updatedConfigs = relayConfigs.map((config) =>
      config.label === label ? { ...config, ...updates } : config,
    );

    await updateEntireConfig(updatedConfigs);
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
        value: false, // Start off
        auto: false, // Start in manual mode
        defaultValue: false,
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
            const label = config.label;
            const isLoading = updating || adding;

            const isAuto = config.auto;
            const isOn = config.value;

            const stateClasses = `${isAuto ? 'auto' : 'manual'} ${isOn ? 'on' : 'off'}`;

            return (
              <div
                key={relay}
                className={`ToggleSwitch ${stateClasses}`}
                onClick={() =>
                  !isLoading &&
                  updateRelayProperty(label, getNextRelayState(config))
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
