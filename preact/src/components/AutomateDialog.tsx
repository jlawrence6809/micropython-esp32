import { useState, useEffect } from 'preact/hooks';
import { validateRule, ValidationResponse } from '../api';
import { FullScreenDialog } from './Dialog';

type AutomateDialogProps = {
  isOpen: boolean;
  label: string;
  initialRule: string;
  onLabelChange: (newLabel: string) => Promise<void>;
  onRuleSubmit: (rule: string) => Promise<void>;
  onClose: () => void;
};

export const AutomateDialog = ({
  isOpen,
  label,
  initialRule,
  onLabelChange,
  onRuleSubmit,
  onClose,
}: AutomateDialogProps) => {
  const [rule, setRule] = useState<string>(initialRule);
  const [validationResult, setValidationResult] = useState<ValidationResponse | null>(null);
  const [validating, setValidating] = useState<boolean>(false);
  const submitDisabled =
    !validationResult || !validationResult.success;

  // Update rule when dialog opens with new data
  useEffect(() => {
    if (isOpen) {
      setRule(initialRule);
      setValidationResult(null);
    }
  }, [isOpen, initialRule]);

  if (!isOpen) return <></>;

  const submit = async () => {
    if (submitDisabled) {
      return;
    }
    try {
      await onRuleSubmit(rule);
      onClose();
    } catch (error) {
      console.error(error);
      alert('Error submitting rule');
    }
  };

  const handleLabelChange = async (newLabel: string) => {
    if (newLabel !== label) {
      try {
        await onLabelChange(newLabel);
      } catch (error) {
        console.error(error);
        alert('Error updating label');
      }
    }
  };

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
        error: {
          message: `Network error: ${error.message}`,
          path: []
        }
      });
    } finally {
      setValidating(false);
    }
  };

  return (
    <FullScreenDialog onClose={onClose}>
      <div className="AutomateDialog">
        <h3>
          <span
            contentEditable
            onBlur={(ev) =>
              handleLabelChange(ev.currentTarget.textContent.trim())
            }
          >
            {label}
          </span>
          <sup className="Pencil">✏️</sup>
        </h3>
        <textarea
          value={rule}
          onChange={(ev) => setRule(ev.currentTarget.value)}
          style={{ width: '100%', height: '200px' }}
        ></textarea>

        <div className="Buttons">
          <button onClick={handleValidation} disabled={validating}>
            {validating ? 'Validating...' : 'Validate'}
          </button>
          <button onClick={() => submit()} disabled={submitDisabled}>
            Submit
          </button>
        </div>

        {/* display validation result */}
        {validationResult && (
          <div>
            <h4>Validation Result</h4>
            {validationResult.success ? (
              <div style={{ color: 'green' }}>
                ✅ Rule is valid (returns type {validationResult.returnType})
              </div>
            ) : (
              <div style={{ color: 'red' }}>
                ❌ {validationResult.error?.message}
                {validationResult.error?.path?.length > 0 && (
                  <div>Path: [{validationResult.error.path.join(', ')}]</div>
                )}
              </div>
            )}
          </div>
        )}

        {/* display current sensor actuator values */}
      </div>
    </FullScreenDialog>
  );
};
