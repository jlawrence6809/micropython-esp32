import { useEffect, useState } from 'preact/hooks';
import { Section } from '../components/Section';
import { RelayDialog } from '../components/RelayDialog';
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
  const [updatingRelay, setUpdatingRelay] = useState<string | null>(null);

  const [editingRelay, setEditingRelay] = useState<Relay | null>(null);
  const [dialogMode, setDialogMode] = useState<'create' | 'edit'>('create');
  const [dialogOpen, setDialogOpen] = useState<boolean>(false);

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
    const response = await postRelayConfig(updatedConfigs);

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
        | 'defaultAuto'
        | 'isInverted'
        | 'value'
        | 'auto'
      >
    >,
  ) => {
    if (relayConfigs === 'loading') return;

    // Set this specific relay as updating
    setUpdatingRelay(label);

    const updatedConfigs = relayConfigs.map((config) =>
      config.label === label ? { ...config, ...updates } : config,
    );

    await updateEntireConfig(updatedConfigs);

    // Clear the updating state
    setUpdatingRelay(null);
  };

  const handleDialogSubmit = async (config: Partial<RelayConfig>) => {
    if (relayConfigs === 'loading') return;

    if (dialogMode === 'create') {
      // Create new relay config with runtime state initialized from defaults
      const relayPayload: RelayConfig = {
        pin: config.pin!,
        label: config.label!,
        isInverted: config.isInverted!,
        defaultValue: config.defaultValue!,
        defaultAuto: config.defaultAuto!,
        rule: config.rule!,
        value: config.defaultValue!,
        auto: config.defaultAuto!,
        last_error: null,
      };

      // Add to existing config
      const updatedConfigs = [...relayConfigs, relayPayload];
      await updateEntireConfig(updatedConfigs);
      await refreshGpioOptions();
    } else {
      // Edit mode - update existing relay
      if (!editingRelay) return;
      await updateRelayProperty(editingRelay, config);
    }
  };

  const openCreateDialog = () => {
    setDialogMode('create');
    setEditingRelay(null);
    setDialogOpen(true);
  };

  const openEditDialog = (relay: Relay) => {
    setDialogMode('edit');
    setEditingRelay(relay);
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
    setEditingRelay(null);
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
            const isLoading = updatingRelay === label;

            const isAuto = config.auto;
            const isOn = config.value;
            const hasError = config.last_error != null;

            const stateClasses = `${isAuto ? 'auto' : 'manual'} ${isOn ? 'on' : 'off'} ${isLoading ? 'loading' : ''} ${hasError ? 'error' : ''}`;

            return (
              <div
                key={relay}
                className={`ToggleSwitch ${stateClasses}`}
                onClick={() =>
                  !isLoading &&
                  updateRelayProperty(label, getNextRelayState(config))
                }
                title={hasError ? `Error: ${config.last_error}` : ''}
              >
                <div
                  className={'AutomateButton'}
                  onClick={(ev) => {
                    ev.stopPropagation();
                    openEditDialog(relay);
                  }}
                >
                  ⛭
                </div>
                {isLoading ? (
                  <span style={{ opacity: 0.7 }}>⏳ {label}</span>
                ) : (
                  <>
                    {label}
                    {hasError && (
                      <span style={{ marginLeft: '0.5rem', color: '#ff6b6b' }}>
                        ⚠️
                      </span>
                    )}
                  </>
                )}
              </div>
            );
          })}

          <div style={{ marginTop: '1rem' }}>
            <button
              onClick={openCreateDialog}
              style={{ padding: '0.75rem 1.5rem', fontSize: '1rem' }}
            >
              + Add Relay
            </button>
          </div>

          {dialogOpen && (
            <RelayDialog
              isOpen={true}
              mode={dialogMode}
              gpioOptions={gpioOptions === 'loading' ? [] : gpioOptions}
              initialConfig={
                editingRelay
                  ? relayConfigs.find((c) => c.label === editingRelay)
                  : undefined
              }
              lastError={
                editingRelay
                  ? relayConfigs.find((c) => c.label === editingRelay)
                      ?.last_error || null
                  : null
              }
              onSubmit={handleDialogSubmit}
              onClose={closeDialog}
            />
          )}
        </>
      )}
    </Section>
  );
};
