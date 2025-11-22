import { RelayConfigDto, RelayConfig } from './types';

export const fetchRelayConfig = async () => {
  const data = await fetch('/relay-config');
  const json: RelayConfigDto = await data.json();
  return json;
};

export const fetchGpioOptions = async () => {
  const data = await fetch('/gpio-options');
  const json = await data.json();
  const options = Object.keys(json).map((k) => parseInt(k, 10));
  return options;
};

export const postRelayConfig = async (updatedConfigs: RelayConfig[]) => {
  const config: RelayConfigDto = {
    count: updatedConfigs.length,
    relays: updatedConfigs,
  };

  const response = await fetch('/relay-config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });

  // todo: should we process the response?
  return response;
};

export interface ValidationResponse {
  success: boolean;
  error?: {
    message: string;
    path: number[];
  };
  returnType?: number;
}

export const validateRule = async (
  rule: string,
): Promise<ValidationResponse> => {
  const response = await fetch('/validate-rule', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    // Send the raw JSON rule (e.g., ["GT",5,3]) without wrapping in an object
    body: rule,
  });

  if (!response.ok) {
    throw new Error(
      `Validation request failed: ${response.status} ${response.statusText}`,
    );
  }

  return await response.json();
};
