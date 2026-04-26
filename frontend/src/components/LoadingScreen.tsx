'use client';
import { useEffect, useRef, useState } from 'react';

const MODULES = [
  { id: 'core',    label: 'CORE SYSTEMS',   prefix: '[SYS]' },
  { id: 'intel',   label: 'INTEL ENGINE',   prefix: '[INT]' },
  { id: 'threat',  label: 'THREAT MODULES', prefix: '[THR]' },
  { id: 'network', label: 'NETWORK LAYER',  prefix: '[NET]' },
  { id: 'crypto',  label: 'CRYPTO ENGINE',  prefix: '[CRY]' },
];

const STATUSES = [
  'INITIALIZING KERNEL',
  'LOADING MODULES',
  'ESTABLISHING CONNECTIONS',
  'CALIBRATING INTEL ENGINE',
  'SYSTEM READY',
];

function MatrixCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const chars = '01アイウエオカキクABCDEF0123456789#@!%&';
    const fontSize = 13;
    const drops: number[] = [];
    const initDrops = () => {
      const cols = Math.floor(canvas.width / fontSize);
      drops.length = 0;
      for (let i = 0; i < cols; i++) drops.push(Math.random() * -60);
    };
    initDrops();
    window.addEventListener('resize', initDrops);

    const draw = () => {
      ctx.fillStyle = 'rgba(13,17,23,0.06)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const cols = Math.floor(canvas.width / fontSize);
      for (let i = 0; i < Math.min(drops.length, cols); i++) {
        const char = chars[Math.floor(Math.random() * chars.length)];
        const bright = Math.random() > 0.96;
        ctx.fillStyle = bright
          ? 'rgba(255,255,255,0.9)'
          : `rgba(79,142,247,${Math.random() * 0.4 + 0.08})`;
        ctx.font = `${fontSize}px 'JetBrains Mono', monospace`;
        ctx.fillText(char, i * fontSize, drops[i] * fontSize);
        if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0;
        drops[i]++;
      }
    };

    const interval = setInterval(draw, 55);
    return () => {
      clearInterval(interval);
      window.removeEventListener('resize', resize);
      window.removeEventListener('resize', initDrops);
    };
  }, []);

  return <canvas ref={canvasRef} className="prism-matrix-canvas" />;
}

function LoadingScreen({ fading, onDone }: { fading: boolean; onDone: () => void }) {
  const [statusIdx, setStatusIdx] = useState(0);
  const [progress, setProgress] = useState(0);
  const [activeModules, setActiveModules] = useState<number[]>([]);
  const [bootLine, setBootLine] = useState('');
  const calledDone = useRef(false);

  useEffect(() => {
    const progressTimer = setInterval(() => {
      setProgress(p => {
        if (p >= 100) {
          clearInterval(progressTimer);
          if (!calledDone.current) {
            calledDone.current = true;
            setTimeout(onDone, 300);
          }
          return 100;
        }
        const increment = Math.max(0.9, Math.random() * ((100 - p) * 0.14));
        return Math.min(p + increment, 100);
      });
    }, 140);

    const statusTimers = STATUSES.map((_, i) =>
      setTimeout(() => setStatusIdx(i), i * 600)
    );

    MODULES.forEach((_, i) => {
      setTimeout(() => setActiveModules(prev => [...prev, i]), 350 + i * 520);
    });

    const bootText = '> PRISM OSINT v2.1 — boot sequence initiated...';
    let charIdx = 0;
    const typeTimer = setInterval(() => {
      if (charIdx <= bootText.length) {
        setBootLine(bootText.slice(0, charIdx));
        charIdx++;
      } else {
        clearInterval(typeTimer);
      }
    }, 38);

    return () => {
      clearInterval(progressTimer);
      statusTimers.forEach(t => clearTimeout(t));
      clearInterval(typeTimer);
    };
  }, []);

  return (
    <div className={`prism-loading${fading ? ' fading' : ''}`}>
      <MatrixCanvas />
      <div className="scanlines" />

      <div className="prism-corner tl" />
      <div className="prism-corner tr" />
      <div className="prism-corner bl" />
      <div className="prism-corner br" />

      <div className="prism-boot-line">
        {bootLine}<span className="prism-cursor">█</span>
      </div>

      <div className="prism-eye">
        <div className="prism-ring ring-1" />
        <div className="prism-ring ring-2" />
        <svg viewBox="0 0 52 44" fill="none">
          <defs>
            <linearGradient id="lg" x1="0" y1="0" x2="52" y2="44" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#4f8ef7"/>
              <stop offset="100%" stopColor="#7c5cfc"/>
            </linearGradient>
          </defs>
          <path d="M2 22C2 22 13 6 26 6C39 6 50 22 50 22C50 22 39 38 26 38C13 38 2 22 2 22Z" stroke="url(#lg)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
          <circle cx="26" cy="22" r="9" stroke="url(#lg)" strokeWidth="2"/>
          <circle cx="26" cy="22" r="4.5" stroke="url(#lg)" strokeWidth="1.2" opacity="0.6"/>
          <circle cx="26" cy="22" r="2.2" fill="url(#lg)"/>
          <line x1="26" y1="13" x2="26" y2="17" stroke="url(#lg)" strokeWidth="1.8" strokeLinecap="round"/>
          <line x1="26" y1="27" x2="26" y2="31" stroke="url(#lg)" strokeWidth="1.8" strokeLinecap="round"/>
          <line x1="17" y1="22" x2="21" y2="22" stroke="url(#lg)" strokeWidth="1.8" strokeLinecap="round"/>
          <line x1="31" y1="22" x2="35" y2="22" stroke="url(#lg)" strokeWidth="1.8" strokeLinecap="round"/>
          <path d="M36 10 A16 16 0 0 1 44 22" stroke="url(#lg)" strokeWidth="1.5" strokeLinecap="round" opacity="0.45"/>
        </svg>
      </div>

      <div className="prism-loading-text">PRISM</div>
      <div className="prism-loading-sub">OSINT Platform v2.1</div>

      <div className="prism-status-bar">
        <div className="prism-status-text">{STATUSES[statusIdx]}</div>
        <div className="prism-progress-track">
          <div className="prism-progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <div className="prism-progress-percent">{Math.round(progress)}%</div>
      </div>

      <div className="prism-modules">
        {MODULES.map((mod, i) => (
          <div key={mod.id} className={`module-item${activeModules.includes(i) ? ' active' : ''}`}>
            <span className="module-prefix">{mod.prefix}</span>
            <span className="module-status">{activeModules.includes(i) ? '■' : '□'}</span>
            {mod.label}
          </div>
        ))}
      </div>
    </div>
  );
}

export function LoadingWrapper({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [fading, setFading] = useState(false);
  const [mounted, setMounted] = useState(false);

  const handleDone = () => {
    setFading(true);
    setTimeout(() => setLoading(false), 450);
  };

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <>
      {loading && <LoadingScreen fading={fading} onDone={handleDone} />}
      <div className={loading ? 'opacity-0 pointer-events-none' : 'prism-content-ready'}>
        {children}
      </div>
    </>
  );
}
