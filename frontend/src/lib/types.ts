export type ScanType = 'domain' | 'ip' | 'email' | 'phone' | 'username';
export type ScanStatus = 'idle' | 'running' | 'completed' | 'failed';
export type ToolMode = 'metadata' | 'headers' | 'crypto' | 'qr' | null;

export interface ScanMeta {
  id: string;
  target: string;
  scan_type: ScanType;
  status: ScanStatus;
  started_at?: string;
  completed_at?: string;
}

export interface OpsecCategory {
  score: number;
  max: number;
  percent: number;
  findings: OpsecFinding[];
}

export interface OpsecFinding {
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  message: string;
  deduction: number;
  category: string;
}

export interface OpsecScore {
  score: number;
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'MINIMAL';
  categories: Record<string, OpsecCategory>;
  all_findings: OpsecFinding[];
}

export interface DnsRecord {
  records: Record<string, unknown[]>;
  error?: string;
}

export interface WhoisData {
  registrar?: string;
  org?: string;
  country?: string;
  creation_date?: string;
  expiration_date?: string;
  name_servers?: string[];
  emails?: string[];
  error?: string;
}

export interface GeoipData {
  ip?: string;
  city?: string;
  region?: string;
  country?: string;
  country_name?: string;
  loc?: string;
  org?: string;
  timezone?: string;
  error?: string;
}

export interface CertTransparencyData {
  subdomains?: string[];
  total_certs?: number;
  error?: string;
}

export interface BlackbirdResult {
  site: string;
  status: 'found' | 'not_found';
  url?: string;
  response_time?: number;
}

export interface VirusTotalData {
  malicious?: number;
  suspicious?: number;
  harmless?: number;
  undetected?: number;
  country?: string;
  as_owner?: string;
  error?: string;
}

export interface AbuseIPDBData {
  abuse_score?: number;
  total_reports?: number;
  isp?: string;
  usage_type?: string;
  is_tor?: boolean;
  error?: string;
}

export interface ShodanData {
  open_ports?: number[];
  vulns?: string[];
  services?: { port: number; transport: string; product?: string; version?: string }[];
  error?: string;
}

export interface WaybackData {
  total_snapshots?: number;
  first_snapshot?: string;
  last_snapshot?: string;
  interesting?: string[];
  snapshots?: { timestamp: string; date: string; wayback_url: string; status: string; mime: string; size: number }[];
  error?: string;
}

export interface PhoneData {
  valid?: boolean;
  country_name?: string;
  country_code?: string;
  carrier?: string;
  line_type?: string;
  region?: string;
  timezones?: string[];
  reverse?: { name?: string; address?: string; source?: string };
  error?: string;
}

export interface TelegramData {
  username?: string;
  found?: boolean;
  name?: string;
  bio?: string;
  followers?: number;
  photo_url?: string;
  is_verified?: boolean;
  type?: string;
  error?: string;
}

export interface ScanResults {
  whois?: WhoisData;
  dns?: DnsRecord;
  geoip?: GeoipData;
  cert_transparency?: CertTransparencyData;
  blackbird?: BlackbirdResult[];
  virustotal?: VirusTotalData;
  abuseipdb?: AbuseIPDBData;
  shodan?: ShodanData;
  wayback?: WaybackData;
  opsec?: OpsecScore;
  phone?: PhoneData;
  telegram?: TelegramData;
  website?: Record<string, unknown>;
  dorks?: string[];
  report_path?: string;
  map_data?: unknown;
  graph?: unknown;
}

export interface UrlScanResult {
  url?: string;
  status?: string;
  malicious?: number;
  suspicious?: number;
  harmless?: number;
  undetected?: number;
  categories?: Record<string, string>;
  permalink?: string;
  error?: string;
}

export interface CryptoResult {
  address?: string;
  type?: string;
  balance?: string;
  balance_usd?: string;
  total_received?: string;
  total_sent?: string;
  tx_count?: number;
  explorer_url?: string;
  error?: string;
}

export interface DarkWebResult {
  query?: string;
  results?: { title?: string; url?: string; description?: string; onion?: string }[];
  source?: string;
  error?: string;
}

export interface QrResult {
  decoded?: string;
  type?: string;
  is_url?: boolean;
  error?: string;
}

export interface HeaderAnalysisResult {
  from?: string;
  to?: string;
  subject?: string;
  date?: string;
  reply_to?: string;
  x_mailer?: string;
  spf?: string;
  dkim?: string;
  dmarc?: string;
  origin_ip?: string;
  origin_geo?: { city?: string; region?: string; country?: string; org?: string };
  origin_rdns?: string;
  hops?: { from_host?: string; by_host?: string; ip?: string; date?: string; geo?: { country?: string }; rdns?: string }[];
  spoofing_flags?: { type: string; detail: string }[];
  error?: string;
}

export interface MetaResult {
  filename?: string;
  file_type?: string;
  file_size?: number;
  dimensions?: { width: number; height: number } | null;
  author?: string | null;
  software?: string | null;
  timestamps?: Record<string, string>;
  camera?: Record<string, string>;
  basic?: Record<string, unknown>;
  exif?: Record<string, unknown>;
  gps?: { lat: number; lng: number; altitude?: number; gps_time?: string } | null;
  pdf_meta?: Record<string, unknown>;
  docx_meta?: Record<string, unknown>;
  error?: string;
}
