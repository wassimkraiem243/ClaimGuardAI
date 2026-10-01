import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import { Sidebar } from '../components/Sidebar';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-inter',
});

const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-jetbrains',
});

export const metadata: Metadata = {
  title: 'ClaimGuard AI',
  description: 'Pre-submission claim validation against payer rules',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrains.variable}`}>
      <body className="min-h-screen bg-bg text-text antialiased">
        <Sidebar />
        <div className="min-h-screen overflow-x-hidden pt-14 md:pl-[252px] md:pt-4 md:pr-4 md:pb-4">
          {children}
        </div>
      </body>
    </html>
  );
}
