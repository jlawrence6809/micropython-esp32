import { useEffect, useState } from 'preact/hooks';
import { Section } from '../components/Section';
import { fetchStatus } from '../api';

/**
 * Global info is the current state of the device.
 * The backend sends an ordered array of key-value pairs.
 */
interface StatusItem {
  key: string;
  value: string | number;
}

export const GlobalInfo = () => {
  const [globalInfo, setGlobalInfo] = useState<StatusItem[] | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchStatus();
        setGlobalInfo(data);
      } catch (error) {
        console.error('Failed to load global info:', error);
        setGlobalInfo(null);
      }
    };
    load();

    // Refresh every 60 seconds
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, []);

  if (globalInfo === null) {
    return (
      <Section className="GlobalInfo" title="System Info">
        <p>Loading...</p>
      </Section>
    );
  }

  return (
    <Section className="GlobalInfo" title="System Info">
      {globalInfo.map((item, index) => (
        <p key={index}>
          <strong>{item.key}:</strong> {item.value}
        </p>
      ))}
    </Section>
  );
};
