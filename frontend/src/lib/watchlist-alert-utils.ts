const WATCHLIST_CHANGE_LABELS: Record<string, string> = {
  'shodan.open_ports[]': 'New open port',
  'cert_transparency.subdomains[]': 'New subdomain',
  'breaches.breaches[].name': 'New breach found',
  'breaches.breaches[].title': 'New breach found'
}

export function formatWatchlistChange(rawFingerprintPath: string): string {
  const [path, value = ''] = rawFingerprintPath.split('=');
  const label = WATCHLIST_CHANGE_LABELS[path];

  if (!label) {
    return rawFingerprintPath;
  }

  return value ? `${label}: ${value}` : label;
}
