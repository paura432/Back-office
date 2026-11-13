import type { Metadata } from 'next';
import KpiDashboard from './kpi-dashboard';
import './reporting.css';

export const metadata: Metadata = {
  title: 'Business performance — TrackFlow',
  description: 'Weekly executive KPIs by country: shipments, on-time deliveries, shipping cost, returns and customer satisfaction.',
};

export default function ReportingPage() {
  return <KpiDashboard />;
}
