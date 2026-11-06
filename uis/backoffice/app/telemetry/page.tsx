import type { Metadata } from 'next';
import TelemetryReportView from './report-view';
import './telemetry.css';

export const metadata: Metadata = {
  title: 'Telemetry report — TrackFlow',
  description: 'Technical view of the events stored in telemetry_events: volume, frontend errors and Web Vitals.',
};

export default function TelemetryPage() {
  return <TelemetryReportView />;
}
