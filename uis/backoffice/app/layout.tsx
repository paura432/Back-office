import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
import { DM_Mono, DM_Sans } from 'next/font/google';
import '../src/styles.css';

const dmSans = DM_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-dm-sans',
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
  title: 'Operations Backoffice — TrackFlow',
  description: 'TrackFlow internal operations dashboard for warehouse, carrier, reverse-logistics, customer experience, and technology teams.',
};

export const viewport: Viewport = { themeColor: '#f4f6f8' };

export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="en" className={`${dmSans.variable} ${dmMono.variable}`}><body>{children}</body></html>;
}