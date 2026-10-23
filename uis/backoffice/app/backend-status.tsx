'use client';

import { useEffect, useState } from 'react';

type BackendStatus = 'checking' | 'operational' | 'degraded' | 'unreachable';

export default function BackendStatus() {
  const [status, setStatus] = useState<BackendStatus>('checking');

  useEffect(() => {
    let cancelled = false;

    async function refresh() {
      try {
        const response = await fetch('/api/status');
        const payload = (await response.json()) as { status?: string };
        if (cancelled) return;
        setStatus(payload.status === 'operational' ? 'operational' : 'degraded');
      } catch {
        if (!cancelled) setStatus('unreachable');
      }
    }

    refresh();
    const timer = setInterval(refresh, 15000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  const label =
    status === 'checking'
      ? 'CHECKING BACKEND'
      : status === 'operational'
        ? 'BACKEND OPERATIONAL'
        : status === 'degraded'
          ? 'BACKEND DEGRADED'
          : 'BACKEND UNREACHABLE';

  const tone =
    status === 'operational' ? 'green' : status === 'checking' ? 'blue' : 'amber';

  return (
    <span className={`backend-status backend-status--${tone}`}>
      <i aria-hidden="true" />
      {label}
    </span>
  );
}