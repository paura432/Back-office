'use client';

import { useEffect, useState } from 'react';
import { track } from '../src/services/telemetry';
import { fingerprint, routeTemplate } from './telemetry-reporter';

type BackendStatus = 'checking' | 'operational' | 'degraded' | 'unreachable';

export default function BackendStatus() {
  const [status, setStatus] = useState<BackendStatus>('checking');

  useEffect(() => {
    let cancelled = false;
    let failing = false; // Report only the transition into failure, not every 15 s poll.

    function reportFailure(requestId?: string, httpStatus?: number) {
      if (failing) return;
      failing = true;
      track('frontend_error_occurred', {
        app: 'backoffice',
        route_template: routeTemplate(),
        error_kind: 'fetch_failed',
        error_fingerprint: fingerprint(`fetch_failed|/status|${httpStatus ?? 'network'}`),
        ...(httpStatus ? { http_status: httpStatus } : {}),
      }, { requestId });
    }

    async function refresh() {
      // randomUUID is unavailable outside secure contexts; then the request is not correlated.
      const requestId = crypto.randomUUID?.();
      try {
        const response = await fetch('/api/status', requestId ? { headers: { 'X-Request-Id': requestId } } : undefined);
        if (response.ok) failing = false;
        else reportFailure(requestId, response.status);
        const payload = (await response.json()) as { status?: string };
        if (cancelled) return;
        setStatus(payload.status === 'operational' ? 'operational' : 'degraded');
      } catch {
        reportFailure(requestId);
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