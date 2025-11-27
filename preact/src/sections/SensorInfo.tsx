import { useEffect, useState } from 'preact/hooks';
import { Section } from '../components/Section';
import { fetchSensors } from '../api';

type SensorInfoResponse = {
  Temperature?: number;
  Humidity?: number;
  Light?: number;
  Switch?: number; // Note: Switch is a boolean in backend dummy data but number in old API?
  // Backend sends: "Switch": False. JSON boolean.
  // Let's update type to accept boolean or number
};

/**
 * Sensor info is the current state of the sensors on the device.
 */
export const SensorInfo = () => {
  // Use 'any' for now to tolerate slight mismatches or different types
  const [sensorInfo, setSensorInfo] = useState<any>({});

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchSensors();
        setSensorInfo(data);
      } catch (error) {
        console.error('Failed to load sensors:', error);
      }
    };
    load();
  }, []);

  return (
    <Section className="SensorInfo" title="Sensor Info">
      <p>Temperature: {sensorInfo.Temperature}F</p>
      <p>Humidity: {sensorInfo.Humidity}%</p>
      <p>Light: {sensorInfo.Light}</p>
      <p>Switch: {String(sensorInfo.Switch)}</p>
    </Section>
  );
};
