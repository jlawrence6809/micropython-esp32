import { useEffect, useState } from 'preact/hooks';
import { Section } from '../components/Section';
import { fetchSensors, fetchSensorConfig, postSensorConfig } from '../api';
import { SensorData, SensorPins } from '../types';

const SENSOR_DATA_TIMER = 30000;

/**
 * Format temperature for display
 */
const formatTemp = (temp: number | null): string => {
  if (temp === null) return '--';
  return `${temp.toFixed(1)}°C`;
};

/**
 * Format humidity for display
 */
const formatHumidity = (humidity: number | null): string => {
  if (humidity === null) return '--';
  return `${humidity.toFixed(0)}%`;
};

/**
 * Format light level for display
 */
const formatLight = (level: number | null): string => {
  if (level === null) return '--';
  return level.toString();
};

/**
 * Pin selector dropdown component
 */
const PinSelect = ({
  id,
  label,
  value,
  options,
  onChange,
  description,
}: {
  id: string;
  label: string;
  value: number;
  options: number[];
  onChange: (value: number) => void;
  description?: string;
}) => (
  <div className="FormGroup">
    <label htmlFor={id}>
      <strong>{label}:</strong>
    </label>
    <select
      id={id}
      value={value}
      onChange={(e) =>
        onChange(parseInt((e.target as HTMLSelectElement).value, 10))
      }
    >
      <option value={-1}>Disabled</option>
      {options.map((pin) => (
        <option key={pin} value={pin}>
          GPIO {pin}
        </option>
      ))}
    </select>
    {description && <small>{description}</small>}
  </div>
);

/**
 * Sensor info displays the current state of the sensors on the device
 * and allows configuration of sensor pins.
 */
export const SensorInfo = () => {
  // Sensor data state
  const [sensorData, setSensorData] = useState<SensorData | null>(null);
  const [sensorDataError, setSensorDataError] = useState<string | null>(null);

  // Configuration state
  const [showConfig, setShowConfig] = useState(false);
  const [sensorPins, setSensorPins] = useState<SensorPins | null>(null);
  const [availablePins, setAvailablePins] = useState<number[]>([]);
  const [adc1Pins, setAdc1Pins] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  // Load sensor data periodically
  useEffect(() => {
    const loadSensorData = async () => {
      try {
        const data = await fetchSensors();
        setSensorData(data);
        setSensorDataError(null);
      } catch (error) {
        console.error('Failed to load sensors:', error);
        setSensorDataError('Failed to load sensor data');
      }
    };

    loadSensorData();
    const interval = setInterval(loadSensorData, SENSOR_DATA_TIMER);
    return () => clearInterval(interval);
  }, []);

  // Load configuration when config panel is opened
  useEffect(() => {
    if (!showConfig) return;

    const loadConfig = async () => {
      setLoading(true);
      try {
        const config = await fetchSensorConfig();
        setSensorPins(config.sensor_pins);
        setAvailablePins(config.available_pins);
        setAdc1Pins(config.adc1_pins);
      } catch (error) {
        console.error('Failed to load sensor config:', error);
        setMessage({ type: 'error', text: 'Failed to load configuration' });
      } finally {
        setLoading(false);
      }
    };

    loadConfig();
  }, [showConfig]);

  const handlePinChange = (key: keyof SensorPins, value: number) => {
    if (!sensorPins) return;
    setSensorPins({ ...sensorPins, [key]: value });
    setMessage(null);
  };

  const handleSave = async (e: Event) => {
    e.preventDefault();
    if (!sensorPins) return;

    setSaving(true);
    setMessage(null);

    try {
      const result = await postSensorConfig(sensorPins);

      if (result.status === 'success') {
        setMessage({
          type: 'success',
          text: result.message || 'Configuration saved!',
        });
      } else {
        setMessage({
          type: 'error',
          text: 'Failed to save configuration',
        });
      }
    } catch (error) {
      console.error('Save error:', error);
      setMessage({ type: 'error', text: 'Failed to save configuration' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Section className="SensorInfo Settings" title="Sensor Info">
      {/* Current Sensor Values */}
      <div style={{ marginBottom: '1rem' }}>
        {sensorDataError ? (
          <p style={{ color: '#f88' }}>{sensorDataError}</p>
        ) : sensorData ? (
          <>
            <p>
              <strong>Temperature:</strong> {formatTemp(sensorData.temperature)}
            </p>
            <p>
              <strong>Humidity:</strong> {formatHumidity(sensorData.humidity)}
            </p>
            <p>
              <strong>Light Level:</strong>{' '}
              {formatLight(sensorData.light_level)}
              {sensorData.light_level !== null && ' (0-4095)'}
            </p>
            <p>
              <strong>Light Switch:</strong>{' '}
              {sensorData.switch_state ? 'Pressed' : 'Released'}
            </p>
            <p>
              <strong>Reset Switch:</strong>{' '}
              {sensorData.reset_switch_state ? 'Pressed' : 'Released'}
            </p>
          </>
        ) : (
          <p>Loading sensor data...</p>
        )}
      </div>

      {/* Configuration Toggle */}
      <button
        type="button"
        onClick={() => setShowConfig(!showConfig)}
        style={{ marginBottom: '1rem' }}
      >
        {showConfig ? 'Hide Pin Configuration' : 'Configure Sensor Pins'}
      </button>

      {/* Configuration Panel */}
      {showConfig && (
        <form onSubmit={handleSave}>
          {loading ? (
            <p>Loading configuration...</p>
          ) : sensorPins ? (
            <>
              <h3 style={{ marginTop: 0 }}>I2C Sensors (AHT21)</h3>
              <p
                style={{
                  fontSize: '0.9rem',
                  color: '#aaa',
                  marginBottom: '1rem',
                }}
              >
                For temperature/humidity sensors using I2C. Both SCL and SDA
                must be set for I2C to work.
              </p>

              <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: '150px' }}>
                  <PinSelect
                    id="i2c_scl"
                    label="I2C SCL"
                    value={sensorPins.i2c_scl}
                    options={availablePins}
                    onChange={(v) => handlePinChange('i2c_scl', v)}
                  />
                </div>
                <div style={{ flex: 1, minWidth: '150px' }}>
                  <PinSelect
                    id="i2c_sda"
                    label="I2C SDA"
                    value={sensorPins.i2c_sda}
                    options={availablePins}
                    onChange={(v) => handlePinChange('i2c_sda', v)}
                  />
                </div>
              </div>

              <hr
                style={{
                  margin: '1.5rem 0',
                  border: 'none',
                  borderTop: '1px solid #444',
                }}
              />

              <h3>OneWire Temperature (DS18B20)</h3>
              <PinSelect
                id="ds18b20"
                label="DS18B20 Pin"
                value={sensorPins.ds18b20}
                options={availablePins}
                onChange={(v) => handlePinChange('ds18b20', v)}
                description="Digital temperature sensor using OneWire protocol"
              />

              <hr
                style={{
                  margin: '1.5rem 0',
                  border: 'none',
                  borderTop: '1px solid #444',
                }}
              />

              <h3>Analog Light Sensor</h3>
              <p
                style={{
                  fontSize: '0.9rem',
                  color: '#aaa',
                  marginBottom: '1rem',
                }}
              >
                Only ADC1 pins are shown. ADC2 pins cannot be used when WiFi is
                active.
              </p>
              <PinSelect
                id="photo_sensor"
                label="Photo Sensor Pin"
                value={sensorPins.photo_sensor}
                options={adc1Pins}
                onChange={(v) => handlePinChange('photo_sensor', v)}
                description="Analog photo resistor for light level detection"
              />

              <hr
                style={{
                  margin: '1.5rem 0',
                  border: 'none',
                  borderTop: '1px solid #444',
                }}
              />

              <h3>Digital Switches</h3>
              <p
                style={{
                  fontSize: '0.9rem',
                  color: '#aaa',
                  marginBottom: '1rem',
                }}
              >
                Digital inputs with internal pull-up resistors. Active when
                grounded.
              </p>

              <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: '150px' }}>
                  <PinSelect
                    id="light_switch"
                    label="Light Switch"
                    value={sensorPins.light_switch}
                    options={availablePins}
                    onChange={(v) => handlePinChange('light_switch', v)}
                  />
                </div>
                <div style={{ flex: 1, minWidth: '150px' }}>
                  <PinSelect
                    id="reset_switch"
                    label="Reset Switch"
                    value={sensorPins.reset_switch}
                    options={availablePins}
                    onChange={(v) => handlePinChange('reset_switch', v)}
                  />
                </div>
              </div>

              {message && (
                <div
                  className={`Message ${message.type}`}
                  style={{ marginTop: '1rem' }}
                >
                  {message.text}
                </div>
              )}

              <button
                type="submit"
                disabled={saving}
                style={{ marginTop: '1rem' }}
              >
                {saving ? 'Saving...' : 'Save Pin Configuration'}
              </button>
            </>
          ) : (
            <p style={{ color: '#f88' }}>Failed to load configuration</p>
          )}
        </form>
      )}
    </Section>
  );
};
