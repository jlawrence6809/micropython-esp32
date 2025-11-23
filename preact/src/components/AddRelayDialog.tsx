import { useState, useEffect } from 'preact/hooks';
import { FullScreenDialog } from './Dialog';
import { RelayConfig } from '../types';

type AddRelayDialogProps = {
  isOpen: boolean;
  gpioOptions: number[];
  onSubmit: (relay: Omit<RelayConfig, 'value' | 'auto'>) => Promise<void>;
  onClose: () => void;
};

export const AddRelayDialog = ({
  isOpen,
  gpioOptions,
  onSubmit,
  onClose,
}: AddRelayDialogProps) => {
  const [pin, setPin] = useState<number | null>(null);
  const [label, setLabel] = useState<string>('');
  const [isInverted, setIsInverted] = useState<boolean>(false);
  const [defaultValue, setDefaultValue] = useState<boolean>(false);
  const [defaultAuto, setDefaultAuto] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);

  // Reset form when dialog opens
  useEffect(() => {
    if (isOpen) {
      setPin(null);
      setLabel('');
      setIsInverted(false);
      setDefaultValue(false);
      setDefaultAuto(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    if (pin === null) {
      alert('Please select a GPIO pin');
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit({
        pin,
        label: label.trim() || `Relay ${pin}`,
        isInverted,
        defaultValue,
        defaultAuto,
        rule: '["NOP"]',
      });
      onClose();
    } catch (error) {
      console.error('Error adding relay:', error);
      alert('Failed to add relay');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <FullScreenDialog onClose={onClose}>
      <div className="AutomateDialog">
        <h3>Add New Relay</h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <strong>GPIO Pin *</strong>
            <select
              value={pin === null ? '' : pin}
              onChange={(e) =>
                setPin(
                  e.currentTarget.value === ''
                    ? null
                    : parseInt(e.currentTarget.value, 10),
                )
              }
              style={{ padding: '0.5rem', fontSize: '1rem' }}
            >
              <option value="">Select GPIO</option>
              {gpioOptions.map((p) => (
                <option key={p} value={p}>
                  GPIO {p}
                </option>
              ))}
            </select>
          </label>

          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <strong>Label (optional)</strong>
            <input
              type="text"
              placeholder={`Relay ${pin || '...'}`}
              value={label}
              onChange={(e) => setLabel(e.currentTarget.value)}
              style={{ padding: '0.5rem', fontSize: '1rem' }}
            />
          </label>

          <label
            style={{
              display: 'flex',
              gap: '0.5rem',
              alignItems: 'center',
              cursor: 'pointer',
            }}
          >
            <input
              type="checkbox"
              checked={isInverted}
              onChange={(e) => setIsInverted(e.currentTarget.checked)}
            />
            <strong>Inverted Logic</strong>
            <span style={{ fontSize: '0.9rem', opacity: 0.7 }}>
              (High = Off, Low = On)
            </span>
          </label>

          <hr style={{ width: '100%', margin: '0.5rem 0' }} />

          <div>
            <strong>Default State on Boot:</strong>
            <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label
                style={{
                  display: 'flex',
                  gap: '0.5rem',
                  alignItems: 'center',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={defaultValue}
                  onChange={(e) => setDefaultValue(e.currentTarget.checked)}
                />
                Default Value: <strong>{defaultValue ? 'ON' : 'OFF'}</strong>
              </label>

              <label
                style={{
                  display: 'flex',
                  gap: '0.5rem',
                  alignItems: 'center',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={defaultAuto}
                  onChange={(e) => setDefaultAuto(e.currentTarget.checked)}
                />
                Default Mode: <strong>{defaultAuto ? 'AUTO' : 'MANUAL'}</strong>
              </label>
            </div>
          </div>
        </div>

        <div className="Buttons" style={{ marginTop: '1.5rem' }}>
          <button onClick={onClose} disabled={submitting}>
            Cancel
          </button>
          <button onClick={handleSubmit} disabled={submitting || pin === null}>
            {submitting ? 'Adding...' : 'Add Relay'}
          </button>
        </div>
      </div>
    </FullScreenDialog>
  );
};

