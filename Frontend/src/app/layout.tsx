import './globals.css';
import { Metadata } from "next";
import { Outfit } from 'next/font/google';
import { AppToaster } from '@/components/ui/AppToaster';
import { Toaster as SonnerToaster } from 'sonner';
import { NavigationLoadingProvider } from '@/context/NavigationLoadingContext';
import NavigationLoadingOverlay from '@/components/NavigationLoadingOverlay';
import Script from 'next/script';

const outfit = Outfit({
  subsets: ["latin"],
  variable: '--font-outfit',
  weight: ['100', '200', '300', '400', '500', '600', '700', '800', '900'],
  display: 'swap',
});

export const metadata: Metadata = {
  title: "Yuba - A Sounding Board for African Entrepreneurs",
  description: "Get contextual and actionable market insights to validate your business ideas. Join early-stage founders building the next generation of African startups.",
  metadataBase: new URL('https://www.yubanow.com'),
  openGraph: {
    title: "Yuba - A Sounding Board for African Entrepreneurs",
    description: "Get contextual and actionable market insights to validate your business ideas. Join early-stage founders building the next generation of African startups.",
    url: 'https://www.yubanow.com',
    siteName: 'Yuba',
    locale: 'en_US',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: "Yuba - A Sounding Board for African Entrepreneurs",
    description: "Get contextual and actionable market insights to validate your business ideas. Join early-stage founders building the next generation of African startups.",
  },
  icons: {
    icon: [
      { url: '/favicon.ico' },
    ],
    apple: [
      { url: '/apple-touch-icon.png' },
    ],
  },
  manifest: '/site.webmanifest',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={outfit.variable}>
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        {/* YouTube preconnect for faster video loading */}
        <link rel="preconnect" href="https://www.youtube.com" />
        <link rel="preconnect" href="https://www.youtube-nocookie.com" />
        <link rel="preconnect" href="https://i.ytimg.com" />
        <link rel="preconnect" href="https://img.youtube.com" />
      </head>
      <body className={`${outfit.className} dark:bg-gray-900`}>
        {/* Microsoft Clarity Analytics */}
        {/* <Script id="clarity-script" strategy="afterInteractive">
          {`
            (function(c,l,a,r,i,t,y){
              c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
              t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
              y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
            })(window, document, "clarity", "script", "un0k7woue7");
          `}
        </Script> */}

        <NavigationLoadingProvider>
          {children}
          <NavigationLoadingOverlay />
          <AppToaster />
          <SonnerToaster 
            position="top-center"
            richColors
            closeButton
            toastOptions={{
              style: {
                background: 'white',
                color: '#0f172a',
                border: '1px solid #e2e8f0',
              },
              className: 'dark:bg-gray-800 dark:text-white dark:border-gray-700',
            }}
          />
        </NavigationLoadingProvider>
      </body>
    </html>
  );
}
