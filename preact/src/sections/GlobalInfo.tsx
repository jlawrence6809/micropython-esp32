import { useEffect, useState } from 'preact/hooks';
import { Section } from '../components/Section';

type GlobalInfoResponse = {
  ChipId?: string;
  ResetCounter?: string;
  LastResetReason?: string;
  InternalTemperature?: string; // Fahrenheit (stringified)
  CurrentTime?: string;
  Core?: string;
  FreeHeap?: string;
  MinFreeHeap?: string;
  HeapSize?: string;
  FreeSketchSpace?: string;
  SketchSize?: string;
  CpuFrequencyMHz?: string;
  UptimeSeconds?: string;
  WiFiStatus?: string;
  WiFiRSSI?: string;
  IPAddress?: string;
  SSID?: string;
};

// ESP32 reset reasons mapping
const getResetReasonString = (reason?: string | number): string => {
  if (reason === undefined) return 'Unknown';
  const code = typeof reason === 'string' ? parseInt(reason, 10) : reason;
  if (Number.isNaN(code as number)) return `Unknown reset reason (${reason})`;

  switch (code) {
    case 0:
      return 'Reset reason cannot be determined';
    case 1:
      return 'Power-on event';
    case 2:
      return 'Software reset via esp_restart';
    case 3:
      return 'Software reset due to exception/panic';
    case 4:
      return 'Reset due to interrupt watchdog';
    case 5:
      return 'Reset due to task watchdog';
    case 6:
      return 'Reset due to other watchdogs';
    case 7:
      return 'Reset after exiting deep sleep mode';
    case 8:
      return 'Brownout reset';
    case 9:
      return 'Reset over SDIO';
    default:
      return `Unknown reset reason (${code})`;
  }
};

const getWifiStatusString = (status?: string): string => {
  if (status === undefined) return 'Unknown';
  const code = parseInt(status, 10);
  if (Number.isNaN(code)) return status;
  // From WiFiType.h (Arduino-ESP32)
  switch (code) {
    case 0:
      return 'Idle';
    case 1:
      return 'No SSID available';
    case 2:
      return 'Scan completed';
    case 3:
      return 'Connected';
    case 4:
      return 'Connection failed';
    case 5:
      return 'Connection lost';
    case 6:
      return 'Disconnected';
    default:
      return `Status ${code}`;
  }
};

const formatUptime = (uptimeSeconds?: string): string | undefined => {
  if (!uptimeSeconds) return undefined;
  const total = parseInt(uptimeSeconds, 10);
  if (Number.isNaN(total)) return uptimeSeconds;
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
      const data = await fetch('/global-info');
      const json = await data.json();
      setGlobalInfo(json);
    };
    load();
  }, []);

  return (
    <Section className="GlobalInfo" title="Global Info">
      <p>Chip Id: #{globalInfo.ChipId}</p>
      <p>Resets: {globalInfo.ResetCounter}</p>
      <p>
        Last reset reason: {getResetReasonString(globalInfo.LastResetReason)}
      </p>
      <p>Internal temperature: {globalInfo.InternalTemperature}F</p>
      <p>Current time: {globalInfo.CurrentTime}</p>
      <p>Core: {globalInfo.Core}</p>
      <p>CPU: {globalInfo.CpuFrequencyMHz} MHz</p>
      <p>Uptime: {formatUptime(globalInfo.UptimeSeconds)}</p>
      <p>Free heap: {globalInfo.FreeHeap} bytes</p>
      <p>Min free heap: {globalInfo.MinFreeHeap} bytes</p>
      <p>Heap size: {globalInfo.HeapSize} bytes</p>
      <p>Sketch size: {globalInfo.SketchSize} bytes</p>
      <p>Free sketch space: {globalInfo.FreeSketchSpace} bytes</p>
      <p>WiFi status: {getWifiStatusString(globalInfo.WiFiStatus)}</p>
      {globalInfo.WiFiStatus === '3' && (
        <>
          <p>SSID: {globalInfo.SSID}</p>
          <p>IP: {globalInfo.IPAddress}</p>
          <p>RSSI: {globalInfo.WiFiRSSI} dBm</p>
        </>
      )}
    </Section>
  );
};
