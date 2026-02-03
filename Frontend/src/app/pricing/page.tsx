"use client";

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Check, Sparkles, Building2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { StripePaymentService } from '@/lib/api/stripePaymentService';
import { useAuthStore } from '@/stores/authStore';
import { HeroHeader } from '@/components/header';
import Footer from '@/components/landing/Footer';
import SignInModal from '@/components/auth/SignInModal';
import DemoRequestModal from '@/components/pricing/DemoRequestModal';

// Constants for post-auth intent
const UPGRADE_INTENT_KEY = 'yuba_upgrade_intent';

interface UpgradeIntent {
  credits: number;
  price: number;
  timestamp: number;
}

// Helper to save/load/clear upgrade intent
const saveUpgradeIntent = (credits: number, price: number) => {
  const intent: UpgradeIntent = { credits, price, timestamp: Date.now() };
  localStorage.setItem(UPGRADE_INTENT_KEY, JSON.stringify(intent));
};

const loadUpgradeIntent = (): UpgradeIntent | null => {
  try {
    const stored = localStorage.getItem(UPGRADE_INTENT_KEY);
    if (!stored) return null;
    const intent: UpgradeIntent = JSON.parse(stored);
    // Expire intent after 30 minutes
    if (Date.now() - intent.timestamp > 30 * 60 * 1000) {
      clearUpgradeIntent();
      return null;
    }
    return intent;
  } catch {
    return null;
  }
};

const clearUpgradeIntent = () => {
  localStorage.removeItem(UPGRADE_INTENT_KEY);
};

// Credit options for Pro tier
const CREDIT_OPTIONS = [100, 200, 300, 400, 500, 600, 700, 800];

// Feature lists
const FREE_FEATURES = [
  'Problem Validator & 1 Report',
  'Problem Predictor',
  'Share Problem Validation Report',
];

const PRO_FEATURES = [
  'Download and Share Problem Validation Report',
  'Run Multiple Projects at once',
  'Invite Co-founders/ Collaborators to your Projects',
  'Access Multiple Workspaces',
  'Persona Builder',
  'Value Proposition Canvas Designer - Customer profile',
  'Hypothesis Development',
  'Assumptions Development',
  'Market Research Questions Generator',
  'Market Research Findings Analyzer & Report',
  'Enhanced Customer Profile',
  'Value Proposition Canvas Designer - Value Map',
  'Full Value Proposition Canvas - Customer profile & Value Map',
  'Value Proposition Statement Design',
  'Business Model Canvas Designer',
  'Solution & Business Model Critique',
  'Enhanced Value Proposition Statement',
  'Enhanced Business Model Canvas Designer',
  'Product Requirement Details',
  'Product Feature Prioritization',
  'Feature Advantage & Benefit Analysis',
  'Market Validation Metrics Designer',
  'Go-To-Market-Strategy Designer',
  'Pricing Strategy Support',
  'Pitch Deck Generator',
  'Chat With Project Feature',
  'Access to Vetted Venture Builders (additional costs apply)',
];

const ENTERPRISE_FEATURES = [
  'Dedicated Support',
  'Onboarding Services',
  'Program / Portfolio Progress Tracking',
  'Multiple Admins',
  'Credits allocations Management',
  'Venture Builders & Coaches seats',
  'Custom Design Systems',
  'Internal Team Capacity Building',
];

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: 'easeOut' as const,
    },
  },
};

// Feature list component with scroll area
function FeatureList({ features, title }: { features: string[]; title?: string }) {
  return (
    <div className="flex flex-col">
      {title && (
        <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">
          {title}
        </p>
      )}
      <div className="max-h-64 overflow-y-auto pr-2 space-y-2 scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600 scrollbar-track-transparent">
        {features.map((feature, index) => (
          <div key={index} className="flex items-start gap-2">
            <Check className="w-4 h-4 text-brand-500 mt-0.5 flex-shrink-0" />
            <span className="text-sm text-gray-600 dark:text-gray-400">{feature}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Credit selector dropdown
function CreditSelector({
  value,
  onChange,
}: {
  value: number;
  onChange: (credits: number) => void;
}) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
        Select Credits
      </label>
      <select
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
      >
        {CREDIT_OPTIONS.map((credits) => (
          <option key={credits} value={credits}>
            {credits} Credits - ${StripePaymentService.calculatePrice(credits)}
          </option>
        ))}
      </select>
      <p className="text-xs text-gray-500 dark:text-gray-400 italic">
        The more projects you run, the more credits you use
      </p>
    </div>
  );
}

// Free tier card
function FreeTierCard() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();

  const handleStartFree = () => {
    if (!isAuthenticated) {
      // User not authenticated, redirect to sign up
      router.push('/signup');
    } else {
      // User authenticated, redirect to choose workspace
      router.push('/choose-workspace');
    }
  };

  return (
    <motion.div
      variants={cardVariants}
      className="relative flex flex-col h-full bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow p-6"
    >
      {/* Header */}
      <div className="mb-6">
        <span className="inline-block px-3 py-1 text-xs font-medium text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-500/10 rounded-full mb-3">
          Tier 1
        </span>
        <h3 className="text-2xl font-bold text-gray-900 dark:text-white">Free</h3>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Discover what Yuba can do for you
        </p>
      </div>

      {/* Pricing */}
      <div className="mb-6">
        <div className="flex items-baseline gap-1">
          <span className="text-4xl font-bold text-gray-900 dark:text-white">$0</span>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">No payment needed</p>
        <p className="text-sm text-gray-500 dark:text-gray-400">Free for everyone</p>
      </div>

      {/* Credits */}
      <div className="mb-6 py-3 px-4 bg-brand-50 dark:bg-brand-500/10 rounded-lg">
        <p className="text-sm font-medium text-brand-700 dark:text-brand-300">
          30 Credits
        </p>
      </div>

      {/* Features */}
      <div className="flex-1 mb-6">
        <FeatureList features={FREE_FEATURES} />
      </div>

      {/* CTA */}
      <Button
        onClick={handleStartFree}
        variant="outline"
        className="w-full border-brand-500 text-brand-500 hover:bg-brand-50 dark:hover:bg-brand-500/10"
      >
        Start Free
      </Button>
    </motion.div>
  );
}

// Pro tier card - receives callbacks from parent for auth flow
interface ProTierCardProps {
  onUpgradeClick: (credits: number, price: number) => void;
  isProcessing: boolean;
}

function ProTierCard({ onUpgradeClick, isProcessing }: ProTierCardProps) {
  const [selectedCredits, setSelectedCredits] = useState(100);
  const price = StripePaymentService.calculatePrice(selectedCredits);

  const handleUpgrade = useCallback(() => {
    onUpgradeClick(selectedCredits, price);
  }, [selectedCredits, price, onUpgradeClick]);

  return (
    <motion.div
      variants={cardVariants}
      className="relative flex flex-col h-full bg-white dark:bg-gray-800 rounded-2xl border-2 border-brand-500 shadow-lg shadow-brand-500/10 p-6"
    >
      {/* Popular badge */}
      <div className="absolute -top-3 left-1/2 -translate-x-1/2">
        <span className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium text-white bg-brand-500 rounded-full">
          <Sparkles className="w-3 h-3" />
          Most Popular
        </span>
      </div>

      {/* Header */}
      <div className="mb-6 mt-2">
        <span className="inline-block px-3 py-1 text-xs font-medium text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-500/10 rounded-full mb-3">
          Tier 2
        </span>
        <h3 className="text-2xl font-bold text-gray-900 dark:text-white">Pro</h3>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Designed to empower individuals or teams exploring, discovering, building, and validating alone or together, to do so with speed and confidence.
        </p>
      </div>

      {/* Pricing */}
      <div className="mb-6">
        <div className="flex items-baseline gap-1">
          <span className="text-4xl font-bold text-brand-500">${price}</span>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          (dynamically increases by $20 for every 100 credits added)
        </p>
      </div>

      {/* Credit Selector */}
      <div className="mb-6">
        <CreditSelector value={selectedCredits} onChange={setSelectedCredits} />
        <div className="mt-3 py-3 px-4 bg-brand-50 dark:bg-brand-500/10 rounded-lg">
          <p className="text-sm font-medium text-brand-700 dark:text-brand-300">
            Selected: {selectedCredits} credits
          </p>
        </div>
      </div>

      {/* Features */}
      <div className="flex-1 mb-6">
        <FeatureList features={PRO_FEATURES} title="All features in Free, plus:" />
      </div>

      {/* CTA */}
      <Button
        onClick={handleUpgrade}
        disabled={isProcessing}
        className="w-full bg-brand-500 hover:bg-brand-600 text-white"
      >
        {isProcessing ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Processing...
          </>
        ) : (
          'Upgrade to Pro'
        )}
      </Button>
    </motion.div>
  );
}

// Enterprise tier card - receives callback to open demo modal
interface EnterpriseTierCardProps {
  onBookDemoClick: () => void;
}

function EnterpriseTierCard({ onBookDemoClick }: EnterpriseTierCardProps) {
  return (
    <motion.div
      variants={cardVariants}
      className="relative flex flex-col h-full bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow p-6"
    >
      {/* Header */}
      <div className="mb-6">
        <span className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-500/10 rounded-full mb-3">
          <Building2 className="w-3 h-3" />
          Tier 3
        </span>
        <h3 className="text-2xl font-bold text-gray-900 dark:text-white">Enterprise</h3>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Built for large orgs and ESOs in need of running and managing portfolios of programs in real time
        </p>
      </div>

      {/* Pricing */}
      <div className="mb-6">
        <div className="flex items-baseline gap-1">
          <span className="text-4xl font-bold text-gray-900 dark:text-white">Custom</span>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Flexible Plans</p>
      </div>

      {/* Placeholder for credits area */}
      <div className="mb-6 py-3 px-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
          Custom credit allocation
        </p>
      </div>

      {/* Features */}
      <div className="flex-1 mb-6">
        <FeatureList features={ENTERPRISE_FEATURES} title="All features in Pro, plus:" />
      </div>

      {/* CTA - Opens Demo Request Modal */}
      <Button
        onClick={onBookDemoClick}
        variant="outline"
        className="w-full border-brand-500 text-brand-500 hover:bg-brand-50 dark:hover:bg-brand-500/10"
      >
        Book a Demo
      </Button>
    </motion.div>
  );
}

// Main pricing page with auth-gated upgrade flow
export default function PricingPage() {
  const router = useRouter();
  const { isAuthenticated, user } = useAuthStore();
  
  // Auth modal state
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Demo request modal state
  const [showDemoModal, setShowDemoModal] = useState(false);
  
  // Track if user just completed auth via modal (not already logged in on page load)
  const justAuthenticatedRef = useRef(false);
  const initialAuthCheckedRef = useRef(false);
  
  // Process checkout with Stripe
  const processCheckout = useCallback(async (credits: number, price: number) => {
    // Clear intent before starting checkout
    clearUpgradeIntent();
    setIsProcessing(true);

    try {
      const response = await StripePaymentService.createCheckoutSession({
        credits,
        amount_usd: price,
        success_url: `${window.location.origin}/pricing/success`,
        cancel_url: `${window.location.origin}/pricing/cancel`,
        product: 'credits_pro',
      });

      console.log('Stripe checkout response:', response);

      // Handle redirect URL (support multiple possible keys from backend)
      const redirectUrl = (response as any).checkout_link ?? response.checkout_url ?? response.url ?? (response as any).redirect_url;

      if (!redirectUrl) {
        console.error('Full response object:', JSON.stringify(response, null, 2));
        throw new Error(`No checkout URL received from server. Response keys: ${Object.keys(response).join(', ')}`);
      }

      window.location.href = redirectUrl;
    } catch (error) {
      console.error('Checkout error:', error);
      toast.error(
        error instanceof Error
          ? error.message
          : 'Failed to create checkout session. Please try again.'
      );
      setIsProcessing(false);
    }
  }, []);

  // Clear stale intent on initial page load if user is already authenticated
  // This prevents auto-checkout from triggering unexpectedly
  useEffect(() => {
    if (!initialAuthCheckedRef.current) {
      initialAuthCheckedRef.current = true;
      // If user is already authenticated on page load, clear any stale intent
      // They should click the button again to initiate a new purchase
      if (isAuthenticated) {
        clearUpgradeIntent();
      }
    }
  }, [isAuthenticated]);

  // Check for pending upgrade intent after FRESH auth (via modal)
  useEffect(() => {
    if (isAuthenticated && justAuthenticatedRef.current) {
      justAuthenticatedRef.current = false; // Reset the flag
      const intent = loadUpgradeIntent();
      if (intent) {
        // User just authenticated with pending upgrade intent
        // Check if they have a workspace selected (tenant_id)
        if (user?.tenant_id) {
          // Has workspace, proceed to checkout
          processCheckout(intent.credits, intent.price);
        } else {
          // No workspace selected, redirect to workspace selector with return URL
          toast.info('Please select a workspace to continue with your purchase.');
          router.push('/choose-workspace?returnTo=/pricing');
        }
      }
    }
  }, [isAuthenticated, user?.tenant_id, router, processCheckout]);

  // Handle upgrade click from ProTierCard
  const handleUpgradeClick = useCallback((credits: number, price: number) => {
    if (!isAuthenticated) {
      // Save intent and show auth modal
      saveUpgradeIntent(credits, price);
      setShowAuthModal(true);
      return;
    }

    // User is authenticated, check for workspace
    if (!user?.tenant_id) {
      // Save intent and redirect to workspace selector
      saveUpgradeIntent(credits, price);
      toast.info('Please select a workspace to continue with your purchase.');
      router.push('/choose-workspace?returnTo=/pricing');
      return;
    }

    // User is authenticated with workspace, proceed to checkout
    processCheckout(credits, price);
  }, [isAuthenticated, user?.tenant_id, router, processCheckout]);

  // Handle auth modal close
  const handleAuthModalClose = useCallback(() => {
    setShowAuthModal(false);
    // Clear intent if modal is closed without completing auth
    if (!isAuthenticated) {
      clearUpgradeIntent();
    }
  }, [isAuthenticated]);

  // Handle successful auth
  const handleAuthSuccess = useCallback(() => {
    justAuthenticatedRef.current = true; // Mark that user just authenticated
    setShowAuthModal(false);
    // The useEffect above will handle the rest when isAuthenticated changes
  }, []);

  return (
    <>
      <HeroHeader />
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pt-22">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-brand-50 via-white to-brand-100 dark:from-gray-900 dark:via-gray-900 dark:to-brand-950 opacity-50" />
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-12 text-center">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 dark:text-white mb-4">
              Pricing
            </h1>
            <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto pb-4">
              Start for free. Upgrade to get the capacity that exactly matches your needs.
            </p>
          </motion.div>
        </div>
      </div>

      {/* Pricing Cards */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid grid-cols-1 md:grid-cols-3 gap-8 -mt-8"
        >
          <FreeTierCard />
          <ProTierCard onUpgradeClick={handleUpgradeClick} isProcessing={isProcessing} />
          <EnterpriseTierCard onBookDemoClick={() => setShowDemoModal(true)} />
        </motion.div>

        {/* Additional info */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-16 text-center"
        >
          <p className="text-sm text-gray-500 dark:text-gray-400">
            All plans include secure payment processing via Stripe.
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            Questions?{' '}
            <a
              href="mailto:info@yubanow.com"
              className="text-brand-500 hover:text-brand-600 underline"
            >
              Contact our sales team
            </a>
          </p>
        </motion.div>
      </div>
      <Footer />
    </div>

    {/* Auth Modal Overlay - uses existing SignInModal */}
    <SignInModal
      isOpen={showAuthModal}
      onOpenChange={(open) => {
        if (!open) handleAuthModalClose();
      }}
      onSuccess={handleAuthSuccess}
      onClose={handleAuthModalClose}
    />

    {/* Demo Request Modal */}
    <DemoRequestModal
      isOpen={showDemoModal}
      onOpenChange={setShowDemoModal}
      requestedTier="organization"
      source="pricing_page"
    />
    </>
  );
}
