'use client';

import { useState, useMemo } from 'react';
import {
  Download,
  FileText,
  Share2,
  ChevronDown,
  ChevronRight,
  Check,
  X,
  AlertTriangle,
  Info,
  Wifi,
  Shield,
  Globe,
  Database,
  Clock,
  Mail,
  User,
  Server,
  Network,
  MapPin,
  File,
  Link2,
  Code,
  Eye,
  EyeOff,
  Sparkles,
  Loader2,
} from 'lucide-react';
import { useTranslations } from '@/lib/i18n';
import { getPrismApiUrl, getPrismApiKey, buildApiUrl } from '@/lib/url-utils';
import { MODULE_MAP } from '@/components/Sidebar';

interface ScanResultsProps {
  results: Record<string, any>;
  target: string;
  scanType: string;
  scanId: string;
}

const SEVERITY_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'];

export function ScanResults({ results, target, scanType, scanId }: ScanResultsProps) {
  const { t } = useTranslations();
  const [expandedModules, setExpandedModules] = useState<Set<string>>(new Set());
  const [showRaw, setShowRaw] = useState(false);

  const toggleModule = (module: string) => {
    setExpandedModules((prev) => {
      const next = new Set(prev);
      if (next.has(module)) {
        next.delete(module);
      } else {
        next.add(module);
      }
      return next;
    });
  };

  // Extract findings
  const findings = useMemo(() => {
    const items: Array<{ severity: string; message: string; source: string }> = [];

    // Check each module for findings
    for (const [key, value] of Object.entries(results)) {
      if (!value || typeof value !== 'object') continue;

      // Shodan vulns
      if (key === 'shodan' && value.vulns) {
        for (const vuln of value.vulns) {
          items.push({
            severity: value.vuln_severity?.[vuln] || 'MEDIUM',
            message: `${vuln}: ${value.vuln_summary?.[vuln] || 'Vulnerability found'}`,
            source: 'Shodan',
          });
        }
      }

      // VirusTotal detections
      if (key === 'virustotal' && value.malicious > 0) {
        items.push({
          severity: value.malicious > 3 ? 'HIGH' : 'MEDIUM',
          message: `${value.malicious} malicious detections out of ${value.total} scanners`,
          source: 'VirusTotal',
        });
      }

      // Breach findings
      if (key === 'breach' && value.found) {
        const total = value.total || value.breaches?.length || 0;
        items.push({
          severity: total > 0 ? 'HIGH' : 'INFO',
          message: `${total} breaches found${value.latest_breach ? ` (latest: ${value.latest_breach})` : ''}`,
          source: 'Breach Check',
        });
      }

      // OPSEC score
      if (key === 'opsec' && value.score !== undefined) {
        const risk = value.risk_level || 'UNKNOWN';
        const severity = risk === 'CRITICAL' ? 'CRITICAL' : 
                        risk === 'HIGH' ? 'HIGH' :
                        risk === 'MEDIUM' ? 'MEDIUM' : 'INFO';
        items.push({
          severity,
          message: `OPSEC Score: ${value.score}/100 (${risk})`,
          source: 'OPSEC',
        });
      }

      // GeoIP
      if (key === 'geoip' && value.country) {
        items.push({
          severity: 'INFO',
          message: `Located in ${value.country}${value.city ? `, ${value.city}` : ''}`,
          source: 'GeoIP',
        });
      }

      // Certificate Transparency
      if (key === 'cert_transparency' && value.subdomains?.length > 0) {
        items.push({
          severity: 'INFO',
          message: `${value.subdomains.length} subdomains found via CT logs`,
          source: 'CT Logs',
        });
      }

      // WHOIS
      if (key === 'whois' && value.registrar) {
        items.push({
          severity: 'INFO',
          message: `Registered with ${value.registrar}${value.creation_date ? `, created ${value.creation_date}` : ''}`,
          source: 'WHOIS',
        });
      }

      // RDAP
      if (key === 'rdap' && value.status === 'registered') {
        let message = `Domain is registered`;
        if (value.registrar) {
          message += ` with ${value.registrar}`;
        }
        if (value.created) {
          message += `, created ${value.created}`;
        }
        if (value.expires) {
          message += `, expires ${value.expires}`;
        }
        items.push({
          severity: 'INFO',
          message,
          source: 'RDAP',
        });
      }
    }

    // Sort by severity
    items.sort((a, b) => {
      const aIdx = SEVERITY_ORDER.indexOf(a.severity);
      const bIdx = SEVERITY_ORDER.indexOf(b.severity);
      return aIdx - bIdx;
    });

    return items;
  }, [results]);

  // OPSEC score
  const opsec = results.opsec || {};
  const score = opsec.score;
  const riskLevel = opsec.risk_level || 'UNKNOWN';

  // Get modules that ran
  const modules = useMemo(() => {
    return Object.entries(results)
      .filter(([key, value]) => {
        return key !== 'opsec' && key !== 'graph' && value !== null && value !== undefined;
      })
      .map(([key, value]) => ({ key, value }));
  }, [results]);

  // Download report
  const downloadReport = async (format: string) => {
    const apiBase = getPrismApiUrl();
    const apiKey = getPrismApiKey();
    const url = buildApiUrl(`/scan/${scanId}/report.${format}`, apiBase);
    const response = await fetch(url, {
      headers: apiKey ? { 'X-API-Key': apiKey } : {},
    });
    if (!response.ok) throw new Error('Failed to download report');
    const blob = await response.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${target}_report.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  };

  return (
    <div className="p-4 space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-1">{target}</h1>
          <p className="text-sm text-text-3">
            {t('scan.type')}: {scanType.toUpperCase()} · {t('scan.completed')}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => downloadReport('html')}
            className="btn-secondary text-sm flex items-center gap-1"
          >
            <FileText size={16} />
            HTML
          </button>
          <button
            onClick={() => downloadReport('pdf')}
            className="btn-secondary text-sm flex items-center gap-1"
          >
            <FileText size={16} />
            PDF
          </button>
          <button
            onClick={() => downloadReport('json')}
            className="btn-secondary text-sm flex items-center gap-1"
          >
            <Code size={16} />
            JSON
          </button>
          <button
            onClick={() => setShowRaw(!showRaw)}
            className="btn-secondary text-sm flex items-center gap-1"
          >
            {showRaw ? <EyeOff size={16} /> : <Eye size={16} />}
            {showRaw ? 'Hide Raw' : 'Raw'}
          </button>
        </div>
      </div>

      {/* OPSEC Score */}
      {score !== undefined && (
        <div className="card">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Shield size={24} className={`
                ${score >= 70 ? 'text-green' : score >= 40 ? 'text-yellow' : 'text-red'}
              `} />
              <div>
                <div className="text-sm font-semibold text-text-1">{t('opsec.title')}</div>
                <div className="text-sm text-text-3">{t('opsec.risk')}: {riskLevel}</div>
              </div>
            </div>
            <div className="text-right">
              <div className={`
                text-3xl font-bold
                ${score >= 70 ? 'text-green' : score >= 40 ? 'text-yellow' : 'text-red'}
              `}>
                {score}/100
              </div>
              <div className="text-xs text-text-3">{t('opsec.label')}</div>
            </div>
          </div>
          <div className="mt-3 w-full h-2 bg-surface-2 rounded-full overflow-hidden">
            <div
              className="h-full transition-all duration-500"
              style={{
                width: `${score}%`,
                background: `linear-gradient(90deg, 
                  ${score <= 30 ? '#ef4444' : score <= 60 ? '#eab308' : '#22c55e'}
                )`,
              }}
            />
          </div>
        </div>
      )}

      {/* Findings */}
      {findings.length > 0 && (
        <div className="card">
          <div className="card-head">
            <AlertTriangle size={16} />
            {t('findings.title')}
          </div>
          <div className="p-3 space-y-1.5">
            {findings.map((finding, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <span className={`
                  inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold whitespace-nowrap
                  ${finding.severity === 'CRITICAL' || finding.severity === 'HIGH' ? 'bg-red/10 text-red' :
                    finding.severity === 'MEDIUM' ? 'bg-yellow/10 text-yellow' :
                    'bg-blue/10 text-blue'}
                `}>
                  {finding.severity}
                </span>
                <span className="text-text-2">{finding.message}</span>
                <span className="text-xs text-text-3 ml-auto">[{finding.source}]</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Module Results */}
      <div className="space-y-2">
        {modules.map(({ key, value }) => {
          const moduleInfo = MODULE_MAP[key];
          const label = moduleInfo?.label || key;
          const icon = moduleInfo?.icon || '📦';
          const isExpanded = expandedModules.has(key);
          const hasData = value && typeof value === 'object' && Object.keys(value).length > 0;
          const isError = value?.error;
          const status = value?.status || (isError ? 'error' : 'ok');

          if (!hasData && !isError) return null;

          return (
            <div key={key} className="card overflow-hidden">
              <button
                onClick={() => toggleModule(key)}
                className="w-full flex items-center gap-2 p-3 hover:bg-surface-2/50 transition-colors"
              >
                <span className="text-base">{icon}</span>
                <span className="font-medium text-text-1">{label}</span>
                <span className={`
                  text-xs px-2 py-0.5 rounded ml-auto
                  ${status === 'ok' ? 'bg-green/10 text-green' :
                    status === 'skipped' ? 'bg-text-3/10 text-text-3' :
                    status === 'rate_limited' ? 'bg-yellow/10 text-yellow' :
                    'bg-red/10 text-red'}
                `}>
                  {status}
                </span>
                {isExpanded ? <ChevronDown size={16} className="text-text-3" /> : <ChevronRight size={16} className="text-text-3" />}
              </button>

              {isExpanded && (
                <div className="p-3 pt-0 border-t border-border-1">
                  {isError ? (
                    <div className="text-red text-sm">{value.error}</div>
                  ) : (
                    <ModuleData data={value} />
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Raw JSON */}
      {showRaw && (
        <div className="card">
          <div className="card-head">
            <Code size={16} />
            Raw Data
          </div>
          <pre className="p-3 bg-surface-2 rounded text-xs font-mono overflow-auto max-h-96 text-text-2">
            {JSON.stringify(results, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

function ModuleData({ data }: { data: any }) {
  if (!data || typeof data !== 'object') {
    return <div className="text-text-3 text-sm">{String(data)}</div>;
  }

  // Skip internal fields
  const skipFields = ['status', 'status_reason', 'error'];

  const entries = Object.entries(data).filter(([k]) => !skipFields.includes(k));

  if (entries.length === 0) {
    return <div className="text-text-3 text-sm">No data</div>;
  }

  return (
    <div className="space-y-2 text-sm">
      {entries.map(([key, value]) => {
        if (value === null || value === undefined) return null;
        if (typeof value === 'string' && !value) return null;

        let display: React.ReactNode;

        if (Array.isArray(value)) {
          if (value.length === 0) {
            display = <span className="text-text-3">Empty</span>;
          } else if (typeof value[0] === 'string') {
            display = (
              <div className="flex flex-wrap gap-1">
                {value.map((item, i) => (
                  <span key={i} className="tag">{item}</span>
                ))}
              </div>
            );
          } else {
            display = (
              <div className="space-y-1">
                {value.map((item, i) => (
                  <div key={i} className="p-2 bg-surface-2 rounded text-xs">
                    <ModuleData data={item} />
                  </div>
                ))}
              </div>
            );
          }
        } else if (typeof value === 'object') {
          display = <ModuleData data={value} />;
        } else if (typeof value === 'boolean') {
          display = value ? <Check size={14} className="text-green" /> : <X size={14} className="text-red" />;
        } else {
          display = <span className="font-mono text-text-1">{String(value)}</span>;
        }

        return (
          <div key={key} className="flex items-start gap-2 border-b border-border-1/50 py-1.5 last:border-0">
            <span className="text-text-3 text-xs font-mono whitespace-nowrap min-w-[100px]">{key}</span>
            <div className="flex-1 min-w-0">{display}</div>
          </div>
        );
      })}
    </div>
  );
}