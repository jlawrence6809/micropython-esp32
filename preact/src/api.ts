import { RelayConfigDto, RelayConfig } from './types';

export const fetchRelayConfig = async () => {
  const data = await fetch('/api/relays/config');
  const json: RelayConfigDto = await data.json();
  return json;
};

export const fetchGpioOptions = async () => {
  // TODO: Implement /api/gpio/available on backend
  // For now, return a static list or empty list to avoid 404
  // const data = await fetch('/api/gpio/available');
  // const json = await data.json();
  // const options = Object.keys(json).map((k) => parseInt(k, 10));
  return [
    0, 1, 2, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32,
    33,
  ];
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
  error?: {
    message: string;
    path: number[];
  };
  returnType?: number;
}

export const validateRule = async (
  rule: string,
): Promise<ValidationResponse> => {
  // const response = await fetch('/validate-rule', {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   // Send the raw JSON rule (e.g., ["GT",5,3]) without wrapping in an object
  //   body: rule,
  // });

  // if (!response.ok) {
  //   throw new Error(
  //     `Validation request failed: ${response.status} ${response.statusText}`,
  //   );
  // }

  // return await response.json();
  return { success: true };
};
