'use client';
import { useState, useCallback } from 'react';
import { Loader2, ArrowLeft, ExternalLink, Upload, XCircle, FileUp } from 'lucide-react';
import * as api from '@/lib/api';
import type { ToolMode, CryptoResult, QrResult, HeaderAnalysisResult, MetaResult } from '@/lib/types';

function Card({ title, children, className }: { title?: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`card mb-3 animate-fade-in ${className ?? ''}`}>
      {title && <div className="card-head">{title}</div>}
      <div className="p-4">{children}</div>
    </div>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <div className="card mb-3 border-red/20 animate-fade-in">
      <div className="p-4 flex gap-3 items-start">
        <div className="w-7 h-7 rounded-md bg-red/10 flex items-center justify-center shrink-0 mt-0.5">
          <XCircle size={14} className="text-red" />
        </div>
        <div>
          <div className="text-[12px] font-semibold text-red mb-1">Error</div>
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
      {loading ? 'Running…' : label}
    </button>
  );
}

function CryptoPanel() {
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
      <Card title="Crypto Address Lookup · Bitcoin & Ethereum">
        <div className="flex gap-2 flex-wrap"><Input value={addr} onChange={setAddr} placeholder="1A1zP1…  /  0x742d…  /  bc1q…" onEnter={run} /><RunBtn loading={loading} label="Lookup" onClick={run} /></div>
      </Card>
      {result && (
        result.error && !result.balance ? (
          <ErrorCard message={result.error} />
        ) : (
          <Card>
            <Row label="Type" value={result.type} />
            <Row label="Address" value={result.address} />
            <Row label="Balance" value={result.balance} />
            <Row label="≈ USD" value={result.balance_usd} />
            <Row label="Total Received" value={result.total_received} />
            <Row label="Total Sent" value={result.total_sent} />
            <Row label="Transactions" value={result.tx_count} />
            {result.explorer_url && (
              <div className="pt-3">
                <a href={result.explorer_url} target="_blank" rel="noreferrer" className="btn-ghost h-8 px-3 text-[11px] inline-flex items-center gap-1">
                  <ExternalLink size={11} /> Open Explorer
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
          <div className="text-[10px] text-text-3">{(file.size / 1024).toFixed(1)} KB · click to change</div>
        </>
      ) : (
        <>
          <div className="text-[12px] font-semibold text-text-2">Drop file here or <span className="text-blue">browse</span></div>
          { hint && <div className="text-[10px] text-text-3">{hint}</div> }
        </>
      )}
      <input type="file" accept={accept} className="hidden" onChange={e => onChange(e.target.files?.[0] ?? null)} />
    </label>
  );
}

function QrPanel() {
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
      <Card title="QR Code Decoder">
        <div className="flex flex-col gap-3">
          <DropZone accept="image/*" file={file} onChange={setFile} hint="PNG, JPG, WEBP supported" />
          <RunBtn loading={loading} label="Decode QR" onClick={run} disabled={!file} />
        </div>
      </Card>
      {result && (
        <Card>
          {result.error ? (
            <ErrorCard message={result.error} />
          ) : (
            <div>
              <Row label="Type" value={result.type} />
              <div className="flex gap-3 text-[12px] py-1">
                <span className="text-text-3 w-36 shrink-0">Content</span>
                {result.is_url ? (
                  <a href={result.decoded} target="_blank" rel="noreferrer" className="text-blue font-mono text-[11px] break-all hover:underline">{result.decoded}</a>
                ) : (
                  <span className="font-mono text-[11px] break-all">{result.decoded}</span>
                )}
              </div>
              {result.is_url && result.decoded && (
                <a href={result.decoded} target="_blank" rel="noreferrer" className="btn-ghost h-8 px-3 text-[11px] mt-3 inline-flex items-center gap-1">
                  <ExternalLink size={11} /> Open URL
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
      <Card title="File Metadata &amp; GEOINT">
        <div className="flex flex-col gap-3">
          <DropZone accept=".jpg,.jpeg,.png,.tiff,.heic,.webp,.pdf,.docx" file={file} onChange={setFile} hint="JPG, PNG, TIFF, HEIC, PDF, DOCX" />
          <RunBtn loading={loading} label="Extract Metadata" onClick={run} disabled={!file} />
        </div>
      </Card>
      {result && (
        <div>
          {result.error ? (
            <ErrorCard message={result.error} />
          ) : (
            <>
              <Card title="File Info">
                <Row label="Filename" value={result.filename} />
                <Row label="Type" value={result.file_type} />
                <Row label="Size" value={result.file_size ? `${(result.file_size / 1024).toFixed(1)} KB` : undefined} />
                <Row label="Dimensions" value={result.dimensions ? `${result.dimensions.width} × ${result.dimensions.height} px` : undefined} />
                <Row label="Author / Copyright" value={result.author} />
                <Row label="Software" value={result.software} />
              </Card>
              {result.timestamps && Object.keys(result.timestamps).length > 0 && (
                <Card title="Timestamps">
                  {Object.entries(result.timestamps).map(([k, v]) => (
                    <Row key={k} label={k} value={v} />
                  ))}
                </Card>
              )}
              {result.camera && Object.keys(result.camera).length > 0 && (
                <Card title="Camera">
                  {Object.entries(result.camera).map(([k, v]) => (
                    <Row key={k} label={k} value={v} />
                  ))}
                </Card>
              )}
              {result.gps && (
                <Card title="GPS Location">
                  <Row label="Latitude" value={result.gps.lat} />
                  <Row label="Longitude" value={result.gps.lng} />
                  {result.gps.altitude && <Row label="Altitude" value={`${Math.round(result.gps.altitude)}m`} />}
                  <div className="mt-3">
                    <a href={`https://www.google.com/maps?q=${result.gps.lat},${result.gps.lng}`} target="_blank" rel="noreferrer" className="btn-ghost h-8 px-3 text-[11px] inline-flex items-center gap-1">
                      <ExternalLink size={11} /> Open in Maps
                    </a>
                  </div>
                </Card>
              )}
              {result.exif && Object.keys(result.exif).length > 0 && (
                <Card title="EXIF / XMP Data">
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

function HeadersPanel() {
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
      <Card title="Email Header Analyzer · Paste raw headers">
        <textarea value={text} onChange={e => setText(e.target.value)} rows={10}
          placeholder="Paste raw email headers here (Gmail: 3-dot menu → Show original)…"
          className="input-field font-mono text-[11px] resize-y leading-relaxed w-full mb-3" />
        <RunBtn loading={loading} label="Analyse" onClick={run} disabled={!text.trim()} />
      </Card>
      {result && !result.error && (
        <div>
          <Card title="Message Metadata">
            <Row label="From" value={result.from} />
            <Row label="To" value={result.to} />
            <Row label="Subject" value={result.subject} />
            <Row label="Date" value={result.date} />
            <Row label="Reply-To" value={result.reply_to} />
            <Row label="X-Mailer" value={result.x_mailer} />
          </Card>
          <Card title="Authentication">
            <Row label="SPF" value={result.spf} />
            <Row label="DKIM" value={result.dkim} />
            <Row label="DMARC" value={result.dmarc} />
          </Card>
          {result.origin_ip && (
            <Card title="Origin">
              <Row label="IP" value={result.origin_ip} />
              <Row label="rDNS" value={result.origin_rdns} />
              {result.origin_geo && (
                <>
                  <Row label="City" value={result.origin_geo.city} />
                  <Row label="Country" value={result.origin_geo.country} />
                  <Row label="Org" value={result.origin_geo.org} />
                </>
              )}
            </Card>
          )}
          {result.spoofing_flags && result.spoofing_flags.length > 0 && (
            <Card title="⚠ Spoofing Indicators">
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
      {result?.error && <ErrorCard message={result.error} />}
    </div>
  );
}

const TOOL_TITLES: Record<string, string> = {
  crypto: 'Crypto Address Lookup', qr: 'QR Code Decoder',
  metadata: 'File Metadata & GEOINT', headers: 'Email Header Analyzer',
};

interface Props {
  mode: ToolMode;
  onBack: () => void;
}

export function ToolPanels({ mode, onBack }: Props) {
  const [activePanel] = useState<ToolMode>(mode);

  return (
    <div className="p-5 animate-fade-in">
      <div className="flex items-center gap-3 mb-5 pb-4 border-b border-border-1">
        <button onClick={onBack}
          className="flex items-center gap-1.5 text-[11px] text-text-3 hover:text-text-2 transition-colors px-2 py-1 rounded hover:bg-surface-3">
          <ArrowLeft size={12} /> Back
        </button>
        <div className="w-px h-4 bg-border-1" />
        <span className="text-[13px] font-bold text-text-1">{TOOL_TITLES[activePanel ?? mode ?? ''] || ''}</span>
      </div>

      {activePanel === 'crypto' && <CryptoPanel />}
      {activePanel === 'qr' && <QrPanel />}
      {activePanel === 'metadata' && <MetadataPanel />}
      {activePanel === 'headers' && <HeadersPanel />}
    </div>
  );
}
