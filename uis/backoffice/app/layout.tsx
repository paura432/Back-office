import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
import '../src/styles.css';

export const metadata: Metadata = {
  title: 'Operations Backoffice — TrackFlow',
  description: 'TrackFlow internal operations dashboard for warehouse, carrier, reverse-logistics, customer experience, and technology teams.',
};

export const viewport: Viewport = { themeColor: '#f4f6f8' };

export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="en"><head><link rel="preconnect" href="https://fonts.googleapis.com" /><link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" /><link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" /></head><body>{children}</body></html>;
}