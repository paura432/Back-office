import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
import { DM_Mono, Manrope } from 'next/font/google';
import '../src/styles.css';

const manrope = Manrope({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '800'],
  display: 'swap',
  variable: '--font-manrope',
  preload: true,
});

const dmMono = DM_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  display: 'swap',
  variable: '--font-dm-mono',
  preload: false,
});

export const metadata: Metadata = {
  title: 'TrackFlow — Logistics that moves with your brand',
  description: 'TrackFlow connects e-commerce brands with reliable warehousing, order fulfillment, last-mile delivery and returns across Los Angeles and Zaragoza.',
};

export const viewport: Viewport = { themeColor: '#f5f6f1' };

export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="en" className={`${manrope.variable} ${dmMono.variable}`}><body>{children}</body></html>;
}