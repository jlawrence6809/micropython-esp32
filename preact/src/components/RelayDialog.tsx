import { useState, useEffect } from 'preact/hooks';
import { validateRule, ValidationResponse } from '../api';
import { FullScreenDialog } from './Dialog';
import { RelayConfig } from '../types';
import { RuleDocumentation } from './RuleDocumentation';

type RelayDialogProps = {
  isOpen: boolean;
  mode: 'create' | 'edit';
  gpioOptions: number[];
  initialConfig?: Partial<RelayConfig>;
  lastError?: string | null;
  onSubmit: (config: Partial<RelayConfig>) => Promise<void>;
  onClose: () => void;
};

export const RelayDialog = ({
  isOpen,
  mode,
  gpioOptions,
  initialConfig,
  lastError,
  onSubmit,
  onClose,
}: RelayDialogProps) => {
  const [pin, setPin] = useState<number | null>(initialConfig?.pin ?? null);
  const [label, setLabel] = useState<string>(initialConfig?.label ?? '');
  const [isInverted, setIsInverted] = useState<boolean>(
    initialConfig?.isInverted ?? false,
  );
  const [defaultValue, setDefaultValue] = useState<boolean>(
    initialConfig?.defaultValue ?? false,
  );
  const [defaultAuto, setDefaultAuto] = useState<boolean>(
    initialConfig?.defaultAuto ?? false,
  );
  const [rule, setRule] = useState<string>(initialConfig?.rule ?? '');
  const [validationResult, setValidationResult] =
    useState<ValidationResponse | null>(null);
  const [validating, setValidating] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);

  // Reset form when dialog opens
  useEffect(() => {
    if (isOpen) {
      setPin(initialConfig?.pin ?? null);
      setLabel(initialConfig?.label ?? '');
      setIsInverted(initialConfig?.isInverted ?? false);
      setDefaultValue(initialConfig?.defaultValue ?? false);
      setDefaultAuto(initialConfig?.defaultAuto ?? false);
      setRule(initialConfig?.rule ?? '');
      setValidationResult(null);
    }
  }, [isOpen, initialConfig]);

  if (!isOpen) return null;

  const handleValidation = async () => {
    if (!rule.trim()) {
      setValidationResult(null);
      return;
    }

    setValidating(true);
    try {
      const result = await validateRule(rule);
      setValidationResult(result);
    } catch (error) {
      console.error('Validation error:', error);
      setValidationResult({
        success: false,
        error: `Network error: ${error.message}`,
      });
    } finally {
      setValidating(false);
    }
  };

  const handleSubmit = async () => {
    if (mode === 'create' && pin === null) {
      alert('Please select a GPIO pin');
      return;
    }

    if (!validationResult || !validationResult.success) {
      alert('Please validate the rule before submitting');
      return;
    }

    setSubmitting(true);
    try {
      const config: Partial<RelayConfig> = {
        pin: pin!,
        label: label.trim() || `Relay ${pin}`,
        isInverted,
        defaultValue,
        defaultAuto,
        rule,
      };

      await onSubmit(config);
      onClose();
    } catch (error) {
      console.error(
        `Error ${mode === 'create' ? 'adding' : 'updating'} relay:`,
        error,
      );
      alert(`Failed to ${mode === 'create' ? 'add' : 'update'} relay`);
    } finally {
      setSubmitting(false);
    }
  };

  const submitDisabled =
    submitting ||
    (mode === 'create' && pin === null) ||
    !validationResult ||
    !validationResult.success;

  return (
    <FullScreenDialog onClose={onClose}>
      <div className="AutomateDialog">
        <h3>{mode === 'create' ? 'Add New Relay' : 'Edit Relay'}</h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* GPIO Pin */}
          <label
            style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}
          >
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
              disabled={mode === 'edit'}
              style={{
                padding: '0.5rem',
                fontSize: '1rem',
                opacity: mode === 'edit' ? 0.6 : 1,
              }}
            >
              <option value="">Select GPIO</option>
              {gpioOptions.map((p) => (
                <option key={p} value={p}>
                  GPIO {p}
                </option>
              ))}
              {mode === 'edit' &&
                pin !== null &&
                !gpioOptions.includes(pin) && (
                  <option value={pin}>GPIO {pin}</option>
                )}
            </select>
            {mode === 'edit' && (
              <span style={{ fontSize: '0.85rem', opacity: 0.7 }}>
                PIN cannot be changed after creation
              </span>
            )}
          </label>

          {/* Label */}
          <label
            style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}
          >
            <strong>Label</strong>
            <input
              type="text"
              placeholder={`Relay ${pin || '...'}`}
              value={label}
              onChange={(e) => setLabel(e.currentTarget.value)}
              style={{ padding: '0.5rem', fontSize: '1rem' }}
            />
          </label>

          {/* Inverted Logic */}
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

          {/* Default State on Boot */}
          <div>
            <strong>Default State on Boot:</strong>
            <div
              style={{
                marginTop: '0.5rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem',
              }}
            >
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

          <hr style={{ width: '100%', margin: '0.5rem 0' }} />

          {/* Rule */}
          <div>
            <strong>Automation Rule</strong>
            <textarea
              value={rule}
              onChange={(ev) => setRule(ev.currentTarget.value)}
              onKeyDown={(ev) => {
                // Allow Tab key to insert spaces instead of changing focus
                if (ev.key === 'Tab') {
                  ev.preventDefault();
                  const target = ev.currentTarget;
                  const start = target.selectionStart;
                  const end = target.selectionEnd;
                  const spaces = '  '; // 2 spaces (or use '\t' for tab character)

                  // Insert spaces at cursor position
                  const newValue =
                    rule.substring(0, start) + spaces + rule.substring(end);
                  setRule(newValue);

                  // Move cursor after inserted spaces
                  setTimeout(() => {
                    target.selectionStart = target.selectionEnd =
                      start + spaces.length;
                  }, 0);
                }
              }}
              placeholder="e.g., get_temperature() > 25"
              style={{ width: '100%', height: '150px', marginTop: '0.5rem' }}
            ></textarea>

            <RuleDocumentation />
          </div>
        </div>

        {/* Validation Button */}
        <div className="Buttons" style={{ marginTop: '1rem' }}>
          <button onClick={handleValidation} disabled={validating}>
            {validating ? 'Validating...' : '✓ Validate Rule'}
          </button>
        </div>

        {/* Validation Result */}
        {validationResult && (
          <div style={{ marginTop: '1rem' }}>
            <h4>Validation Result</h4>
            {validationResult.success ? (
              <div style={{ color: 'green' }}>
                ✅ {validationResult.message || 'Rule is valid'}
              </div>
            ) : (
              <div style={{ color: 'red' }}>❌ {validationResult.error}</div>
            )}
          </div>
        )}

        {/* Runtime Error */}
        {lastError && (
          <div style={{ marginTop: '1rem' }}>
            <h4>Runtime Error</h4>
            <div
              style={{
                color: 'red',
                padding: '0.5rem',
                backgroundColor: '#ffe0e0',
                borderRadius: '4px',
              }}
            >
              ⚠️ {lastError}
            </div>
            <div
              style={{ fontSize: '0.9rem', marginTop: '0.5rem', color: '#666' }}
            >
              This error occurred during the last rule evaluation in the
              automation loop.
            </div>
          </div>
        )}

        {/* Submit/Cancel Buttons */}
        <div className="Buttons" style={{ marginTop: '1.5rem' }}>
          <button onClick={onClose} disabled={submitting}>
            Cancel
          </button>
          <button onClick={handleSubmit} disabled={submitDisabled}>
            {submitting
              ? mode === 'create'
                ? 'Adding...'
                : 'Updating...'
              : mode === 'create'
                ? 'Add Relay'
                : 'Update Relay'}
          </button>
        </div>
      </div>
    </FullScreenDialog>
  );
};
