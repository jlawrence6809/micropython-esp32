import { useState, useEffect } from 'preact/hooks';
import { Section } from '../components/Section';

type Network = {
  ssid: string;
  rssi: number;
  security: string;
};

type WiFiStatus = {
  sta_active: boolean;
  sta_connected: boolean;
  sta_ip?: string;
  sta_ssid?: string;
  sta_rssi?: number;
  ap_active: boolean;
  ap_ip?: string;
  ap_ssid?: string;
};

/**
 * WiFi configuration form with network scanning.
 */
export const WifiForm = () => {
  const [networks, setNetworks] = useState<Network[]>([]);
  const [scanning, setScanning] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [status, setStatus] = useState<WiFiStatus | null>(null);
  const [selectedSsid, setSelectedSsid] = useState('');
  const [password, setPassword] = useState('');

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      const response = await fetch('/api/wifi/status');
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      console.error('Failed to load WiFi status:', err);
    }
  };

  const scanNetworks = async () => {
    setScanning(true);
    try {
      const response = await fetch('/api/wifi/scan');
      const data = await response.json();
      setNetworks(data.networks || []);
    } catch (err) {
      alert('Failed to scan networks');
    } finally {
      setScanning(false);
    }
  };

  const onSubmit = async (e: Event) => {
    e.preventDefault();
    if (!selectedSsid || !password) {
      alert('Please enter SSID and password');
      return;
    }

    setConnecting(true);
    try {
      const response = await fetch('/api/wifi/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ssid: selectedSsid, password, save: true }),
      });
      const data = await response.json();
      
      if (data.status === 'success') {
        alert(`Connected to ${selectedSsid}!\nIP: ${data.ip}\n\nDevice will now be accessible at this IP address.`);
        // Reload status after connection
        setTimeout(loadStatus, 2000);
      } else {
        alert(`Failed to connect: ${data.message}`);
      }
    } catch (err) {
      alert('Failed to send WiFi credentials');
    } finally {
      setConnecting(false);
    }
  };

  return (
    <Section title="WiFi Settings">
      {status && (
        <div style={{ marginBottom: '1rem', padding: '0.5rem', background: '#333', borderRadius: '4px' }}>
          <strong>Current Status:</strong>
          {status.sta_connected ? (
            <div style={{ color: '#4CAF50' }}>
              ✓ Connected to {status.sta_ssid} ({status.sta_ip})
              <br />
              Signal: {status.sta_rssi} dBm
            </div>
          ) : status.ap_active ? (
            <div style={{ color: '#FF9800' }}>
              ⚠ AP Mode: {status.ap_ssid} ({status.ap_ip})
              <br />
              Connect to this network to configure WiFi
            </div>
          ) : (
            <div style={{ color: '#F44336' }}>✗ Not connected</div>
          )}
        </div>
      )}

      <form className="WifiForm" onSubmit={onSubmit}>
        <div style={{ marginBottom: '1rem' }}>
          <button
            type="button"
            onClick={scanNetworks}
            disabled={scanning}
            style={{ marginBottom: '0.5rem' }}
          >
            {scanning ? 'Scanning...' : '📡 Scan Networks'}
          </button>

          {networks.length > 0 && (
            <select
              value={selectedSsid}
              onChange={(e) => setSelectedSsid(e.currentTarget.value)}
              style={{ width: '100%', padding: '0.5rem', marginBottom: '0.5rem' }}
            >
              <option value="">Select a network...</option>
              {networks.map((net) => (
                <option key={net.ssid} value={net.ssid}>
                  {net.ssid} ({net.rssi} dBm, {net.security})
                </option>
              ))}
            </select>
          )}

          <label for="ssid">WiFi Name (SSID)</label>
          <input
            type="text"
            id="ssid"
            name="ssid"
            value={selectedSsid}
            onChange={(e) => setSelectedSsid(e.currentTarget.value)}
            placeholder="Enter SSID manually or select above"
            style={{ width: '100%', padding: '0.5rem' }}
          />
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label for="password">WiFi Password</label>
          <input
            type="password"
            id="password"
            name="password"
            value={password}
            onChange={(e) => setPassword(e.currentTarget.value)}
            placeholder="Enter password"
            style={{ width: '100%', padding: '0.5rem' }}
          />
        </div>

        <button type="submit" disabled={connecting || !selectedSsid || !password}>
          {connecting ? 'Connecting...' : 'Connect & Save'}
        </button>
      </form>
    </Section>
  );
};
