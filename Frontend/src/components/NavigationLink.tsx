"use client";

import React from 'react';
import Link from 'next/link';
import { useNavigationLoading } from '@/context/NavigationLoadingContext';
import { usePathname, useRouter } from 'next/navigation';

interface NavigationLinkProps {
  href: string;
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  prefetch?: boolean;
}

const NavigationLink: React.FC<NavigationLinkProps> = ({ 
  href, 
  children, 
  className, 
  onClick,
  prefetch = true,
}) => {
  const { startLoading } = useNavigationLoading();
  const pathname = usePathname();
  const router = useRouter();

  const handleClick = () => {
    // Avoid triggering loading when clicking the already active route
    if (pathname !== href) {
      startLoading();
    }
    if (onClick) {
      onClick();
    }
  };

  const handleMouseEnter = () => {
    if (prefetch) {
      try {
        router.prefetch(href);
      } catch {
        // ignore prefetch errors silently
      }
    }
  };

  return (
    <Link href={href} className={className} onClick={handleClick} onMouseEnter={handleMouseEnter}>
      {children}
    </Link>
  );
};

export default NavigationLink;
