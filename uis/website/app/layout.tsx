import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
<<<<<<< HEAD
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

=======
import '../src/styles.css';

>>>>>>> origin/main
export const metadata: Metadata = {
  title: 'TrackFlow — Logistics that moves with your brand',
  description: 'TrackFlow connects e-commerce brands with reliable warehousing, order fulfillment, last-mile delivery and returns across Los Angeles and Zaragoza.',
};

export const viewport: Viewport = { themeColor: '#f5f6f1' };

export default function RootLayout({ children }: { children: ReactNode }) {
<<<<<<< HEAD
  return <html lang="en" className={`${manrope.variable} ${dmMono.variable}`}><body>{children}</body></html>;
=======
  return <html lang="en"><head><link rel="preconnect" href="https://fonts.googleapis.com" /><link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" /><link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet" /></head><body>{children}</body></html>;
>>>>>>> origin/main
}