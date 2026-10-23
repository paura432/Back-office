import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
<<<<<<< HEAD
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

=======
import '../src/styles.css';

>>>>>>> origin/main
export const metadata: Metadata = {
  title: 'Operations Backoffice — TrackFlow',
  description: 'TrackFlow internal operations dashboard for warehouse, carrier, reverse-logistics, customer experience, and technology teams.',
};

export const viewport: Viewport = { themeColor: '#f4f6f8' };

export default function RootLayout({ children }: { children: ReactNode }) {
<<<<<<< HEAD
  return <html lang="en" className={`${dmSans.variable} ${dmMono.variable}`}><body>{children}</body></html>;
=======
  return <html lang="en"><head><link rel="preconnect" href="https://fonts.googleapis.com" /><link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" /><link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" /></head><body>{children}</body></html>;
>>>>>>> origin/main
}