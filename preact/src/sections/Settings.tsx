import { useEffect, useState } from 'preact/hooks';
import { Section } from '../components/Section';
import { fetchConfig, fetchAvailableBoards, postConfig } from '../api';

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
    </Section>
  );
};
