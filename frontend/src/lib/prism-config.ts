export type PrismRuntimeConfig = {
  apiUrl?: string;
  apiKey?: string;
  basePath?: string;
  demoMode?: boolean;
};

declare global {
  interface Window {
    __PRISM_CONFIG__?: PrismRuntimeConfig;
  }
}

function hasOwnConfigValue(config: PrismRuntimeConfig, key: keyof PrismRuntimeConfig): boolean {
  return Object.prototype.hasOwnProperty.call(config, key);
}

export function readPrismRuntimeConfig(): PrismRuntimeConfig {
  if (typeof window === 'undefined') return {};
  return window.__PRISM_CONFIG__ || {};
}

export function getPrismApiUrl(
  config: PrismRuntimeConfig = readPrismRuntimeConfig(),
  buildValue = process.env.NEXT_PUBLIC_API_URL || '',
): string {
  return hasOwnConfigValue(config, 'apiUrl') ? config.apiUrl || '' : buildValue;
}

export function getPrismApiKey(
  config: PrismRuntimeConfig = readPrismRuntimeConfig(),
  buildValue = process.env.NEXT_PUBLIC_API_KEY || '',
): string {
  return hasOwnConfigValue(config, 'apiKey') ? config.apiKey || '' : buildValue;
}

export function getPrismBasePath(
  config: PrismRuntimeConfig = readPrismRuntimeConfig(),
  buildValue = process.env.NEXT_PUBLIC_BASE_PATH || '',
): string {
  return hasOwnConfigValue(config, 'basePath') ? config.basePath || '' : buildValue;
}

export function getPrismDemoMode(
  config: PrismRuntimeConfig = readPrismRuntimeConfig(),
  buildValue = process.env.NEXT_PUBLIC_DEMO_MODE || '',
): boolean {
  if (hasOwnConfigValue(config, 'demoMode')) return config.demoMode === true;
  return ['1', 'true', 'yes', 'on'].includes(buildValue.trim().toLowerCase());
}
