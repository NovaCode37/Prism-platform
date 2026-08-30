export type ScanType = 'domain' | 'ip' | 'email' | 'phone' | 'username';
export type ScanStatus = 'idle' | 'running' | 'completed' | 'failed';
export type ToolMode = 'metadata' | 'headers' | 'crypto' | 'qr' | 'mac' | 'subnet' | 'hash' | 'encoder' | 'jwt' | null;

/** Standard per-module result status (mirrors modules/module_status.py). */
export type ModuleStatus = 'ok' | 'skipped' | 'rate_limited' | 'error';
/** Live status shown on the progress badges while a scan runs. */
export type LiveModuleStatus = ModuleStatus | 'running';

/** Status fields attached by key-dependent modules. */
export interface ModuleStatusFields {
  status?: ModuleStatus;
  status_reason?: string;
}

export interface ScanMeta {
  id: string;
  target: string;
  scan_type: ScanType;
  status: ScanStatus;
  modules: string[];
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

export interface VirusTotalData extends ModuleStatusFields {
  malicious?: number;
  suspicious?: number;
  harmless?: number;
  undetected?: number;
  country?: string;
  as_owner?: string;
  error?: string;
}

export interface AbuseIPDBData extends ModuleStatusFields {
  abuse_score?: number;
  total_reports?: number;
  isp?: string;
  usage_type?: string;
  is_tor?: boolean;
  error?: string;
}

export interface ShodanData extends ModuleStatusFields {
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

export interface TelegramData extends ModuleStatusFields {
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

export interface EmailRepData {
  email?: string;
  reputation?: string;
  suspicious?: boolean;
  valid_mx?: boolean;
  deliverable?: boolean | null;
  spoofable?: boolean;
  disposable?: boolean;
  free_provider?: boolean;
  spf?: boolean;
  dmarc?: boolean;
  domain_reputation?: string;
  mx_records?: string[];
  error?: string;
}

export interface SmtpData {
  email?: string;
  exists?: boolean | null;
  smtp_connect?: boolean;
  catch_all?: boolean;
  disposable?: boolean;
  details?: string[];
  error?: string;
}

export interface BreachData extends ModuleStatusFields {
  found?: boolean;
  total?: number;
  breaches?: (string | { name?: string; title?: string })[];
  error?: string;
}

export interface GravatarAccount {
  name?: string;
  display?: string;
  url?: string;
}

export interface HudsonRockData extends ModuleStatusFields {
  target?: string;
  target_type?: 'domain' | 'email' | 'username';
  total_compromised?: number | null;
  employees?: number | null;
  users?: number | null;
  third_parties?: number | null;
  employee_urls?: { url: string; occurrence?: number }[];
  stealer_families?: Record<string, number>;
  employee_password_stats?: Record<string, number | null>;
  user_password_stats?: Record<string, number | null>;
  stealers_found?: number | null;
  compromised?: boolean;
  corporate_services?: number | null;
  user_services?: number | null;
  error?: string;
}

export interface GravatarData extends ModuleStatusFields {
  avatar_url?: string;
  display_name?: string;
  accounts?: GravatarAccount[];
  error?: string;
}

export interface BlackbirdFailure extends ModuleStatusFields {
  error?: string;
}

export interface ScanResults {
  whois?: WhoisData;
  dns?: DnsRecord;
  geoip?: GeoipData;
  cert_transparency?: CertTransparencyData;
  blackbird?: BlackbirdResult[] | BlackbirdFailure;
  virustotal?: VirusTotalData;
  abuseipdb?: AbuseIPDBData;
  shodan?: ShodanData;
  wayback?: WaybackData;
  opsec?: OpsecScore;
  phone?: PhoneData;
  telegram?: TelegramData;
  emailrep?: EmailRepData;
  smtp?: SmtpData;
  breaches?: BreachData;
  gravatar?: GravatarData;
  hudsonrock?: HudsonRockData;
  website?: Record<string, unknown>;
  dorks?: string[];
  censys?: CensysData;
  onion?: OnionData;
  github?: GitHubData;
  report_path?: string;
  map_data?: unknown;
  graph?: unknown;
}

export interface GitHubData extends ModuleStatusFields {
  username?: string;
  profile?: {
    name?: string | null;
    bio?: string | null;
    company?: string | null;
    location?: string | null;
    blog?: string | null;
    twitter?: string | null;
    email?: string | null;
    type?: string | null;
    followers?: number;
    following?: number;
    public_repos?: number;
    created_at?: string | null;
    avatar_url?: string | null;
    html_url?: string | null;
  } | null;
  repo_count?: number;
  total_stars?: number;
  top_languages?: { language: string; count: number }[];
  emails?: string[];
  error?: string | null;
}

export interface CensysData extends ModuleStatusFields {
  error?: string | null;
  ip?: string;
  domain?: string;
  asn?: number;
  as_name?: string;
  country?: string;
  city?: string;
  open_ports?: number[];
  services?: { port: number; service?: string; transport?: string; software?: string | null }[];
  subdomains?: string[];
  certificates?: { fingerprint?: string; issuer?: string; names?: string[] }[];
  total?: number;
}

export interface OnionData {
  error?: string | null;
  target?: string;
  total_found?: number;
  results?: { source?: string; url: string; title?: string | null; description?: string | null }[];
  sources?: { ahmia?: number; darksearch?: number };
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

export interface MacResult {
  mac?: string;
  vendor?: string | null;
  error?: string;
}

export interface WatchlistAlert {
  at: number;
  added: string[];
  removed: string[];
  added_count: number;
  removed_count: number;
}

export interface Watchlist {
  id: string;
  target: string;
  scan_type: ScanType;
  modules: string[];
  interval_hours: number;
  webhook_url?: string | null;
  created_at: number;
  last_run: number | null;
  next_run: number;
  last_status: string;
  run_count: number;
  alerts: WatchlistAlert[];
  paused: boolean;
}

export interface JwtResult {
  header?: Record<string, unknown>;
  payload?: Record<string, unknown>;
  exp?: string | null;
  iat?: string | null;
  nbf?: string | null;
  error?: string;
}

export interface UsageData {
  principal: string;
  used: number;
  limit: number | null;
  remaining: number | null;
  resets_at: number;
  window_seconds: number;
}