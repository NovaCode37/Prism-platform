export function Logo({ size = 26, animated = false }: { size?: number; animated?: boolean }) {
  const h = Math.round(size * 0.846);
  const gId = animated ? 'logo-grad-a' : 'logo-grad';

  const eyeOpen   = 'M2 22C2 22 13 6 26 6C39 6 50 22 50 22C50 22 39 38 26 38C13 38 2 22 2 22Z';
  const eyeClosed = 'M2 22C2 22 13 22 26 22C39 22 50 22 50 22C50 22 39 22 26 22C13 22 2 22 2 22Z';
  const blinkPath = `${eyeOpen}; ${eyeOpen}; ${eyeClosed}; ${eyeClosed}; ${eyeOpen}; ${eyeOpen}`;
  const blinkKT   = '0; 0.68; 0.74; 0.8; 0.86; 1';
  const blinkShow = '1; 1; 0; 0; 1; 1';

  return (
    <svg width={size} height={h} viewBox="0 0 52 44" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id={gId} x1="0" y1="0" x2="52" y2="44" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#4f8ef7" />
          <stop offset="100%" stopColor="#7c5cfc" />
        </linearGradient>
        {animated && (
          <filter id="logo-glow-f" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="1.6" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        )}
      </defs>

      <path
        d={eyeOpen}
        stroke={`url(#${gId})`} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
        filter={animated ? 'url(#logo-glow-f)' : undefined}
      >
        {animated && (
          <animate attributeName="d"
            values={blinkPath} keyTimes={blinkKT}
            dur="4s" repeatCount="indefinite" calcMode="linear" />
        )}
      </path>

      <g>
        {animated && (
          <animate attributeName="opacity"
            values={blinkShow} keyTimes={blinkKT}
            dur="4s" repeatCount="indefinite" calcMode="linear" />
        )}

        <circle cx="26" cy="22" r="9" stroke={`url(#${gId})`} strokeWidth="2">
          {animated && <animate attributeName="r" values="9;9.8;9" dur="2.5s" repeatCount="indefinite" />}
        </circle>

        <circle cx="26" cy="22" r="4.5" stroke={`url(#${gId})`} strokeWidth="1.2" opacity="0.6" />

        <circle cx="26" cy="22" r="2.2" fill={`url(#${gId})`}>
          {animated && <animate attributeName="r" values="2.2;3.2;2.2" dur="1.6s" repeatCount="indefinite" />}
        </circle>

        <line x1="26" y1="13" x2="26" y2="17" stroke={`url(#${gId})`} strokeWidth="1.8" strokeLinecap="round" />
        <line x1="26" y1="27" x2="26" y2="31" stroke={`url(#${gId})`} strokeWidth="1.8" strokeLinecap="round" />
        <line x1="17" y1="22" x2="21" y2="22" stroke={`url(#${gId})`} strokeWidth="1.8" strokeLinecap="round" />
        <line x1="31" y1="22" x2="35" y2="22" stroke={`url(#${gId})`} strokeWidth="1.8" strokeLinecap="round" />
      </g>

      <path d="M36 10 A16 16 0 0 1 44 22" stroke={`url(#${gId})`} strokeWidth="1.5"
        strokeLinecap="round" opacity={animated ? 0.65 : 0.45}>
        {animated && (
          <animateTransform attributeName="transform" type="rotate"
            from="0 26 22" to="360 26 22" dur="5s" repeatCount="indefinite" />
        )}
      </path>

      {animated && (
        <path d="M16 34 A16 16 0 0 1 8 22" stroke={`url(#${gId})`} strokeWidth="1"
          strokeLinecap="round" opacity="0.3">
          <animateTransform attributeName="transform" type="rotate"
            from="0 26 22" to="-360 26 22" dur="8s" repeatCount="indefinite" />
        </path>
      )}
    </svg>
  );
}
