"use client";

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useUser, useIsAuthenticated, useIsLoading, useLogout } from '@/stores/authStore';
import Image from 'next/image';

// Navigation links configuration
const NAV_LINKS: { name: string; href: string; disabled: boolean }[] = [
  { name: 'Product', href: '#', disabled: true },
  { name: 'Solutions', href: '#', disabled: true },
  { name: 'Resources', href: '#', disabled: true },
  { name: 'Pricing', href: '/pricing', disabled: false },
  { name: 'FAQs', href: '/#faq', disabled: false },
];

// User menu items for authenticated users
const USER_MENU_ITEMS = [
  { name: 'Dashboard', href: '/team-workspace', icon: '📊' },
  { name: 'Profile', href: '/profile', icon: '👤' },
  { name: 'Settings', href: '/settings', icon: '⚙️' },
] as const;

const Navbar = () => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const mobileMenuRef = useRef<HTMLDivElement>(null);
  
  const pathname = usePathname();
  const router = useRouter();
  const user = useUser();
  const isAuthenticated = useIsAuthenticated();
  const isLoading = useIsLoading();
  const logOut = useLogout();

  // Close menus when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
      if (mobileMenuRef.current && !mobileMenuRef.current.contains(event.target as Node)) {
        setIsMobileMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close mobile menu on route change
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [pathname]);

  const handleLogout = async () => {
    try {
      await logOut();
      setIsUserMenuOpen(false);
      setIsMobileMenuOpen(false);
      router.push('/');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const handleFAQClick = () => {
    if (pathname !== '/') {
      // Navigate to home page first, then scroll to FAQ
      router.push('/#faq');
    } else {
      // Already on home page, just scroll to FAQ
      const faqSection = document.getElementById('faq-section');
      if (faqSection) {
        faqSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <header className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex-shrink-0">
              <div className="h-8 w-32 bg-gray-200 animate-pulse rounded"></div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="h-8 w-8 bg-gray-200 animate-pulse rounded-full"></div>
            </div>
          </div>
        </div>
      </header>
    );
  }

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-200 transition-all duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex-shrink-0">
            <Link href="/" className="flex items-center space-x-2 group">
              <Image
                src="/assets/Logo/yuba-logo-black.svg"
                alt="Yuba"
                width={32}
                height={32}
                className="h-8 w-auto transition-transform group-hover:scale-105"
                priority
              />
              <span className="text-xl font-bold text-gray-900 hidden sm:block">Yuba</span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-1">
            {NAV_LINKS.map((link) => {
              if (link.disabled) {
                return (
                  <span
                    key={link.name}
                    className="px-3 py-2 text-sm font-medium text-gray-400 cursor-not-allowed"
                  >
                    {link.name}
                  </span>
                );
              }

              if (link.name === 'FAQs') {
                return (
                  <button
                    key={link.name}
                    onClick={handleFAQClick}
                    className="px-3 py-2 text-sm font-medium text-gray-700 hover:text-[#128AA3] hover:bg-gray-50 rounded-md transition-colors"
                  >
                    {link.name}
                  </button>
                );
              }

              return (
                <Link
                  key={link.name}
                  href={link.href}
                  className="px-3 py-2 text-sm font-medium text-gray-700 hover:text-[#128AA3] hover:bg-gray-50 rounded-md transition-colors"
                >
                  {link.name}
                </Link>
              );
            })}
          </nav>

          {/* Desktop Auth Section */}
          <div className="hidden md:flex items-center space-x-4">
            {isAuthenticated ? (
              <div className="flex items-center space-x-3">
                <Link
                  href="/team-workspace"
                  className="flex items-center space-x-2 px-4 py-2 text-sm font-medium text-white bg-[#128AA3] hover:bg-[#0f6f82] rounded-md transition-colors shadow-sm"
                >
                  <span>📊</span>
                  <span>Dashboard</span>
                </Link>
                
                {/* User Avatar - Optional for profile access */}
                <div className="relative" ref={userMenuRef}>
                  <button
                    onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                    className="h-8 w-8 bg-gray-200 text-gray-700 rounded-full flex items-center justify-center text-sm font-semibold hover:bg-gray-300 transition-colors"
                    aria-expanded={isUserMenuOpen}
                    aria-haspopup="true"
                    title={user?.full_name || user?.email || 'User menu'}
                  >
                    {user?.full_name ? user.full_name.charAt(0).toUpperCase() : user?.email?.charAt(0).toUpperCase() || 'U'}
                  </button>

                  {/* Minimal User Dropdown */}
                  {isUserMenuOpen && (
                    <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                      <div className="px-4 py-3 border-b border-gray-100">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {user?.full_name || 'User'}
                        </p>
                        <p className="text-sm text-gray-500 truncate">{user?.email}</p>
                      </div>
                      
                      <Link
                        href="/profile"
                        className="flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                        onClick={() => setIsUserMenuOpen(false)}
                      >
                        <span>👤</span>
                        <span>Profile</span>
                      </Link>
                      
                      <Link
                        href="/settings"
                        className="flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                        onClick={() => setIsUserMenuOpen(false)}
                      >
                        <span>⚙️</span>
                        <span>Settings</span>
                      </Link>
                      
                      <div className="border-t border-gray-100 mt-1">
                        <button
                          onClick={handleLogout}
                          className="flex items-center space-x-3 w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                        >
                          <span>🚪</span>
                          <span>Sign Out</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex items-center space-x-3">
                <Link
                  href="/signin"
                  className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-[#128AA3] transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  href="/signup"
                  className="px-4 py-2 text-sm font-medium text-white bg-[#128AA3] hover:bg-[#0f6f82] rounded-md transition-colors shadow-sm"
                >
                  Get Started
                </Link>
              </div>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 text-gray-700 hover:text-[#128AA3] hover:bg-gray-50 rounded-md transition-colors"
              aria-expanded={isMobileMenuOpen}
              aria-label="Toggle menu"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {isMobileMenuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-gray-200 bg-white" ref={mobileMenuRef}>
            <div className="px-2 pt-2 pb-3 space-y-1">
              {/* Mobile Navigation Links */}
              {NAV_LINKS.map((link) => {
                if (link.disabled) {
                  return (
                    <span
                      key={link.name}
                      className="block px-3 py-2 text-base font-medium text-gray-400 cursor-not-allowed"
                    >
                      {link.name}
                    </span>
                  );
                }

                if (link.name === 'FAQs') {
                  return (
                    <button
                      key={link.name}
                      onClick={() => {
                        handleFAQClick();
                        setIsMobileMenuOpen(false);
                      }}
                      className="block w-full text-left px-3 py-2 text-base font-medium text-gray-700 hover:text-[#128AA3] hover:bg-gray-50 rounded-md transition-colors"
                    >
                      {link.name}
                    </button>
                  );
                }

                return (
                  <Link
                    key={link.name}
                    href={link.href}
                    className="block px-3 py-2 text-base font-medium text-gray-700 hover:text-[#128AA3] hover:bg-gray-50 rounded-md transition-colors"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    {link.name}
                  </Link>
                );
              })}

              {/* Mobile Auth Section */}
              {isAuthenticated ? (
                <div className="border-t border-gray-200 pt-4 mt-4">
                  {/* Dashboard Link */}
                  <Link
                    href="/team-workspace"
                    className="flex items-center space-x-3 px-3 py-2 mb-3 text-base font-medium text-white bg-[#128AA3] hover:bg-[#0f6f82] rounded-md transition-colors"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    <span>📊</span>
                    <span>Dashboard</span>
                  </Link>
                  
                  {/* User Info */}
                  <div className="flex items-center space-x-3 px-3 py-2 mb-3 bg-gray-50 rounded-md">
                    <div className="h-10 w-10 bg-gray-200 text-gray-700 rounded-full flex items-center justify-center font-semibold">
                      {user?.full_name ? user.full_name.charAt(0).toUpperCase() : user?.email?.charAt(0).toUpperCase() || 'U'}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {user?.full_name || 'User'}
                      </p>
                      <p className="text-sm text-gray-500 truncate">{user?.email}</p>
                    </div>
                  </div>
                  
                  {/* Secondary Actions */}
                  <Link
                    href="/profile"
                    className="flex items-center space-x-3 px-3 py-2 text-base font-medium text-gray-700 hover:text-[#128AA3] hover:bg-gray-50 rounded-md transition-colors"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    <span>👤</span>
                    <span>Profile</span>
                  </Link>
                  
                  <Link
                    href="/settings"
                    className="flex items-center space-x-3 px-3 py-2 text-base font-medium text-gray-700 hover:text-[#128AA3] hover:bg-gray-50 rounded-md transition-colors"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    <span>⚙️</span>
                    <span>Settings</span>
                  </Link>
                  
                  <button
                    onClick={handleLogout}
                    className="flex items-center space-x-3 w-full px-3 py-2 text-base font-medium text-red-600 hover:bg-red-50 rounded-md transition-colors mt-2"
                  >
                    <span>🚪</span>
                    <span>Sign Out</span>
                  </button>
                </div>
              ) : (
                <div className="border-t border-gray-200 pt-4 mt-4 space-y-2">
                  <Link
                    href="/signin"
                    className="block w-full px-3 py-2 text-base font-medium text-center text-gray-700 hover:text-[#128AA3] border border-gray-300 hover:border-[#128AA3] rounded-md transition-colors"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    Sign In
                  </Link>
                  <Link
                    href="/signup"
                    className="block w-full px-3 py-2 text-base font-medium text-center text-white bg-[#128AA3] hover:bg-[#0f6f82] rounded-md transition-colors"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    Get Started
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </header>
  );
};

export default Navbar;