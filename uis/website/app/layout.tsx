import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
import '../src/styles.css';

export const metadata: Metadata = {
  title: 'TrackFlow — Logistics that moves with your brand',
  description: 'TrackFlow connects e-commerce brands with reliable warehousing, order fulfillment, last-mile delivery and returns across Los Angeles and Zaragoza.',
};

export const viewport: Viewport = { themeColor: '#f5f6f1' };

export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="en"><head><link rel="preconnect" href="https://fonts.googleapis.com" /><link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" /><link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet" /></head><body>{children}</body></html>;
}