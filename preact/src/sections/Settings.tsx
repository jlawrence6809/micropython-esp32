import { useEffect, useState } from 'preact/hooks';
import { Section } from '../components/Section';
import {
  fetchConfig,
  fetchAvailableBoards,
  postConfig,
  postTimeSet,
} from '../api';

interface Board {
  filename: string;
  name: string;
  chip: string;
  description?: string;
}

export const Settings = () => {
  const [hostname, setHostname] = useState('');
  const [board, setBoard] = useState('');
  const [currentBoardName, setCurrentBoardName] = useState('');
  const [availableBoards, setAvailableBoards] = useState<Board[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  // Time setting state
  const [timeHour, setTimeHour] = useState('12');
  const [timeMinute, setTimeMinute] = useState('0');
  const [settingTime, setSettingTime] = useState(false);

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const [config, boards] = await Promise.all([
          fetchConfig(),
          fetchAvailableBoards(),
        ]);

        setHostname(config.hostname || '');
        let boardValue = config.board || '';
        if (boardValue && !boardValue.endsWith('.json')) {
          boardValue = boardValue + '.json';
        }
        setBoard(boardValue);
        setCurrentBoardName(config.board_name || '');
        setAvailableBoards(boards || []);
        setLoading(false);
      } catch (error) {
        console.error('Failed to load config:', error);
        setMessage({ type: 'error', text: 'Failed to load configuration' });
        setLoading(false);
      }
    };

    loadConfig();
  }, []);

  const handleSave = async (e: Event) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    try {
      const result = await postConfig({
        hostname: hostname || undefined,
        board: board || undefined,
      });

      if (result.status === 'success') {
        setMessage({
          type: 'success',
          text: result.message || 'Configuration saved successfully!',
        });

        if (result.restart_required) {
          setTimeout(() => {
            setMessage({
              type: 'success',
              text: 'Configuration saved! Please restart the device for changes to take effect.',
            });
          }, 1000);
        }
      } else {
        setMessage({
          type: 'error',
          text: result.message || 'Failed to save configuration',
        });
      }
    } catch (error) {
      console.error('Save error:', error);
      setMessage({ type: 'error', text: 'Failed to save configuration' });
    } finally {
      setSaving(false);
    }
  };

  const handleSetTime = async (e: Event) => {
    e.preventDefault();
    setSettingTime(true);
    setMessage(null);

    try {
      const hour = parseInt(timeHour, 10);
      const minute = parseInt(timeMinute, 10);

      if (isNaN(hour) || isNaN(minute)) {
        setMessage({ type: 'error', text: 'Invalid time values' });
        return;
      }

      const result = await postTimeSet(hour, minute);

      if (result.status === 'success') {
        setMessage({
          type: 'success',
          text: `Time set to ${result.current_time}`,
        });
      } else {
        setMessage({
          type: 'error',
          text: result.message || 'Failed to set time',
        });
      }
    } catch (error) {
      console.error('Set time error:', error);
      setMessage({ type: 'error', text: 'Failed to set time' });
    } finally {
      setSettingTime(false);
    }
  };

  if (loading) {
    return <Section title="Settings">Loading...</Section>;
  }

  return (
    <Section className="Settings" title="Settings">
      <form onSubmit={handleSave}>
        <div className="FormGroup">
          <label htmlFor="hostname">
            <strong>Hostname:</strong>
          </label>
          <input
            id="hostname"
            type="text"
            value={hostname}
            onInput={(e) => setHostname((e.target as HTMLInputElement).value)}
            placeholder="esp32"
            pattern="[a-zA-Z0-9\-_]+"
            title="Only letters, numbers, hyphens, and underscores allowed"
          />
          <small>
            Used for mDNS ({hostname || 'esp32'}.local) and AP mode SSID
          </small>
        </div>

        <div className="FormGroup">
          <label htmlFor="board">
            <strong>Board Configuration:</strong>
          </label>
          <select
            id="board"
            value={board}
            onChange={(e) => setBoard((e.target as HTMLSelectElement).value)}
          >
            {availableBoards.map((b) => (
              <option key={b.filename} value={b.filename}>
                {b.name} ({b.chip})
              </option>
            ))}
          </select>
          <small>Current: {currentBoardName}</small>
        </div>

        {message && (
          <div className={`Message ${message.type}`}>{message.text}</div>
        )}

        <button type="submit" disabled={saving}>
          {saving ? 'Saving...' : 'Save Configuration'}
        </button>
      </form>

      <hr
        style={{
          margin: '2rem 0',
          border: 'none',
          borderTop: '1px solid #333',
        }}
      />

      <form onSubmit={handleSetTime}>
        <h3>Manual Time Setting</h3>
        <p style={{ fontSize: '0.9rem', color: '#aaa', marginBottom: '1rem' }}>
          Use this to manually set the time when WiFi/NTP is unavailable (e.g.,
          in AP mode). The time will be saved and used as a fallback on future
          boots.
        </p>

        <div
          className="FormGroup"
          style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}
        >
          <div style={{ flex: 1 }}>
            <label htmlFor="timeHour">
              <strong>Hour (0-23):</strong>
            </label>
            <input
              id="timeHour"
              type="number"
              min="0"
              max="23"
              value={timeHour}
              onInput={(e) => setTimeHour((e.target as HTMLInputElement).value)}
              required
            />
          </div>

          <div style={{ flex: 1 }}>
            <label htmlFor="timeMinute">
              <strong>Minute (0-59):</strong>
            </label>
            <input
              id="timeMinute"
              type="number"
              min="0"
              max="59"
              value={timeMinute}
              onInput={(e) =>
                setTimeMinute((e.target as HTMLInputElement).value)
              }
              required
            />
          </div>

          <button type="submit" disabled={settingTime} style={{ flex: 1 }}>
            {settingTime ? 'Setting...' : 'Set Time'}
          </button>
        </div>
      </form>
    </Section>
  );
};
