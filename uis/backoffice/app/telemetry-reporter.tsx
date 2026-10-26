'use client';

import { useEffect } from 'react';
import { useReportWebVitals } from 'next/web-vitals';
import { track, type EventProperties } from '../src/services/telemetry';

type VitalName = EventProperties['web_vitals_measured']['metric'];
const VITALS = new Set<string>(['LCP', 'CLS', 'INP', 'TTFB', 'FCP']);
let pageViewed = false; // React Strict Mode runs effects twice in development.

// Only templates, never raw URLs: the backoffice has a single static route.
export const routeTemplate = () => (window.location.pathname === '/' ? '/' : '<unmatched>');

const viewportClass = () => (window.innerWidth < 768 ? 'mobile' : window.innerWidth < 1024 ? 'tablet' : 'desktop');

// FNV-1a 64-bit: groups identical errors without sending messages or stacks.
export function fingerprint(text: string): string {
  let hash = 0xcbf29ce484222325n;
  for (const char of text) hash = BigInt.asUintN(64, (hash ^ BigInt(char.codePointAt(0)!)) * 0x100000001b3n);
  return hash.toString(16).padStart(16, '0');
}

function referrerType() {
  if (!document.referrer) return 'direct';
  try {
    return new URL(document.referrer).origin === window.location.origin ? 'internal' : 'external';
  } catch {
    return 'unknown';
  }
}

function reportError(kind: 'js_exception' | 'unhandled_rejection', message: string, source = '') {
  let path = '';
  try {
    path = source ? new URL(source).pathname : '';
  } catch {
    // Unparseable source: fingerprint without it.
  }
  track('frontend_error_occurred', {
    app: 'backoffice',
    route_template: routeTemplate(),
    error_kind: kind,
    error_fingerprint: fingerprint(`${kind}|${message.replace(/\d+/g, '0')}|${path}`),
  });
}

function reportWebVital(metric: { name: string; value: number; rating: string }) {
  if (!VITALS.has(metric.name)) return;
  track('web_vitals_measured', {
    app: 'backoffice',
    route_template: routeTemplate(),
    metric: metric.name as VitalName,
    value: Math.max(0, metric.value),
    rating: metric.rating === 'needs-improvement' ? 'needs_improvement' : metric.rating === 'poor' ? 'poor' : 'good',
    viewport_class: viewportClass(),
  });
}

export default function TelemetryReporter() {
  useReportWebVitals(reportWebVital);

  useEffect(() => {
    if (!pageViewed) {
      pageViewed = true;
      const locale = navigator.language;
      track('page_viewed', {
        app: 'backoffice',
        route_template: routeTemplate(),
        viewport_class: viewportClass(),
        referrer_type: referrerType(),
        ...(/^[a-z]{2}(-[A-Z]{2})?$/.test(locale) ? { locale } : {}),
      });
    }
    const onError = (event: ErrorEvent) => reportError('js_exception', String(event.message), event.filename);
    const onRejection = (event: PromiseRejectionEvent) =>
      reportError('unhandled_rejection', event.reason instanceof Error ? event.reason.message : String(event.reason));
    window.addEventListener('error', onError);
    window.addEventListener('unhandledrejection', onRejection);
    return () => {
      window.removeEventListener('error', onError);
      window.removeEventListener('unhandledrejection', onRejection);
    };
  }, []);

  return null;
}
