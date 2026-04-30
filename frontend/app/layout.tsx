import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Meridian Support Chatbot',
  description: 'Customer support chatbot powered by MCP and Groq',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
