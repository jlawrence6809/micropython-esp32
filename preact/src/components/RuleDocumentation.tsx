import { useState } from 'preact/hooks';

export const RuleDocumentation = () => {
  const [docsExpanded, setDocsExpanded] = useState<boolean>(false);
  return (
    <details
      style={{ marginTop: '0.5rem', fontSize: '0.9em' }}
      open={docsExpanded}
      onToggle={(e) => setDocsExpanded(e.currentTarget.open)}
    >
      <summary style={{ cursor: 'pointer', userSelect: 'none' }}>
        📖 Rule Documentation
      </summary>
      <div
        style={{
          marginTop: '0.5rem',
          padding: '0.75rem',
          background: '#f5f5f5',
          borderRadius: '4px',
          maxHeight: '300px',
          overflowY: 'auto',
          color: 'black',
        }}
      >
        <h4 style={{ marginTop: 0 }}>Return Values</h4>
        <ul style={{ marginLeft: '1.5rem', marginBottom: '1rem' }}>
          <li>
            <code>True</code> → Turn relay ON
          </li>
          <li>
            <code>False</code> → Turn relay OFF
          </li>
          <li>
            <code>None</code> → Keep current state (no change)
          </li>
        </ul>

        <h4>Available Functions</h4>
        <ul style={{ marginLeft: '1.5rem', marginBottom: '1rem' }}>
          <li>
            <code>get_temperature()</code> - Temperature in °C
          </li>
          <li>
            <code>get_humidity()</code> - Humidity %
          </li>
          <li>
            <code>get_switch_state()</code> - Light switch (True when pressed)
          </li>
          <li>
            <code>get_time()</code> - Seconds since midnight
          </li>
          <li>
            <code>time(hour, minute)</code> - Convert time to seconds
          </li>
          <li>
            <code>get_last_*()</code> - Previous sensor values (for edge
            detection)
          </li>
        </ul>

        <h4>Examples</h4>
        <div style={{ marginBottom: '0.5rem' }}>
          <strong>Simple condition:</strong>
          <pre
            style={{
              background: '#fff',
              padding: '0.5rem',
              borderRadius: '4px',
              overflow: 'auto',
            }}
          >
            get_temperature() &gt; 25
          </pre>
        </div>

        <div style={{ marginBottom: '0.5rem' }}>
          <strong>Time range (8 AM to 6 PM):</strong>
          <pre
            style={{
              background: '#fff',
              padding: '0.5rem',
              borderRadius: '4px',
              overflow: 'auto',
            }}
          >
            time(8, 0) &lt;= get_time() &lt; time(18, 0)
          </pre>
        </div>

        <div style={{ marginBottom: '0.5rem' }}>
          <strong>Toggle on switch press:</strong>
          <pre
            style={{
              background: '#fff',
              padding: '0.5rem',
              borderRadius: '4px',
              overflow: 'auto',
            }}
          >
            {`True if (get_switch_state() and not get_last_switch_state()) else None`}
          </pre>
        </div>

        <div style={{ marginBottom: '0.5rem' }}>
          <strong>Multi-line with variables:</strong>
          <pre
            style={{
              background: '#fff',
              padding: '0.5rem',
              borderRadius: '4px',
              overflow: 'auto',
            }}
          >
            {`temp = get_temperature()
humidity = get_humidity()

if temp > 25 and humidity > 60:
result = True
elif temp < 20:
result = False
else:
result = None  # Keep current state`}
          </pre>
        </div>

        <div>
          <strong>Hysteresis (avoid rapid switching):</strong>
          <pre
            style={{
              background: '#fff',
              padding: '0.5rem',
              borderRadius: '4px',
              overflow: 'auto',
            }}
          >
            {`temp = get_temperature()
result = True if temp > 25 else (False if temp < 23 else None)`}
          </pre>
        </div>

        <p
          style={{
            marginTop: '1rem',
            fontSize: '0.85em',
            color: '#666',
          }}
        >
          💡 <strong>Tip:</strong> Use Tab to indent, and set{' '}
          <code>result = ...</code> in multi-line rules
        </p>
      </div>
    </details>
  );
};
