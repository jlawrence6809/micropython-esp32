import { useEffect, useState } from 'preact/hooks';
import { Section } from '../components/Section';

type SensorInfoResponse = {
  Temperature?: number;
  Humidity?: number;
  Light?: number;
  Switch?: number;
};

/**
 * Sensor info is the current state of the sensors on the device.
 */
export const SensorInfo = () => {
  const [sensorInfo, setSensorInfo] = useState<SensorInfoResponse>({});

  useEffect(() => {
    const load = async () => {
      const data = await fetch('/sensor-info');
      const json = await data.json();
      setSensorInfo(json);
    };
    load();
  }, []);

  return (
    <Section className="SensorInfo" title="Sensor Info">
      <p>Temperature: {sensorInfo.Temperature}F</p>
      <p>Humidity: {sensorInfo.Humidity}%</p>
      <p>Light: {sensorInfo.Light}</p>
      <p>Switch: {sensorInfo.Switch}</p>
    </Section>
  );
};
