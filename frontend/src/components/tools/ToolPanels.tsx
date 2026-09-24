'use client';
import { useState, useCallback } from 'react';
import { Loader2, ArrowLeft, ExternalLink, Upload, XCircle, FileUp } from 'lucide-react';
import { useTranslations } from '@/lib/i18n';
import { runEncoder, type EncoderMode } from '@/lib/encoder-utils';
import * as api from '@/lib/api';
import type { ToolMode, CryptoResult, QrResult, HeaderAnalysisResult, MetaResult, MacResult } from '@/lib/types';

function Card({ title, children, className }: { title?: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`card mb-3 animate-fade-in ${className ?? ''}`}>
      {title && <div className="card-head">{title}</div>}
      <div className="p-4">{children}</div>
    </div>
  );
}

function ErrorCard({ label, message }: { label: string; message: string }) {
  return (
    <div className="card mb-3 border-red/20 animate-fade-in">
      <div className="p-4 flex gap-3 items-start">
        <div className="w-7 h-7 rounded-md bg-red/10 flex items-center justify-center shrink-0 mt-0.5">
          <XCircle size={14} className="text-red" />
        </div>
        <div>
          <div className="text-[12px] font-semibold text-red mb-1">{label}</div>
          <div className="text-[12px] text-text-3 leading-relaxed">{message}</div>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string | number | null }) {
  if (!value && value !== 0) return null;
  return (
    <div className="flex gap-3 text-[12px] py-1 border-b border-border-1 last:border-0">
      <span className="text-text-3 w-36 shrink-0 truncate" title={label}>{label}</span>
      <span className="text-text-1 font-mono break-all">{String(value)}</span>
    </div>
  );
}
function Input({ value, onChange, placeholder, onEnter }: { value: string; onChange: (v: string) => void; placeholder?: string; onEnter?: () => void }) {
  return (
    <input className="input-field flex-1" value={value} onChange={e => onChange(e.target.value)}
      placeholder={placeholder} onKeyDown={e => e.key === 'Enter' && onEnter?.()} />
  );
}
function RunBtn({ loading, label, onClick, disabled }: { loading: boolean; label: string; onClick: () => void; disabled?: boolean }) {
  return (
    <button className="btn-primary shrink-0 px-5" onClick={onClick} disabled={loading || disabled}>
      {loading && <Loader2 size={13} className="spin" />}
      {loading ? 'Running...' : label}
    </button>
  );
}

function CryptoPanel() {
  const { t } = useTranslations();
  const [addr, setAddr] = useState('');
  const [result, setResult] = useState<CryptoResult | null>(null);
  const [loading, setLoading] = useState(false);
  const run = async () => {
    if (!addr.trim()) return;
    setLoading(true); setResult(null);
    try {
      setResult(await api.lookupCrypto(addr.trim()));
    } catch (e) {
      setResult({ address: addr, error: e instanceof Error ? e.message : 'Request failed' } as import('@/lib/types').CryptoResult);
    }
    setLoading(false);
  };
  return (
    <div>
      <Card title={t('toolPanels.crypto.title')}>
        <div className="flex gap-2 flex-wrap"><Input value={addr} onChange={setAddr} placeholder={t('toolPanels.crypto.placeholder')} onEnter={run} /><RunBtn loading={loading} label={t('toolPanels.crypto.lookup')} onClick={run} /></div>
      </Card>
      {result && (
        result.error && !result.balance ? (
          <ErrorCard label={t('toolPanels.error')} message={result.error} />
        ) : (
          <Card>
            <Row label={t('toolPanels.crypto.type')} value={result.type} />
            <Row label={t('toolPanels.crypto.address')} value={result.address} />
            <Row label={t('toolPanels.crypto.balance')} value={result.balance} />
            <Row label={t('toolPanels.crypto.usd')} value={result.balance_usd} />
            <Row label={t('toolPanels.crypto.totalReceived')} value={result.total_received} />
            <Row label={t('toolPanels.crypto.totalSent')} value={result.total_sent} />
            <Row label={t('toolPanels.crypto.transactions')} value={result.tx_count} />
            {result.explorer_url && (
              <div className="pt-3">
                <a href={result.explorer_url} target="_blank" rel="noreferrer" className="btn-ghost h-8 px-3 text-[11px] inline-flex items-center gap-1">
                  <ExternalLink size={11} /> {t('toolPanels.crypto.openExplorer')}
                </a>
              </div>
            )}
          </Card>
        )
      )}
    </div>
  );
}

function DropZone({ accept, file, onChange, hint }: { accept: string; file: File | null; onChange: (f: File | null) => void; hint?: string }) {
  const { t } = useTranslations();
  const [drag, setDrag] = useState(false);
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDrag(false);
    const f = e.dataTransfer.files?.[0];
    if (f) onChange(f);
  }, [onChange]);
  return (
    <label
      className={`relative flex flex-col items-center justify-center gap-2 w-full rounded-lg border-2 border-dashed cursor-pointer transition-all duration-200 py-8 px-4 text-center
        ${ drag ? 'border-blue bg-blue/5' : file ? 'border-blue/40 bg-blue/5' : 'border-border-2 hover:border-border-3 bg-surface-1 hover:bg-surface-2' }`}
      onDragOver={e => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={onDrop}
    >
      <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors ${ file ? 'bg-blue/15' : 'bg-surface-3' }`}>
        { file ? <FileUp size={18} className="text-blue" /> : <Upload size={18} className="text-text-3" /> }
      </div>
      { file ? (
        <>
          <div className="text-[12px] font-semibold text-text-1 truncate max-w-full px-4">{file.name}</div>
          <div className="text-[10px] text-text-3">{(file.size / 1024).toFixed(1)} KB · {t('toolPanels.qr.clickToChange')}</div>
        </>
      ) : (
        <>
          <div className="text-[12px] font-semibold text-text-2">{t('toolPanels.qr.dropFile')} <span className="text-blue">{t('toolPanels.qr.browse')}</span></div>
          { hint && <div className="text-[10px] text-text-3">{hint}</div> }
        </>
      )}
      <input type="file" accept={accept} className="hidden" onChange={e => onChange(e.target.files?.[0] ?? null)} />
    </label>
  );
}
function QrPanel() {
  const { t } = useTranslations();
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<QrResult | null>(null);
  const [loading, setLoading] = useState(false);
  const run = async () => {
    if (!file) return;
    setLoading(true); setResult(null);
    try {
      setResult(await api.decodeQr(file));
    } catch (e) {
      setResult({ error: e instanceof Error ? e.message : 'Request failed' } as import('@/lib/types').QrResult);
    }
    setLoading(false);
  };
  return (
    <div>
      <Card title={t('toolPanels.qr.title')}>
        <div className="flex flex-col gap-3">
          <DropZone accept="image/*" file={file} onChange={setFile} hint={t('toolPanels.qr.hint')} />
          <RunBtn loading={loading} label={t('toolPanels.qr.decode')} onClick={run} disabled={!file} />
        </div>
      </Card>
      {result && (
        <Card>
          {result.error ? (
            <ErrorCard label={t('toolPanels.error')} message={result.error} />
          ) : (
            <div>
              <Row label={t('toolPanels.qr.type')} value={result.type} />
              <div className="flex gap-3 text-[12px] py-1">
                <span className="text-text-3 w-36 shrink-0">{t('toolPanels.qr.content')}</span>
                {result.is_url ? (
                  <a href={result.decoded} target="_blank" rel="noreferrer" className="text-blue font-mono text-[11px] break-all hover:underline">{result.decoded}</a>
                ) : (
                  <span className="font-mono text-[11px] break-all">{result.decoded}</span>
                )}
              </div>
              {result.is_url && result.decoded && (
                <a href={result.decoded} target="_blank" rel="noreferrer" className="btn-ghost h-8 px-3 text-[11px] mt-3 inline-flex items-center gap-1">
                  <ExternalLink size={11} /> {t('toolPanels.qr.openUrl')}
                </a>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

function MetadataPanel() {
  const { t } = useTranslations();
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<MetaResult | null>(null);
  const [loading, setLoading] = useState(false);
  const run = async () => {
    if (!file) return;
    setLoading(true); setResult(null);
    try {
      setResult(await api.extractMetadata(file));
    } catch (e) {
      setResult({ error: e instanceof Error ? e.message : 'Request failed' } as import('@/lib/types').MetaResult);
    }
    setLoading(false);
  };
  return (
    <div>
      <Card title={t('toolPanels.metadata.title')}>
        <div className="flex flex-col gap-3">
          <DropZone accept=".jpg,.jpeg,.png,.tiff,.heic,.webp,.pdf,.docx" file={file} onChange={setFile} hint="JPG, PNG, TIFF, HEIC, PDF, DOCX" />
          <RunBtn loading={loading} label={t('toolPanels.metadata.extract')} onClick={run} disabled={!file} />
        </div>
      </Card>
      {result && (
        <div>
          {result.error ? (
            <ErrorCard label={t('toolPanels.error')} message={result.error} />
          ) : (
            <>
              <Card title={t('toolPanels.metadata.fileInfo')}>
                <Row label={t('toolPanels.metadata.filename')} value={result.filename} />
                <Row label={t('toolPanels.metadata.fileType')} value={result.file_type} />
                <Row label={t('toolPanels.metadata.size')} value={result.file_size ? `${(result.file_size / 1024).toFixed(1)} KB` : undefined} />
                <Row label={t('toolPanels.metadata.dimensions')} value={result.dimensions ? `${result.dimensions.width} × ${result.dimensions.height} px` : undefined} />
                <Row label={t('toolPanels.metadata.author')} value={result.author} />
                <Row label={t('toolPanels.metadata.software')} value={result.software} />
              </Card>
              {result.timestamps && Object.keys(result.timestamps).length > 0 && (
                <Card title={t('toolPanels.metadata.timestamps')}>
                  {Object.entries(result.timestamps).map(([k, v]) => (
                    <Row key={k} label={k} value={v} />
                  ))}
                </Card>
              )}
              {result.camera && Object.keys(result.camera).length > 0 && (
                <Card title={t('toolPanels.metadata.camera')}>
                  {Object.entries(result.camera).map(([k, v]) => (
                    <Row key={k} label={k} value={v} />
                  ))}
                </Card>
              )}
              {result.gps && (
                <Card title={t('toolPanels.metadata.gpsLocation')}>
                  <Row label={t('toolPanels.metadata.latitude')} value={result.gps.lat} />
                  <Row label={t('toolPanels.metadata.longitude')} value={result.gps.lng} />
                  {result.gps.altitude && <Row label={t('toolPanels.metadata.altitude')} value={`${Math.round(result.gps.altitude)}m`} />}
                  <div className="mt-3">
                    <a href={`https://www.google.com/maps?q=${result.gps.lat},${result.gps.lng}`} target="_blank" rel="noreferrer" className="btn-ghost h-8 px-3 text-[11px] inline-flex items-center gap-1">
                      <ExternalLink size={11} /> {t('toolPanels.metadata.openInMaps')}
                    </a>
                  </div>
                </Card>
              )}
              {result.exif && Object.keys(result.exif).length > 0 && (
                <Card title={t('toolPanels.metadata.exifData')}>
                  {Object.entries(result.exif).slice(0, 30).map(([k, v]) => (
                    <Row key={k} label={k} value={String(v)} />
                  ))}
                </Card>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function MacPanel() {
  const { t } = useTranslations();
  const [addr, setAddr] = useState('');
  const [result, setResult] = useState<MacResult | null>(null);
  const [loading, setLoading] = useState(false);
  const run = async () => {
    if (!addr.trim()) return;
    setLoading(true); setResult(null);
    try {
      setResult(await api.lookupMac(addr.trim()));
    } catch (e) {
      setResult({ error: e instanceof Error ? e.message : 'Request failed' });
    }
    setLoading(false);
  };
  return (
    <div>
      <Card title={t('toolPanels.mac.title')}>
        <div className="flex gap-2 flex-wrap"><Input value={addr} onChange={setAddr} placeholder={t('toolPanels.mac.placeholder')} onEnter={run} /><RunBtn loading={loading} label={t('toolPanels.mac.lookup')} onClick={run} disabled={!addr.trim()} /></div>
      </Card>
      {result && (
        result.error ? (
          <ErrorCard label={t('toolPanels.error')} message={result.error} />
        ) : (
          <Card>
            <Row label={t('toolPanels.mac.macAddress')} value={result.mac} />
            <Row label={t('toolPanels.mac.vendor')} value={result.vendor || t('toolPanels.mac.notFound')} />
          </Card>
        )
      )}
    </div>
  );
}

function HashPanel() {
  const { t } = useTranslations();
  const [hash, setHash] = useState('');
  const [error, setError] = useState('');
  const [result, setResult] = useState<{ type: string; length: number } | null>(null);

  const identifyHash = (value: string) => {
    const trimmed = value.trim().toLowerCase();
    setHash(value);
    setError('');
    setResult(null);

    if (!trimmed) return;

    if (!/^[a-f0-9]*$/.test(trimmed)) {
      setError(t('toolPanels.hash.invalidHex'));
      return;
    }

    const len = trimmed.length;
    let type = 'Unknown';

    if (len === 32) type = 'MD5 / MD4 / NTLM';
    else if (len === 40) type = 'SHA-1 / LM';
    else if (len === 64) type = 'SHA-256 / BLAKE2b-256';
    else if (len === 128) type = 'SHA-512 / BLAKE2b-512';
    else {
      setError(t('toolPanels.hash.unsupportedLength'));
      return;
    }

    setResult({ type, length: len });
  };

  return (
    <div>
      <Card title={t('toolPanels.hash.title')}>
        <div className="flex flex-col gap-2">
          <textarea
            value={hash}
            onChange={e => identifyHash(e.target.value)}
            placeholder={t('toolPanels.hash.placeholder')}
            className="input-field font-mono text-[11px] resize-y leading-relaxed w-full"
            rows={6}
          />
          {error && <span className="text-[11px] text-red">{error}</span>}
        </div>
      </Card>
      {result && (
        <Card>
          <Row label={t('toolPanels.hash.detected')} value={result.type} />
          <Row label={t('toolPanels.hash.length')} value={result.length} />
        </Card>
      )}
    </div>
  );
}
function EncoderPanel() {
  const { t } = useTranslations();
  const [input, setInput] = useState('');
  const [output, setOutput] = useState('');
  const [error, setError] = useState('');
  const [mode, setMode] = useState<EncoderMode>('base64');

  const run = (op: 'encode' | 'decode') => {
    setError('');
    setOutput('');
    if (!input) return;
    try {
      setOutput(runEncoder(input, mode, op));
    } catch {
      setError(t('toolPanels.encoder.invalid'));
    }
  };

  return (
    <div>
      <Card title={t('toolPanels.encoder.title')}>
        <div className="flex gap-2 mb-3">
          {(['base64', 'url'] as const).map(m => (
            <button key={m} type="button" onClick={() => { setMode(m); setOutput(''); setError(''); }}
              className={`px-3 py-1 text-[11px] rounded border transition-colors ${mode === m ? 'border-blue/50 text-blue bg-blue/10' : 'border-border-2 text-text-3 hover:text-text-2'}`}>
              {m === 'base64' ? 'Base64' : 'URL'}
            </button>
          ))}
        </div>
        <textarea
          value={input}
          onChange={e => { setInput(e.target.value); setError(''); }}
          placeholder={t('toolPanels.encoder.placeholder')}
          className="input-field font-mono text-[11px] resize-y leading-relaxed w-full"
          rows={5}
        />
        <div className="flex gap-2 mt-2">
          <button type="button" onClick={() => run('encode')}
            className="flex-1 text-[11px] py-1.5 rounded border border-blue/40 text-blue bg-blue/10 hover:bg-blue/20 transition-colors">
            {t('toolPanels.encoder.encode')}
          </button>
          <button type="button" onClick={() => run('decode')}
            className="flex-1 text-[11px] py-1.5 rounded border border-border-2 text-text-3 hover:text-text-2 transition-colors">
            {t('toolPanels.encoder.decode')}
          </button>
        </div>
        {error && <span className="text-[11px] text-red mt-2 block">{error}</span>}
      </Card>
      {output && (
        <Card title={t('toolPanels.encoder.output')}>
          <textarea readOnly value={output} rows={5}
            className="input-field font-mono text-[11px] resize-y leading-relaxed w-full" />
        </Card>
      )}
    </div>
  );
}

function base64UrlDecode(str: string): string {
  const padded = str.replace(/-/g, '+').replace(/_/g, '/');
  const pad = padded.length % 4;
  const withPad = pad ? padded + '='.repeat(4 - pad) : padded;
  return decodeURIComponent(escape(atob(withPad)));
}

function formatTimestamp(value: unknown): string | null {
  if (typeof value !== 'number') return null;
  const date = new Date(value * 1000);
  if (isNaN(date.getTime())) return null;
  return date.toLocaleString();
}

function JwtPanel() {
  const { t } = useTranslations();
  const [token, setToken] = useState('');
  const [result, setResult] = useState<import('@/lib/types').JwtResult | null>(null);
  const [isExpired, setIsExpired] = useState(false);

  const run = () => {
    const trimmed = token.trim();
    if (!trimmed) return;
    const parts = trimmed.split('.');
    if (parts.length !== 3) {
      setResult({ error: t('toolPanels.jwt.invalid') });
      setIsExpired(false);
      return;
    }
    try {
      const header = JSON.parse(base64UrlDecode(parts[0]));
      const payload = JSON.parse(base64UrlDecode(parts[1]));
      setResult({
        header,
        payload,
        iat: formatTimestamp(payload.iat),
        exp: formatTimestamp(payload.exp),
        nbf: formatTimestamp(payload.nbf),
      });
      setIsExpired(typeof payload.exp === 'number' && payload.exp * 1000 < Date.now());
    } catch {
      setResult({ error: t('toolPanels.jwt.invalid') });
      setIsExpired(false);
    }
  };

  return (
    <div>
      <Card title={t('toolPanels.jwt.title')}>
        <textarea
          value={token}
          onChange={e => setToken(e.target.value)}
          placeholder={t('toolPanels.jwt.placeholder')}
          className="input-field font-mono text-[11px] resize-y leading-relaxed w-full mb-3"
          rows={4}
        />
        <RunBtn loading={false} label={t('toolPanels.jwt.decode')} onClick={run} disabled={!token.trim()} />
      </Card>
      {result && (
        result.error ? (
          <ErrorCard label={t('toolPanels.error')} message={result.error} />
        ) : (
          <div>
            {isExpired && (
              <div className="text-[11px] text-red mb-2 px-1">{t('toolPanels.jwt.expired')}</div>
            )}
            <Card title={t('toolPanels.jwt.header')}>
              <textarea readOnly value={JSON.stringify(result.header, null, 2)} rows={4}
                className="input-field font-mono text-[11px] resize-y leading-relaxed w-full" />
            </Card>
            <Card title={t('toolPanels.jwt.payload')}>
              <textarea readOnly value={JSON.stringify(result.payload, null, 2)} rows={8}
                className="input-field font-mono text-[11px] resize-y leading-relaxed w-full" />
            </Card>
            <Card>
              <Row label={t('toolPanels.jwt.issuedAt')} value={result.iat ?? undefined} />
              <Row label={t('toolPanels.jwt.expiresAt')} value={result.exp ?? undefined} />
              <Row label={t('toolPanels.jwt.notBefore')} value={result.nbf ?? undefined} />
            </Card>
            <div className="text-[10px] text-text-3 px-1">{t('toolPanels.jwt.noSignatureWarning')}</div>
          </div>
        )
      )}
    </div>
  );
}
function HeadersPanel() {
  const { t } = useTranslations();
  const [text, setText] = useState('');
  const [result, setResult] = useState<HeaderAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const run = async () => {
    if (!text.trim()) return;
    setLoading(true); setResult(null);
    try {
      setResult(await api.analyzeHeaders(text.trim()));
    } catch (e) {
      setResult({ error: e instanceof Error ? e.message : 'Request failed' } as import('@/lib/types').HeaderAnalysisResult);
    }
    setLoading(false);
  };
  return (
    <div>
      <Card title={t('toolPanels.headers.title')}>
        <textarea value={text} onChange={e => setText(e.target.value)} rows={10}
          placeholder={t('toolPanels.headers.placeholder')}
          className="input-field font-mono text-[11px] resize-y leading-relaxed w-full mb-3" />
        <RunBtn loading={loading} label={t('toolPanels.headers.analyse')} onClick={run} disabled={!text.trim()} />
      </Card>
      {result && !result.error && (
        <div>
          <Card title={t('toolPanels.headers.messageMetadata')}>
            <Row label={t('toolPanels.headers.from')} value={result.from} />
            <Row label={t('toolPanels.headers.to')} value={result.to} />
            <Row label={t('toolPanels.headers.subject')} value={result.subject} />
            <Row label={t('toolPanels.headers.date')} value={result.date} />
            <Row label={t('toolPanels.headers.replyTo')} value={result.reply_to} />
            <Row label={t('toolPanels.headers.xMailer')} value={result.x_mailer} />
          </Card>
          <Card title={t('toolPanels.headers.authentication')}>
            <Row label={t('toolPanels.headers.spf')} value={result.spf} />
            <Row label={t('toolPanels.headers.dkim')} value={result.dkim} />
            <Row label={t('toolPanels.headers.dmarc')} value={result.dmarc} />
          </Card>
          {result.origin_ip && (
            <Card title={t('toolPanels.headers.origin')}>
              <Row label="IP" value={result.origin_ip} />
              <Row label={t('toolPanels.headers.rdns')} value={result.origin_rdns} />
              {result.origin_geo && (
                <>
                  <Row label={t('toolPanels.headers.city')} value={result.origin_geo.city} />
                  <Row label={t('toolPanels.headers.country')} value={result.origin_geo.country} />
                  <Row label={t('toolPanels.headers.org')} value={result.origin_geo.org} />
                </>
              )}
            </Card>
          )}
          {result.spoofing_flags && result.spoofing_flags.length > 0 && (
            <Card title={t('toolPanels.headers.spoofingIndicators')}>
              {result.spoofing_flags.map((f, i) => (
                <div key={i} className="py-1.5 border-b border-border-1 last:border-0">
                  <span className="badge badge-high mr-2">{f.type}</span>
                  <span className="text-[12px] text-text-2">{f.detail}</span>
                </div>
              ))}
            </Card>
          )}
        </div>
      )}
      {result?.error && <ErrorCard label={t('toolPanels.error')} message={result.error} />}
    </div>
  );
}
function SubnetPanel() {
  const { t } = useTranslations();

  function ipToInt(ip: string): number {
    return ip.split('.').reduce((acc, oct) => (acc << 8) + parseInt(oct, 10), 0) >>> 0;
  }
  function intToIp(n: number): string {
    return [(n >>> 24) & 0xff, (n >>> 16) & 0xff, (n >>> 8) & 0xff, n & 0xff].join('.');
  }
  function cidrToMask(cidr: number): number {
    return cidr === 0 ? 0 : (0xffffffff << (32 - cidr)) >>> 0;
  }
  function maskToCidr(mask: number): number {
    let n = mask >>> 0, count = 0;
    while (n & 0x80000000) { count++; n = (n << 1) >>> 0; }
    return count;
  }
  function isValidIp(ip: string): boolean {
    const parts = ip.split('.');
    if (parts.length !== 4) return false;
    return parts.every(p => { const n = parseInt(p, 10); return !isNaN(n) && n >= 0 && n <= 255 && String(n) === p; });
  }
  function isValidMask(mask: string): boolean {
    if (!isValidIp(mask)) return false;
    const inv = (~ipToInt(mask)) >>> 0;
    return (inv & (inv + 1)) === 0;
  }
  function getIpType(ip: string): string {
    const n = ipToInt(ip);
    if ((n >>> 24) === 10 || ((n >>> 16) & 0xfff0) === 0xac10 || (n >>> 16) === 0xc0a8) return 'Private (RFC 1918)';
    if ((n >>> 24) === 127) return 'Loopback';
    if ((n >>> 28) === 0xe) return 'Multicast';
    return 'Public';
  }

  const [ip, setIp] = useState('');
  const [prefix, setPrefix] = useState('24');
  const [prefixMode, setPrefixMode] = useState<'cidr' | 'mask'>('cidr');
  const [errors, setErrors] = useState<{ ip?: string; prefix?: string }>({});
  const [result, setResult] = useState<null | {
    cidr: number; networkAddress: string; broadcastAddress: string;
    subnetMask: string; wildcardMask: string;
    firstUsable: string; lastUsable: string;
    usableHosts: number; totalHosts: number; ipType: string;
  }>(null);

  const run = () => {
    const errs: { ip?: string; prefix?: string } = {};
    if (!ip.trim()) errs.ip = 'IP address is required';
    else if (!isValidIp(ip.trim())) errs.ip = 'Invalid IP (e.g. 192.168.1.0)';

    let cidr = 0;
    if (prefixMode === 'cidr') {
      const n = parseInt(prefix.replace('/', ''), 10);
      if (isNaN(n) || n < 0 || n > 32) errs.prefix = 'CIDR must be 0–32';
      else cidr = n;
    } else {
      if (!isValidMask(prefix.trim())) errs.prefix = 'Invalid subnet mask';
      else cidr = maskToCidr(ipToInt(prefix.trim()));
    }

    setErrors(errs);
    if (Object.keys(errs).length > 0) return;

    const mask = cidrToMask(cidr);
    const ipInt = ipToInt(ip.trim());
    const netInt = (ipInt & mask) >>> 0;
    const bcastInt = (netInt | (~mask >>> 0)) >>> 0;
    const total = Math.pow(2, 32 - cidr);
    const usable = cidr >= 31 ? total : Math.max(0, total - 2);

    setResult({
      cidr,
      networkAddress: intToIp(netInt),
      broadcastAddress: intToIp(bcastInt),
      subnetMask: intToIp(mask),
      wildcardMask: intToIp(~mask >>> 0),
      firstUsable: cidr >= 31 ? intToIp(netInt) : intToIp(netInt + 1),
      lastUsable: cidr >= 31 ? intToIp(bcastInt) : intToIp(bcastInt - 1),
      usableHosts: usable,
      totalHosts: total,
      ipType: getIpType(ip.trim()),
    });
  };

  return (
    <div>
      <Card>
        <div className="flex gap-2 mb-3">
          {(['cidr', 'mask'] as const).map(m => (
            <button key={m} onClick={() => { setPrefixMode(m); setPrefix(m === 'cidr' ? '24' : '255.255.255.0'); setErrors({}); }}
              className={`px-3 py-1 text-[11px] rounded border transition-colors ${prefixMode === m ? 'border-blue/50 text-blue bg-blue/10' : 'border-border-2 text-text-3 hover:text-text-2'}`}>
              {m === 'cidr' ? 'CIDR' : 'Subnet Mask'}
            </button>
          ))}
        </div>

        <div className="flex gap-2 flex-wrap mb-2">
          <div className="flex flex-col gap-1 flex-1 min-w-[140px]">
            <input className="input-field" value={ip} onChange={e => { setIp(e.target.value); setErrors(p => ({ ...p, ip: undefined })); }}
              placeholder="192.168.1.0" onKeyDown={e => e.key === 'Enter' && run()} />
            {errors.ip && <span className="text-[11px] text-red">{errors.ip}</span>}
          </div>
          <div className="flex flex-col gap-1 min-w-[120px]">
            {prefixMode === 'cidr' ? (
              <input className="input-field" value={prefix} onChange={e => { setPrefix(e.target.value); setErrors(p => ({ ...p, prefix: undefined })); }}
                placeholder="/24" onKeyDown={e => e.key === 'Enter' && run()} />
            ) : (
              <input className="input-field" value={prefix} onChange={e => { setPrefix(e.target.value); setErrors(p => ({ ...p, prefix: undefined })); }}
                placeholder="255.255.255.0" onKeyDown={e => e.key === 'Enter' && run()} />
            )}
            {errors.prefix && <span className="text-[11px] text-red">{errors.prefix}</span>}
          </div>
          <RunBtn loading={false} label="Calculate" onClick={run} />
        </div>

        {prefixMode === 'cidr' && (
          <div className="mt-3">
            <input type="range" min="0" max="32"
              value={parseInt(prefix) || 24}
              onChange={e => setPrefix(e.target.value)}
              className="w-full accent-blue cursor-pointer" />
            <div className="flex justify-between text-[10px] text-text-3 mt-0.5">
              {[0, 8, 16, 24, 32].map(n => (
                <button key={n} onClick={() => setPrefix(String(n))} className="hover:text-blue transition-colors">/{n}</button>
              ))}
            </div>
          </div>
        )}
      </Card>

      {result && (
        <Card>
          <Row label="Network Address" value={`${result.networkAddress}/${result.cidr}`} />
          <Row label="Subnet Mask" value={result.subnetMask} />
          <Row label="Wildcard Mask" value={result.wildcardMask} />
          <Row label="Broadcast Address" value={result.broadcastAddress} />
          <Row label="First Usable IP" value={result.firstUsable} />
          <Row label="Last Usable IP" value={result.lastUsable} />
          <Row label="Usable Hosts" value={result.usableHosts.toLocaleString()} />
          <Row label="Total Addresses" value={result.totalHosts.toLocaleString()} />
          <Row label="IP Type" value={result.ipType} />
        </Card>
      )}
    </div>
  );
}
const TOOL_TITLES: Record<string, string> = {
  crypto: 'Crypto Address Lookup', qr: 'QR Code Decoder',
  metadata: 'File Metadata & GEOINT', headers: 'Email Header Analyzer', mac: 'MAC Lookup',
  subnet: 'IP / Subnet Calculator', hash: 'Hash Identifier', encoder: 'Base64 & URL Encoder',
  jwt: 'JWT Decoder',
};

interface Props {
  mode: ToolMode;
  onBack: () => void;
}

export function ToolPanels({ mode, onBack }: Props) {
  const { t } = useTranslations();
  const [activePanel] = useState<ToolMode>(mode);

  return (
    <div className="p-5 animate-fade-in">
      <div className="flex items-center gap-3 mb-5 pb-4 border-b border-border-1">
        <button onClick={onBack}
          className="flex items-center gap-1.5 text-[11px] text-text-3 hover:text-text-2 transition-colors px-2 py-1 rounded hover:bg-surface-3">
          <ArrowLeft size={12} /> {t('toolPanels.back')}
        </button>
        <div className="w-px h-4 bg-border-1" />
        <span className="text-[13px] font-bold text-text-1">{TOOL_TITLES[activePanel ?? mode ?? ''] || ''}</span>
      </div>

      {activePanel === 'crypto' && <CryptoPanel />}
      {activePanel === 'qr' && <QrPanel />}
      {activePanel === 'metadata' && <MetadataPanel />}
      {activePanel === 'headers' && <HeadersPanel />}
      {activePanel === 'subnet' && <SubnetPanel />}
      {activePanel === 'mac' && <MacPanel />}
      {activePanel === 'hash' && <HashPanel />}
      {activePanel === 'encoder' && <EncoderPanel />}
      {activePanel === 'jwt' && <JwtPanel />}
    </div>
  );
}