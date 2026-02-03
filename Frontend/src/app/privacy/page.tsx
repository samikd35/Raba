"use client";

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, FileText, Printer } from 'lucide-react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import Image from 'next/image';

interface Section {
  id: string;
  title: string;
  number?: string;
}

const sections: Section[] = [
  { id: 'introduction', title: 'Introduction', number: '1' },
  { id: 'scope', title: 'Scope of This Policy', number: '2' },
  { id: 'data-collection', title: 'Data We Collect', number: '3' },
  { id: 'data-usage', title: 'How We Use Your Data', number: '4' },
  { id: 'legal-bases', title: 'Legal Bases for Processing', number: '5' },
  { id: 'data-sharing', title: 'Sharing and Disclosure of Data', number: '6' },
  { id: 'international-transfers', title: 'International Data Transfers', number: '7' },
  { id: 'data-retention', title: 'Data Retention', number: '8' },
  { id: 'your-rights', title: 'Your Rights and Choices', number: '9' },
  { id: 'security', title: 'Security', number: '10' },
  { id: 'childrens-privacy', title: "Children's Privacy", number: '11' },
  { id: 'third-party', title: 'Third-Party Sites and Services', number: '12' },
  { id: 'google-apis', title: 'Google API Services Disclosure', number: '13' },
  { id: 'changes', title: 'Changes to This Privacy Policy', number: '14' },
  { id: 'contact', title: 'Contact Us', number: '15' },
];

export default function PrivacyPolicyPage() {
  const [activeSection, setActiveSection] = useState('introduction');
  const [isNavExpanded, setIsNavExpanded] = useState(true);
  const [isPrintView, setIsPrintView] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const mainRef = useRef<HTMLElement>(null);
  const sectionRefs = useRef<{ [key: string]: HTMLElement }>({});
  const isScrollingRef = useRef(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const savedTheme = localStorage.getItem('yuba-privacy-theme');
    if (savedTheme) {
      setIsDarkMode(savedTheme === 'dark');
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setIsDarkMode(prefersDark);
    }
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    setPrefersReducedMotion(reducedMotion);
  }, []);

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  useEffect(() => {
    const print = searchParams?.get('print');
    if (print === '1') {
      setIsPrintView(true);
    }
  }, [searchParams]);

  useEffect(() => {
    if (isPrintView) {
      setTimeout(() => window.print(), 100);
    }
  }, [isPrintView]);

  useEffect(() => {
    if (isPrintView || !mainRef.current) return;

    const scrollContainer = mainRef.current;
    
    const observerOptions: IntersectionObserverInit = {
      root: scrollContainer,
      rootMargin: '-48px 0px -70% 0px',
      threshold: 0
    };

    const observerCallback = (entries: IntersectionObserverEntry[]) => {
      if (isScrollingRef.current) return;
      
      const visibleEntries = entries.filter(entry => entry.isIntersecting);
      if (visibleEntries.length === 0) return;
      
      const sortedEntries = visibleEntries.sort((a, b) => {
        return a.boundingClientRect.top - b.boundingClientRect.top;
      });
      
      const topEntry = sortedEntries[0];
      const sectionId = topEntry.target.id;
      
      setActiveSection(sectionId);
      if (window.location.hash !== `#${sectionId}`) {
        window.history.replaceState(null, '', `#${sectionId}`);
      }
    };

    const observer = new IntersectionObserver(observerCallback, observerOptions);

    Object.values(sectionRefs.current).forEach((element) => {
      if (element) observer.observe(element);
    });

    return () => observer.disconnect();
  }, [isPrintView]);

  useEffect(() => {
    if (typeof window !== 'undefined' && window.location.hash) {
      const hash = window.location.hash.substring(1);
      setTimeout(() => scrollToSection(hash), 300);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const scrollToSection = (sectionId: string) => {
    const element = sectionRefs.current[sectionId];
    const scrollContainer = mainRef.current;
    
    if (element && scrollContainer) {
      isScrollingRef.current = true;
      setActiveSection(sectionId);
      
      const containerRect = scrollContainer.getBoundingClientRect();
      const elementRect = element.getBoundingClientRect();
      const offset = 48;
      const scrollTop = scrollContainer.scrollTop + (elementRect.top - containerRect.top) - offset;
      
      if (prefersReducedMotion) {
        scrollContainer.scrollTop = scrollTop;
        isScrollingRef.current = false;
      } else {
        scrollContainer.scrollTo({ top: scrollTop, behavior: 'smooth' });
        setTimeout(() => {
          isScrollingRef.current = false;
        }, 500);
      }
      
      window.history.pushState(null, '', `#${sectionId}`);
    }
  };

  const handlePrintVersion = () => {
    router.push('/privacy?print=1');
  };

  if (isPrintView) {
    return (
      <div className="max-w-4xl mx-auto p-8 bg-white text-black print:p-0">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Yuba Privacy Policy</h1>
          <p className="text-sm text-gray-600">Effective January 1, 2026</p>
        </div>
        <PrintContent sectionRefs={sectionRefs} />
      </div>
    );
  }

  return (
    <div className={`flex h-screen overflow-hidden transition-colors duration-200 ${isDarkMode ? 'bg-gray-900' : 'bg-white'}`}>
      <aside className={`w-80 flex flex-col overflow-hidden transition-colors duration-200 ${
        isDarkMode ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-50'
      }`}>
        <div className={`px-8 pt-6 pb-3 border-b transition-colors duration-200 ${
          isDarkMode ? 'border-gray-700' : 'border-gray-200'
        }`}>
          <Link href="/" className="flex items-center gap-3 mb-2 group">
            <div className="relative ">
              <Image
                src="/images/logo/yuba-logo-black.png"
                alt="Yuba"
                width={90}
                height={90}
                className={`transition-opacity duration-200 ${isDarkMode ? 'opacity-0 absolute' : 'opacity-100'}`}
              />
            </div>
          </Link>
        </div>

        <div className="flex-1 overflow-y-auto">
          <div className="p-4">
            <button
              onClick={() => setIsNavExpanded(!isNavExpanded)}
              className={`w-full flex items-center justify-between p-3 rounded-lg transition-colors mb-2 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${
                isDarkMode ? 'hover:bg-gray-700 focus:ring-offset-gray-800' : 'hover:bg-gray-100 focus:ring-offset-gray-50'
              }`}
              aria-expanded={isNavExpanded}
              aria-controls="privacy-nav"
            >
              <div className="flex items-center gap-2">
                <span className={`text-lg font-medium transition-colors duration-200 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>The Privacy Policy</span>
              </div>
              {isNavExpanded ? (
                <ChevronUp className={`w-4 h-4 transition-colors duration-200 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`} />
              ) : (
                <ChevronDown className={`w-4 h-4 transition-colors duration-200 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`} />
              )}
            </button>

            <AnimatePresence>
              {isNavExpanded && (
                <motion.nav
                  id="privacy-nav"
                  initial={prefersReducedMotion ? {} : { height: 0, opacity: 0 }}
                  animate={prefersReducedMotion ? {} : { height: 'auto', opacity: 1 }}
                  exit={prefersReducedMotion ? {} : { height: 0, opacity: 0 }}
                  transition={{ duration: prefersReducedMotion ? 0 : 0.2 }}
                  className="overflow-hidden"
                  role="navigation"
                  aria-label="Privacy policy sections"
                >
                  <ul className="space-y-1">
                    {sections.map((section) => (
                      <li key={section.id}>
                        <button
                          onClick={() => scrollToSection(section.id)}
                          className={`w-full text-left px-3 py-2 text-sm transition-all duration-200 relative focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 ${
                            activeSection === section.id
                              ? isDarkMode ? 'text-brand-400 bg-current/5' : 'text-brand-500 bg-current/5'
                              : isDarkMode ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-700 hover:bg-gray-100'
                          } ${isDarkMode ? 'focus-visible:ring-offset-gray-800' : 'focus-visible:ring-offset-gray-50'}`}
                          aria-current={activeSection === section.id ? 'location' : undefined}
                          tabIndex={0}
                        >
                          {activeSection === section.id && (
                            <motion.div 
                              layoutId="activeIndicator"
                              className="absolute left-0 top-0 bottom-0 w-[3px] bg-brand-500"
                              initial={prefersReducedMotion ? {} : { opacity: 0 }}
                              animate={prefersReducedMotion ? {} : { opacity: 1 }}
                              transition={{ duration: prefersReducedMotion ? 0 : 0.15 }}
                            />
                          )}
                          <span className="pl-2">
                            {section.number ? `${section.number}. ` : ''}
                            {section.title}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </motion.nav>
              )}
            </AnimatePresence>
          </div>
        </div>
      </aside>

      <main ref={mainRef} className={`flex-1 overflow-y-auto transition-colors duration-200 ${isDarkMode ? 'bg-gray-900' : 'bg-white'}`}>
        <div className="max-w-4xl mx-auto px-12 py-12" ref={contentRef}>
          <div className="mb-8">
            <h1 className={`text-4xl font-bold mb-6 transition-colors duration-200 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>Yuba Privacy Policy</h1>
            
            <div className={`flex items-center gap-2 text-sm mb-8 transition-colors duration-200 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              <span>Effective January 2026</span>
              <span className={isDarkMode ? 'text-gray-600' : 'text-gray-400'}>|</span>
              <button
                onClick={handlePrintVersion}
                className="text-brand-500 hover:underline flex items-center gap-1 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 rounded transition-all"
                aria-label="View printable version"
              >
                <Printer className="w-3.5 h-3.5" />
                View printable version
              </button>
            </div>

            <PolicyContent sectionRefs={sectionRefs} isDarkMode={isDarkMode} />
          </div>
        </div>
      </main>
    </div>
  );
}

function PolicyContent({ sectionRefs, isDarkMode }: { sectionRefs: React.MutableRefObject<{ [key: string]: HTMLElement }>; isDarkMode: boolean }) {
  const h2Class = `text-2xl font-semibold mb-4 transition-colors duration-200 ${isDarkMode ? 'text-white' : 'text-gray-900'}`;
  const h3Class = `text-lg font-semibold mb-3 transition-colors duration-200 ${isDarkMode ? 'text-gray-100' : 'text-gray-900'}`;
  const textClass = `space-y-4 leading-relaxed transition-colors duration-200 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`;
  const linkClass = 'text-brand-500 hover:underline focus:outline-none focus:ring-2 focus:ring-brand-500 rounded';
  const codeClass = `font-mono text-sm px-2 py-1 rounded transition-colors duration-200 ${isDarkMode ? 'bg-gray-800 text-gray-300' : 'bg-gray-100 text-gray-800'}`;

  return (
    <>
      <section ref={(el) => { if (el) sectionRefs.current['introduction'] = el; }} id="introduction" className="mb-12">
        <h2 className={h2Class}>1. Introduction</h2>
        <div className={textClass}>
          <p>
            This Privacy Policy explains how Yuba ("Yuba", "we", "our", or "us") collects, uses, discloses, and protects personal data when you use our products and services. Yuba is developed and operated by Yuba Holdings Inc., based in Delaware, USA.
          </p>
          <p>
            By accessing or using Yuba, you agree to this Privacy Policy. If you do not agree, you should not use our services.
          </p>
          <p>
            If you have any questions, you can contact us at:{' '}
            <a href="mailto:info@yubanow.com" className={linkClass}>info@yubanow.com</a>.
          </p>
        </div>
      </section>

      <section ref={(el) => { if (el) sectionRefs.current['scope'] = el; }} id="scope" className="mb-12">
        <h2 className={h2Class}>2. Scope of This Policy</h2>
        <div className={textClass}>
          <p>This Privacy Policy applies to personal data that we process when you:</p>
          <ul className="list-disc pl-6 space-y-2">
            <li>Create or access a Yuba account.</li>
            <li>Use any Yuba module (including Problem Discovery, Value Proposition Design, Business Model & MVP Design, and Market Validation).</li>
            <li>Use the Venture Builder (VB) features, including viewing VB profiles, booking sessions, and attending coaching sessions.</li>
            <li>Use co-founder matching, team or organization workspaces, and other ecosystem features.</li>
            <li>Use the Google sign-in and Google Calendar integration.</li>
            <li>Interact with us via email, in-product messaging, or support.</li>
          </ul>
          <p>
            This Privacy Policy does not apply to websites, applications, or services that we do not control. However, when we integrate with third-party services (such as Google, payment providers, or AI infrastructure providers), this Policy explains how we send data to and receive data from those services.
          </p>
        </div>
      </section>

      <section ref={(el) => { if (el) sectionRefs.current['data-collection'] = el; }} id="data-collection" className="mb-12">
        <h2 className={h2Class}>3. Data We Collect</h2>
        <div className={`space-y-6 leading-relaxed transition-colors duration-200 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          <p>We collect different types of personal data depending on how you use Yuba.</p>
          
          <div>
            <h3 className={h3Class}>3.1 Account and Identity Data</h3>
            <p className="mb-2">When you create an account or are invited into a workspace, we may collect:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Name and surname.</li>
              <li>Email address.</li>
              <li>Password or authentication credentials (or a third-party login identifier if SSO is enabled).</li>
              <li>Profile image or avatar (if you choose to upload one).</li>
              <li>Country, city, or region (if provided).</li>
            </ul>
            <p className="mt-3">When you use Google sign-in, we may additionally receive from Google:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Your primary Google Account email address.</li>
              <li>A basic identifier that allows us to associate your Yuba account with your Google account.</li>
            </ul>
            <p className="mt-2">These are provided under the scopes:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li><code className={codeClass}>openid</code></li>
              <li><code className={codeClass}>https://www.googleapis.com/auth/userinfo.email</code></li>
            </ul>
          </div>

          <div>
            <h3 className={h3Class}>3.2 Workspace, Team, and Organization Data</h3>
            <p className="mb-2">For workspaces (independent users, teams, organizations), we may collect:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Workspace / organization name.</li>
              <li>Workspace type (e.g., individual, team, accelerator, university, ESO).</li>
              <li>Role and permissions (e.g., organization admin, team admin, member).</li>
              <li>List of members and invited users.</li>
            </ul>
            <p className="mt-2">Organization and team admins may be able to see certain usage and activity data of members within their workspace, as described below.</p>
          </div>

          <div>
            <h3 className={h3Class}>3.3 Venture Builder Profile Data</h3>
            <p className="mb-2">If you register as a Venture Builder, we may collect:</p>
            <p className="mb-2">Professional profile information, such as:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Name, photo, title, biography.</li>
              <li>Areas of expertise and sectors of focus.</li>
              <li>Experience, languages, country/region.</li>
              <li>Availability preferences and time zone.</li>
              <li>Public rate information (e.g., how many credits per hour a session costs).</li>
              <li>Links to external profiles (e.g., LinkedIn) if you choose to share them.</li>
            </ul>
            <p className="mt-2">Some VB profile fields may be visible to users when you appear in the directory.</p>
          </div>

          <div>
            <h3 className={h3Class}>3.4 Project and Content Data</h3>
            <p className="mb-2">When you use Yuba's modules, you may provide:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Problem descriptions, opportunity statements, and user personas.</li>
              <li>Market research inputs, competitor information, and assumptions.</li>
              <li>Value propositions, business model components, MVP scopes, and experiment plans.</li>
              <li>Uploads or pasted content (e.g., text from documents, links, or summaries).</li>
              <li>Responses to guided questionnaires and forms.</li>
            </ul>
            <p className="mt-2">This content may be processed by our Agentic System to generate outputs such as structured reports, recommendations, and summaries. We store this content securely and associate it with your account, project, and workspace.</p>
          </div>

          <div>
            <h3 className={h3Class}>3.5 Session and Scheduling Data</h3>
            <p className="mb-2">For the Venture Builder scheduling feature, we collect:</p>
            <p className="mb-2">Session booking details, including:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Venture Builder involved.</li>
              <li>Project linked to the session.</li>
              <li>Time and date of the session.</li>
              <li>Duration and status (pending, booked, completed, cancelled).</li>
              <li>Credits spent and billing context.</li>
            </ul>
            <p className="mt-2">Meeting agenda and notes:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Agenda text that founders provide when booking sessions.</li>
              <li>Optional notes a VB may add in their own workspace.</li>
            </ul>
            <p className="mt-2">We use this data to schedule and manage sessions, and to show relevant information to the founder, the VB, and relevant admins (e.g., organization admins) according to your workspace's access rules.</p>
          </div>

          <div>
            <h3 className={h3Class}>3.6 Google Calendar Data (Venture Builder Integration)</h3>
            <p className="mb-2">
              If you are a Venture Builder and you choose to connect your Google Calendar, we will access certain data from your Google account using the following scope:
            </p>
            <p className="mb-2">
              <code className={codeClass}>https://www.googleapis.com/auth/calendar.events</code> – "View and edit events on all of your calendars."
            </p>
            <p className="mb-2">Using this scope, our application may access:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Basic information about the calendars that support events for your account (such as identifiers and time zone), to the extent required to create and manage Yuba-related events.</li>
            </ul>
            <p className="mt-2">Event data related to Yuba-created coaching sessions, including:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Start time, end time, and time zone.</li>
              <li>Attendee email addresses (e.g., you and the founder).</li>
              <li>Event identifiers needed to update or cancel the event.</li>
              <li>The text we place into the event (such as the session title and agenda you or the founder provided in Yuba).</li>
            </ul>
            <p className="mt-2">Availability / conflict information:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>We use Google Calendar to check for busy periods in order to avoid double-booking.</li>
              <li>Our implementation is designed to use free/busy information for conflict checking and not to read or store the titles, descriptions, or attachments of events that were not created by Yuba.</li>
            </ul>
            <p className="mt-2">We also store:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>OAuth tokens (access token, refresh token, expiry time) to keep your calendar connection active.</li>
            </ul>
            <p className="mt-3 font-semibold">We do not:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Store your Google password.</li>
              <li>Sell Google Calendar data.</li>
              <li>Use Google Calendar data to build advertising profiles.</li>
            </ul>
            <p className="mt-2">You can revoke Yuba's access at any time via your Google Account settings. If you revoke access, Yuba's scheduling features for that calendar may stop working until you reconnect.</p>
          </div>

          <div>
            <h3 className={h3Class}>3.7 Payment and Credits Data</h3>
            <p className="mb-2">When you purchase credits or use paid features, we collect and process:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Basic billing information (e.g., name, email, organization details).</li>
              <li>Transaction details (amount, currency, date, payment method type).</li>
            </ul>
            <p className="mt-2">Credit usage history:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Credits allocated to your workspace.</li>
              <li>Which features or sessions consumed credits.</li>
            </ul>
            <p className="mt-2">Sensitive payment data such as full card details are typically processed by third-party payment providers, not stored by Yuba directly.</p>
          </div>

          <div>
            <h3 className={h3Class}>3.8 Technical and Usage Data</h3>
            <p className="mb-2">When you use Yuba, we may collect:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Device and browser information (e.g., browser type and version, operating system, screen resolution).</li>
              <li>IP address and approximate location (city-level) to help with security, fraud prevention, and localization.</li>
            </ul>
            <p className="mt-2">Log data such as:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Pages and screens viewed.</li>
              <li>Buttons and features used.</li>
              <li>Timestamps and session duration.</li>
              <li>Error and performance data (e.g., crash logs, API error responses).</li>
            </ul>
            <p className="mt-2">This helps us improve reliability, diagnose issues, and understand how Yuba is used.</p>
          </div>

          <div>
            <h3 className={h3Class}>3.9 Cookies and Similar Technologies</h3>
            <p className="mb-2">We may use cookies and similar technologies to:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Keep you logged in and maintain session state.</li>
              <li>Remember your preferences (e.g., language, active workspace).</li>
              <li>Measure product usage and improve the user experience.</li>
            </ul>
            <p className="mt-2">Where legally required, we will present a cookie notice and/or consent banner.</p>
          </div>

          <div>
            <h3 className={h3Class}>3.10 Communications Data</h3>
            <p className="mb-2">If you contact us via email, in-product chat, or other channels, we collect:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Your contact details (e.g., email address).</li>
              <li>Content of your messages and any attachments.</li>
              <li>Metadata such as timestamps and support ticket status.</li>
            </ul>
            <p className="mt-2">We use this data to respond to inquiries, provide support, and improve our services.</p>
          </div>
        </div>
      </section>

      <section ref={(el) => { if (el) sectionRefs.current['data-usage'] = el; }} id="data-usage" className="mb-12">
        <h2 className={h2Class}>4. How We Use Your Data</h2>
        <div className={`space-y-6 leading-relaxed transition-colors duration-200 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          <p>We use personal data for the following purposes:</p>
          
          <div>
            <h3 className={h3Class}>4.1 To Provide and Improve Yuba</h3>
            <ul className="list-disc pl-6 space-y-1">
              <li>Create and manage user accounts and workspaces.</li>
              <li>Provide modules such as Problem Discovery, Value Proposition Design, Business Model & MVP Design, and Market Validation.</li>
              <li>Powerful agentic features that analyze your inputs and generate structured outputs, recommendations, and reports.</li>
              <li>Enable Venture Builder profiles, discovery, and booking.</li>
              <li>Provide scheduling functionality, including calendar connections, availability computation, and session management.</li>
              <li>Track credit balances and apply credit deductions for usage.</li>
              <li>Diagnose and fix bugs, improve user experience, and add new features.</li>
            </ul>
          </div>

          <div>
            <h3 className={h3Class}>4.2 To Facilitate Collaboration and Ecosystem Features</h3>
            <ul className="list-disc pl-6 space-y-1">
              <li>Share project information with Venture Builders only where you explicitly select the project for a session or where your workspace/admin has configured sharing rules.</li>
              <li>Allow teams and organizations to work collaboratively on projects and see shared content.</li>
              <li>Provide co-founder matching or other ecosystem features where applicable.</li>
            </ul>
          </div>

          <div>
            <h3 className={h3Class}>4.3 To Communicate With You</h3>
            <ul className="list-disc pl-6 space-y-1">
              <li>Send transactional emails and notifications (e.g., account creation, password resets, session bookings, reschedule links, credit usage notifications).</li>
              <li>Send administrative updates about changes to our terms, policies, or platform features.</li>
              <li>Where permitted, send relevant product updates or educational content about using Yuba.</li>
            </ul>
            <p className="mt-2">You can opt out of non-essential communications at any time using unsubscribe links or notification settings.</p>
          </div>

          <div>
            <h3 className={h3Class}>4.4 To Ensure Security and Prevent Abuse</h3>
            <ul className="list-disc pl-6 space-y-1">
              <li>Detect and prevent fraud, abuse, or security incidents.</li>
              <li>Verify account ownership where necessary.</li>
              <li>Monitor for unusual activity that could indicate unauthorized access.</li>
            </ul>
          </div>

          <div>
            <h3 className={h3Class}>4.5 To Comply With Legal Obligations</h3>
            <ul className="list-disc pl-6 space-y-1">
              <li>Maintain business and financial records.</li>
              <li>Respond to lawful requests by public authorities.</li>
              <li>Enforce our terms of use and other agreements.</li>
            </ul>
          </div>

          <div>
            <h3 className={h3Class}>4.6 For Analytics and Product Development</h3>
            <ul className="list-disc pl-6 space-y-1">
              <li>Analyze aggregate usage patterns (e.g., which modules are used most, typical flows across features).</li>
              <li>Measure performance and reliability.</li>
              <li>Develop new features and services based on anonymized or pseudonymized data where possible.</li>
            </ul>
            <p className="mt-2">We strive to use de-identified or aggregated data whenever feasible for analytics and product development.</p>
          </div>
        </div>
      </section>

      <section ref={(el) => { if (el) sectionRefs.current['legal-bases'] = el; }} id="legal-bases" className="mb-12">
        <h2 className={h2Class}>5. Legal Bases for Processing (When Applicable)</h2>
        <div className={textClass}>
          <p>Where the EU/EEA, UK, or similar data protection laws apply, we rely on the following legal bases:</p>
          <ul className="list-disc pl-6 space-y-2 mt-3">
            <li><strong>Performance of a contract:</strong> Processing necessary to provide our services to you, including account management, project processing, and scheduling.</li>
            <li><strong>Legitimate interests:</strong> For analytics, product development, security, fraud prevention, and improving the user experience, provided these interests are not overridden by your rights.</li>
            <li><strong>Consent:</strong> Where we rely on your consent (for example, for certain cookies, marketing communications, or specific third-party integrations).</li>
            <li><strong>Legal obligations:</strong> Where processing is necessary to comply with applicable laws.</li>
          </ul>
        </div>
      </section>

      <section ref={(el) => { if (el) sectionRefs.current['data-sharing'] = el; }} id="data-sharing" className="mb-12">
        <h2 className={h2Class}>6. Sharing and Disclosure of Data</h2>
        <div className={`space-y-6 leading-relaxed transition-colors duration-200 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          <p className="font-semibold">We do not sell your personal data.</p>
          <p>We may share data in the following situations:</p>
          
          <div>
            <h3 className={h3Class}>6.1 Within Your Workspace and Projects</h3>
            <ul className="list-disc pl-6 space-y-1">
              <li>Data you add to a workspace can be visible to other members of that workspace according to the roles and permissions set by your organization or team.</li>
              <li>Project content linked to a Venture Builder session is shared with that VB so they can prepare and deliver the session, in accordance with your selections.</li>
            </ul>
          </div>

          <div>
            <h3 className={h3Class}>6.2 With Venture Builders</h3>
            <p className="mb-2">When you book a session with a VB:</p>
            <p className="mb-2">The VB can see:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Basic information needed to run the session (e.g., your name, project name, project ID reference, session time, and agenda).</li>
              <li>Any project context explicitly shared for the session.</li>
            </ul>
            <p className="mt-2">Venture Builders are independent professionals or partners and may have their own privacy obligations. However, they must use your data only for the purpose of providing coaching or related services in Yuba.</p>
          </div>

          <div>
            <h3 className={h3Class}>6.3 With Workspace and Organization Admins</h3>
            <p className="mb-2">Admins may be able to see high-level usage information, such as:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Which users in their workspace are using Yuba.</li>
              <li>Credit allocations and usage.</li>
              <li>Which projects and sessions are associated with their organization.</li>
            </ul>
            <p className="mt-2">They should not have unrestricted access to all personal data, but they may access relevant data for managing the workspace.</p>
          </div>

          <div>
            <h3 className={h3Class}>6.4 With Service Providers</h3>
            <p className="mb-2">We use third-party service providers to help operate Yuba, such as:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Cloud hosting providers.</li>
              <li>Database and storage providers.</li>
              <li>Email and notification services.</li>
              <li>Payment processors.</li>
              <li>Analytics and monitoring tools.</li>
              <li>AI infrastructure providers.</li>
            </ul>
            <p className="mt-2">These providers process data only on our instructions and under appropriate contractual safeguards.</p>
          </div>

          <div>
            <h3 className={h3Class}>6.5 AI and Model Providers</h3>
            <p className="mb-2">To deliver AI-powered features (such as generating reports, structuring content, or summarizing your inputs), we may send certain project and content data to large language model providers under strict terms.</p>
            <p className="mt-2">Google user data obtained via Google APIs (including Google Calendar event data, tokens, and identifiers) is not used to train or improve general-purpose AI models and is not provided to external AI model providers, except where it is strictly necessary to provide a user-visible feature you have requested and is consistent with Google's policies. Our current implementation does not send Google Calendar data to external AI providers.</p>
            <p className="mt-2">When we send non-Google data to AI infrastructure providers, we:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Use secure channels.</li>
              <li>Limit data to what is necessary for the requested feature.</li>
              <li>Contractually restrict providers from using your data to train models for other customers or for their own advertising.</li>
            </ul>
          </div>

          <div>
            <h3 className={h3Class}>6.6 Legal and Compliance</h3>
            <p className="mb-2">We may disclose data to third parties:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>To comply with legal processes or enforceable governmental requests.</li>
              <li>To enforce our terms of use or investigate potential violations.</li>
              <li>To protect the rights, property, or safety of Yuba, our users, or the public.</li>
            </ul>
          </div>

          <div>
            <h3 className={h3Class}>6.7 Business Transfers</h3>
            <p>If we are involved in a merger, acquisition, financing, or sale of assets, your personal data may be transferred as part of that transaction, subject to continuity of protections consistent with this Privacy Policy.</p>
          </div>
        </div>
      </section>

      <section ref={(el) => { if (el) sectionRefs.current['international-transfers'] = el; }} id="international-transfers" className="mb-12">
        <h2 className={h2Class}>7. International Data Transfers</h2>
        <div className={textClass}>
          <p>
            Our infrastructure or service providers may be located in different countries. As a result, your personal data may be transferred to and processed in countries outside of your country of residence.
          </p>
          <p>
            Where required by law, we will implement appropriate safeguards (such as standard contractual clauses) to protect personal data transferred across borders.
          </p>
        </div>
      </section>

      <section ref={(el) => { if (el) sectionRefs.current['data-retention'] = el; }} id="data-retention" className="mb-12">
        <h2 className={h2Class}>8. Data Retention</h2>
        <div className={textClass}>
          <p>We retain personal data for as long as necessary to:</p>
          <ul className="list-disc pl-6 space-y-2 mt-3">
            <li>Provide the services you use.</li>
            <li>Support legitimate business purposes (e.g., accounting, analytics, security).</li>
            <li>Comply with legal obligations.</li>
          </ul>
          <p className="mt-4">In general:</p>
          <ul className="list-disc pl-6 space-y-2">
            <li>Account and workspace data are retained while your account or workspace is active.</li>
            <li>Project and content data are retained while the workspace is active, unless you delete them.</li>
            <li>Session and credit ledger data may be retained for longer periods as part of business and financial records.</li>
            <li>Google Calendar access and refresh tokens are retained while your Google Calendar connection is active. When you disconnect your calendar from Yuba or revoke access via Google, we delete the stored tokens from our active systems as soon as reasonably practicable, and in any case within a commercially reasonable period. Tokens may remain in encrypted backups for a limited retention period, after which backups are rotated and old data is deleted. Tokens in backups are not used for any active processing.</li>
          </ul>
          <p className="mt-4">We may anonymize or aggregate data so that it can no longer be linked to individuals. We may retain such data for longer periods for analytics and product improvement.</p>
        </div>
      </section>

      <section ref={(el) => { if (el) sectionRefs.current['your-rights'] = el; }} id="your-rights" className="mb-12">
        <h2 className={h2Class}>9. Your Rights and Choices</h2>
        <div className={textClass}>
          <p>Depending on your location and applicable law, you may have the following rights:</p>
          <ul className="list-disc pl-6 space-y-2 mt-3">
            <li><strong>Access:</strong> Request a copy of the personal data we hold about you.</li>
            <li><strong>Rectification:</strong> Ask us to correct inaccurate or incomplete data.</li>
            <li><strong>Deletion:</strong> Request deletion of your personal data in certain circumstances.</li>
            <li><strong>Restriction:</strong> Request that we restrict processing in certain situations.</li>
            <li><strong>Portability:</strong> Receive your data in a structured, commonly used format or ask us to transfer it to another service where technically feasible.</li>
            <li><strong>Objection:</strong> Object to certain types of processing (e.g., direct marketing or processing based on legitimate interests).</li>
            <li><strong>Withdraw consent:</strong> Where processing is based on consent, you can withdraw your consent at any time.</li>
          </ul>
          <p className="mt-4">
            To exercise your rights, you can contact us at{' '}
            <a href="mailto:info@yubanow.com" className={linkClass}>info@yubanow.com</a>. We may need to verify your identity before acting on your request.
          </p>
          <p>You also have the right to lodge a complaint with a data protection authority, where applicable.</p>
        </div>
      </section>

      <section ref={(el) => { if (el) sectionRefs.current['security'] = el; }} id="security" className="mb-12">
        <h2 className={h2Class}>10. Security</h2>
        <div className={textClass}>
          <p>We take reasonable and appropriate technical and organizational measures to protect personal data, including:</p>
          <ul className="list-disc pl-6 space-y-2 mt-3">
            <li>Encryption in transit (e.g., HTTPS / TLS) and, where appropriate, at rest.</li>
            <li>Access controls and role-based permissions.</li>
            <li>Regular backups and disaster recovery planning.</li>
            <li>Logging and monitoring for suspicious activity.</li>
          </ul>
          <p className="mt-4">For sensitive items such as Google OAuth tokens, we:</p>
          <ul className="list-disc pl-6 space-y-2">
            <li>Store tokens in restricted systems with access limited to necessary services.</li>
            <li>Encrypt tokens at rest.</li>
            <li>Use secure communication channels when exchanging tokens with Google.</li>
          </ul>
          <p className="mt-4">
            However, no system is completely secure. We cannot guarantee absolute security of your data. You are responsible for choosing a strong password and keeping your login credentials confidential.
          </p>
        </div>
      </section>

      <section ref={(el) => { if (el) sectionRefs.current['childrens-privacy'] = el; }} id="childrens-privacy" className="mb-12">
        <h2 className={h2Class}>11. Children's Privacy</h2>
        <div className={textClass}>
          <p>
            Yuba is not directed to children under the age of 16 (or the age required by local law). We do not knowingly collect personal data from children under this age. If we become aware that we have collected such data, we will take steps to delete it.
          </p>
          <p>
            If you believe that a child has provided us with personal data, please contact us at{' '}
            <a href="mailto:info@yubanow.com" className={linkClass}>info@yubanow.com</a>.
          </p>
        </div>
      </section>

      <section ref={(el) => { if (el) sectionRefs.current['third-party'] = el; }} id="third-party" className="mb-12">
        <h2 className={h2Class}>12. Third-Party Sites and Services</h2>
        <div className={textClass}>
          <p>Yuba may contain links to or integrate with third-party websites or services, including:</p>
          <ul className="list-disc pl-6 space-y-2 mt-3">
            <li>External learning resources.</li>
            <li>Services used by accelerators, incubators, or universities.</li>
            <li>Third-party payment or communication services.</li>
            <li>Google services such as Google Sign-In and Google Calendar.</li>
          </ul>
          <p className="mt-4">
            When you connect such services or follow links, your use of those third-party services is governed by their own terms and privacy policies. However, this Privacy Policy still explains how we handle any personal data that passes between Yuba and those services.
          </p>
        </div>
      </section>

      <section ref={(el) => { if (el) sectionRefs.current['google-apis'] = el; }} id="google-apis" className="mb-12">
        <h2 className={h2Class}>13. Additional Disclosure for Google API Services (Google Sign-In and Google Calendar)</h2>
        <div className={`space-y-6 leading-relaxed transition-colors duration-200 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          <p>
            Yuba's use of information received from Google APIs will adhere to the{' '}
            <a
              href="https://developers.google.com/terms/api-services-user-data-policy"
              target="_blank"
              rel="noopener noreferrer"
              className={linkClass}
            >
              Google API Services User Data Policy
            </a>
            , including the Limited Use requirements.
          </p>
          <p>In particular:</p>
          
          <div>
            <h3 className={h3Class}>Scopes we request</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li><code className={codeClass}>openid</code> – to associate you with your Google account identity.</li>
              <li><code className={codeClass}>https://www.googleapis.com/auth/userinfo.email</code> – to access your primary Google Account email address.</li>
              <li><code className={codeClass}>https://www.googleapis.com/auth/calendar.events</code> – to view, create, and edit events on your calendars for the purpose of scheduling Venture Builder sessions.</li>
            </ul>
          </div>

          <div>
            <h3 className={h3Class}>How we use Google user data</h3>
            <p className="mb-2">We use Google identity scopes only to sign you in, associate your Yuba account with your Google account, and pre-fill or validate your email address.</p>
            <p className="mb-2">We use the Calendar events scope to:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Create and update calendar events that correspond to Yuba coaching sessions.</li>
              <li>Read event metadata necessary to manage those Yuba-created events.</li>
              <li>Check for busy periods to avoid double-booking, primarily via free/busy information.</li>
            </ul>
            <p className="mt-2">We do not use Google Calendar data for advertising or to build profiles unrelated to the scheduling features you use.</p>
          </div>

          <div>
            <h3 className={h3Class}>How we share Google user data</h3>
            <p className="mb-2">We do not sell Google user data.</p>
            <p className="mb-2">We do not share Google Calendar data with third parties except:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>With service providers acting on our behalf (e.g., hosting and infrastructure providers) under strict confidentiality and data protection obligations.</li>
              <li>When required by law or to protect our rights, users, or the public, as described elsewhere in this Policy.</li>
            </ul>
            <p className="mt-2">We do not share Google user data with external AI model providers for training or general-purpose model improvement.</p>
          </div>

          <div>
            <h3 className={h3Class}>Human access to Google user data</h3>
            <p className="mb-2">Access to Google user data within our organization is limited to personnel who need it to operate, maintain, or secure the scheduling features (for example, debugging a specific user issue with your consent).</p>
            <p>We do not allow broad, unnecessary human reading of Google user data.</p>
          </div>

          <div>
            <h3 className={h3Class}>Limited Use</h3>
            <p className="mb-2">We use Google user data only to provide or improve user-facing features that are prominent in Yuba's interface (such as sign-in, viewing availability, and managing sessions), or for security and abuse prevention. We do not:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Use Google user data for advertising serving, targeting, or measurement.</li>
              <li>Transfer Google user data to third parties for their own advertising or marketing.</li>
              <li>Use Google user data to build profiles unrelated to the Yuba features you interact with.</li>
            </ul>
            <p className="mt-2">If our use of Google APIs changes in a material way, we will update this Privacy Policy accordingly and, where required, seek additional permissions or consent.</p>
          </div>
        </div>
      </section>

      <section ref={(el) => { if (el) sectionRefs.current['changes'] = el; }} id="changes" className="mb-12">
        <h2 className={h2Class}>14. Changes to This Privacy Policy</h2>
        <div className={textClass}>
          <p>
            We may update this Privacy Policy from time to time to reflect changes in technology, laws, or our services.
          </p>
          <p>When we make material changes, we will:</p>
          <ul className="list-disc pl-6 space-y-2 mt-3">
            <li>Update the "Last updated" date at the top of this Policy.</li>
            <li>Provide additional notice where required (e.g., via email or in-app notification).</li>
          </ul>
          <p className="mt-4">
            Your continued use of Yuba after changes take effect means you accept the updated Privacy Policy.
          </p>
        </div>
      </section>

      <section ref={(el) => { if (el) sectionRefs.current['contact'] = el; }} id="contact" className="mb-12">
        <h2 className={h2Class}>15. Contact Us</h2>
        <div className={textClass}>
          <p>
            If you have any questions, concerns, or requests related to this Privacy Policy or your personal data, you can contact us at:
          </p>
          <p className="font-semibold mt-3">
            Email:{' '}
            <a href="mailto:info@yubanow.com" className={linkClass}>
              info@yubanow.com
            </a>
          </p>
          <p>We will do our best to respond within a reasonable timeframe.</p>
        </div>
      </section>
    </>
  );
}

function PrintContent({ sectionRefs }: { sectionRefs: React.MutableRefObject<{ [key: string]: HTMLElement }> }) {
  return <PolicyContent sectionRefs={sectionRefs} isDarkMode={false} />;
}
