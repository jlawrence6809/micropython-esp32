import { RelayConfigDto, RelayConfig } from './types';

export const fetchRelayConfig = async () => {
  const data = await fetch('/api/relays/config');
  const json: RelayConfigDto = await data.json();
  return json;
};

export const fetchGpioOptions = async () => {
  const data = await fetch('/api/gpio/available');
  const json = await data.json();
  const options = Object.keys(json).map((k) => parseInt(k, 10));
  return options;
};

export const postRelayConfig = async (updatedConfigs: RelayConfig[]) => {
  const config: RelayConfigDto = {
    count: updatedConfigs.length,
    relays: updatedConfigs,
  };

  const response = await fetch('/api/relays/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });

  // todo: should we process the response?
  return response;
};

export interface ValidationResponse {
  success: boolean;
  message?: string;
  error?: string;
}

export const validateRule = async (
  rule: string,
): Promise<ValidationResponse> => {
  const response = await fetch('/api/validate-rule', {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: rule,
  });

  if (!response.ok) {
    throw new Error(
      `Validation request failed: ${response.status} ${response.statusText}`,
    );
  }

  return await response.json();
};

// Config API
export const fetchConfig = async () => {
  const response = await fetch('/api/config');
  return await response.json();
};

export const fetchAvailableBoards = async () => {
  const response = await fetch('/api/boards');
  const json = await response.json();
  return json.boards;
};

export const postConfig = async (config: {
  hostname?: string;
  board?: string;
}) => {
  const response = await fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  return await response.json();
};

// Status API
export const fetchStatus = async () => {
  const response = await fetch('/api/status');
  return await response.json();
};

// Sensor API
export const fetchSensors = async () => {
  const response = await fetch('/api/sensors');
  return await response.json();
};

// WiFi API
export const fetchWifiStatus = async () => {
  const response = await fetch('/api/wifi/status');
  return await response.json();
};

export const fetchWifiScan = async () => {
  const response = await fetch('/api/wifi/scan');
  const data = await response.json();
  return data.networks || [];
};

export const postWifiConnect = async (
  ssid: string,
  password: string,
  save: boolean = true,
) => {
  const response = await fetch('/api/wifi/connect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ssid, password, save }),
  });
  return await response.json();
};

// System API
export const postRestart = async () => {
  const response = await fetch('/api/restart', { method: 'POST' });
  return await response.json();
};
