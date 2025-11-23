import { useEffect, useState } from 'preact/hooks';
import { Section } from '../components/Section';

// todo: look into supporting more
type GlobalInfoResponse = {
  platform?: string;
  memory_free?: number;
  memory_alloc?: number;
  uptime_seconds?: number;
  frequency?: number;
};

const formatUptime = (uptimeSeconds?: number): string | undefined => {
  if (uptimeSeconds === undefined) return undefined;
  const total = uptimeSeconds;
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  const parts = [] as string[];
  if (days) parts.push(`${days}d`);
  parts.push(`${hours}h`, `${minutes}m`, `${seconds}s`);
  return parts.join(' ');
};

/**
 * Global info is the current state of the device.
 */
export const GlobalInfo = () => {
  const [globalInfo, setGlobalInfo] = useState<GlobalInfoResponse>({});

  useEffect(() => {
    const load = async () => {
      const data = await fetch('/api/status');
      const json = await data.json();
      setGlobalInfo(json);
    };
    load();
  }, []);

  return (
    <Section className="GlobalInfo" title="Global Info">
      <p>Platform: {globalInfo.platform}</p>
      <p>
        CPU: {globalInfo.frequency ? globalInfo.frequency / 1000000 : 0} MHz
      </p>
      <p>Uptime: {formatUptime(globalInfo.uptime_seconds)}</p>
      <p>Free heap: {globalInfo.memory_free} bytes</p>
      <p>Allocated heap: {globalInfo.memory_alloc} bytes</p>
    </Section>
  );
};
