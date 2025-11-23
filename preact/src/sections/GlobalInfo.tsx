import { useEffect, useState } from 'preact/hooks';
import { Section } from '../components/Section';

/**
 * Global info is the current state of the device.
 * The backend sends a dynamic key-value object that we render as-is.
 */
export const GlobalInfo = () => {
  const [globalInfo, setGlobalInfo] = useState<Record<
    string,
    string | number
  > | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetch('/api/status');
        const json = await data.json();
        setGlobalInfo(json);
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
      {Object.entries(globalInfo).map(([key, value]) => (
        <p key={key}>
          <strong>{key}:</strong> {value}
        </p>
      ))}
    </Section>
  );
};
