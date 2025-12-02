import { RelayConfigDto, RelayConfig } from './types';

// ============================================================================
// Request Queue & Deduplication
// ============================================================================

// Global request queue - ensures sequential API calls
let requestQueue: Promise<any> = Promise.resolve();

// In-flight request tracking - prevents duplicate requests
const inFlightRequests = new Map<string, Promise<any>>();

/**
 * Queued fetch with deduplication.
 * - Prevents duplicate concurrent requests to same endpoint
 * - Spaces out requests by 100ms to avoid overwhelming ESP32
 */
async function queuedFetch(
  url: string,
  options?: RequestInit,
): Promise<Response> {
  // Create unique key for this request
  const key = `${url}:${JSON.stringify(options || {})}`;

  // Deduplication: if same request is already in-flight, return that promise
  if (inFlightRequests.has(key)) {
    return await inFlightRequests.get(key);
  }

  // Add to queue - chain to previous request completion
  const promise = requestQueue.then(async () => {
    // 100ms delay before this request
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Execute the actual fetch
    const response = await fetch(url, options);
    return response;
  });

  // Update queue to this request's completion (catch errors so queue continues)
  requestQueue = promise.catch(() => {});
  inFlightRequests.set(key, promise);

  try {
    return await promise;
  } catch (error) {
    console.error(`[queuedFetch] Fetch error: ${key}`, error);
    throw error;
  } finally {
    // Clean up after request completes
    inFlightRequests.delete(key);
  }
}

// ============================================================================
// API Functions
// ============================================================================

export const fetchRelayConfig = async () => {
  const data = await queuedFetch('/api/relays/config');
  const json: RelayConfigDto = await data.json();
  return json;
};

export const fetchGpioOptions = async () => {
  const data = await queuedFetch('/api/gpio/available');
  const json = await data.json();
  const options = Object.keys(json).map((k) => parseInt(k, 10));
  return options;
};

export const postRelayConfig = async (updatedConfigs: RelayConfig[]) => {
  const config: RelayConfigDto = {
    count: updatedConfigs.length,
    relays: updatedConfigs,
  };

  const response = await queuedFetch('/api/relays/config', {
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
  const response = await queuedFetch('/api/validate-rule', {
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
  const response = await queuedFetch('/api/config');
  return await response.json();
};

export const fetchAvailableBoards = async () => {
  const response = await queuedFetch('/api/boards');
  const json = await response.json();
  return json.boards;
};

export const postConfig = async (config: {
  hostname?: string;
  board?: string;
}) => {
  const response = await queuedFetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  return await response.json();
};

// Status API
export const fetchStatus = async () => {
  const response = await queuedFetch('/api/status');
  return await response.json();
};

// Sensor API
export const fetchSensors = async () => {
  const response = await queuedFetch('/api/sensors');
  return await response.json();
};

// WiFi API
export const fetchWifiStatus = async () => {
  const response = await queuedFetch('/api/wifi/status');
  return await response.json();
};

export const fetchWifiScan = async () => {
  const response = await queuedFetch('/api/wifi/scan');
  const data = await response.json();
  return data.networks || [];
};

export const postWifiConnect = async (
  ssid: string,
  password: string,
  save: boolean = true,
) => {
  const response = await queuedFetch('/api/wifi/connect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ssid, password, save }),
  });
  return await response.json();
};

// System API
export const postRestart = async () => {
  const response = await queuedFetch('/api/restart', { method: 'POST' });
  return await response.json();
};

// Time API
export const postTimeSet = async (hour: number, minute: number) => {
  const response = await queuedFetch('/api/time/set', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hour, minute }),
  });
  return await response.json();
};
