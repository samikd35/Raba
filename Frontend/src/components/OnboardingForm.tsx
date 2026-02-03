'use client'

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { generateProblemsComplete, type ProblemGenerationParameters, type Problem, testApiConnectivity } from '@/lib/api/problemGeneration';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-hot-toast';
import { useAuthStore } from "@/stores/authStore";
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Label } from '@/components/ui/label';
import { CountrySelection } from '@/components/CountrySelection';
import { InsufficientCreditsModal } from '@/components/common/InsufficientCreditsModal';
import { cn } from '@/lib/utils';
import { 
  ChevronLeft, 
  ChevronRight, 
  Loader2, 
  CheckCircle, 
  Zap, 
  Users, 
  Target, 
  Lightbulb, 
  AlertCircle,
  ArrowRight,
  Globe,
  Briefcase,
  Building,
  Package,
  Heart,
  Factory
} from 'lucide-react';

interface FormData {
  industries: string[];
  country: string;
  professions: string[];
  productTypes: string[];
  targetCustomers: string[];
  impactFocus: string;
  customValues: {
    industries: string[];
    professions: string[];
    productTypes: string[];
    targetCustomers: string[];
    impactFocus: string;
  };
}

type GenerationState = 
  | { status: 'idle' | 'validating' | 'submitting' | 'processing' | 'completed'; progress: number; message: string; jobId?: string; startTime?: number; error?: undefined; }
  | { status: 'error'; progress: number; message: string; error: string; jobId?: string; startTime?: number; };

const STORAGE_KEY = 'onboarding_form_data_v1';
const STEP_ICONS = [Factory, Globe, Briefcase, Package, Users, Heart];

const industryOptions = [
  'Agriculture / Food',
  'Healthcare / Life Sciences',
  'Education & EdTech',
  'Financial Services & FinTech',
  'Energy & Utilities',
  'Transportation & Mobility',
  'Logistics & Supply Chain',
  'Retail & e-Commerce',
  'Manufacturing',
  'Construction & Real Estate',
  'Creative & Entertainment',
  'Tourism & Hospitality',
  'Water & Sanitation',
  'Climate / Environmental Services',
  'Public Services / GovTech',
  'ICT / Telecom',
  'Mining & Natural Resources',
  'Sport',
  'Other'
];

const countryOptions = [
  'Algeria', 'Angola', 'Benin', 'Botswana', 'Burkina Faso', 'Burundi', 'Cabo Verde', 'Cameroon', 'Central African Republic',
  'Chad', 'Comoros', 'Congo (Congo-Brazzaville)', 'Côte d\'Ivoire', 'Democratic Republic of the Congo', 'Djibouti',
  'Egypt', 'Equatorial Guinea', 'Eritrea', 'Eswatini', 'Ethiopia', 'Gabon', 'Gambia', 'Ghana', 'Guinea', 'Guinea-Bissau',
  'Kenya', 'Lesotho', 'Liberia', 'Libya', 'Madagascar', 'Malawi', 'Mali', 'Mauritania', 'Mauritius', 'Morocco', 'Mozambique',
  'Namibia', 'Niger', 'Nigeria', 'Rwanda', 'Sao Tome and Principe', 'Senegal', 'Seychelles', 'Sierra Leone', 'Somalia',
  'South Africa', 'South Sudan', 'Sudan', 'Tanzania', 'Togo', 'Tunisia', 'Uganda', 'Zambia', 'Zimbabwe'
];

const professionOptions = [
  'Software / Web Developer',
  'Data / AI Professional',
  'Mechanical Engineer',
  'Electrical / Electronics Engineer',
  'Civil / Construction Engineer',
  'Business / Management',
  'Finance / Accounting',
  'Marketing / Sales',
  'Healthcare Professional',
  'Agriculture / Agronomy',
  'Education / Teaching',
  'Design / UX',
  'Logistics / Supply Chain',
  'Manufacturing / Operations',
  'Legal / Policy',
  'Research / Academia',
  'Other'
];

const productTypeOptions = [
  'Digital / tech products or services',
  'Physical products',
  'Hardware products',
  'Creative Products / Services',
  'Hybrid (digital + physical)',
  'Other'

];

const targetCustomerOptions = [
  'Businesses (B2B)', 'Consumers (B2C)', 'Both (B2B2C)', 'Non-profits', 'Government', 'Other'

];

const impactFocusOptions = [
  'Fully Commercial',
  'Social Venture',
  'Non-Profit / Foundations',
  'Other'
];

const stepLabels = ['Industry', 'Geography', 'Professional Background', 'Product Type', 'Customer', 'Impact'];

// Mapping functions to transform form data to API parameters
const mapFormDataToApiParameters = (formData: FormData): ProblemGenerationParameters => {
  // Helper to map to snake_case
  const toSnakeCase = (str: string): string => 
    str.toLowerCase()
       .replace(/ \/ /g, '_')
       .replace(/\s+/g, '_')
       .replace(/[^a-z0-9_]/g, '');

  // Get custom values safely
  const customValues = formData.customValues || {
    industries: [],
    professions: [],
    productTypes: [],
    targetCustomers: [],
    impactFocus: ''
  };

  // Map industries - include custom values
  const mapIndustries = (industries: string[]): string[] => {
    const mapped = industries.filter(i => i !== 'Other').map(toSnakeCase);
    if (industries.includes('Other') && customValues.industries?.[0]) {
      mapped.push(toSnakeCase(customValues.industries[0]));
    }
    return mapped;
  };

  // Map professions/background - include custom values
  const mapBackground = (professions: string[]): string[] => {
    const mapped = professions.filter(p => p !== 'Other').map(toSnakeCase);
    if (professions.includes('Other') && customValues.professions?.[0]) {
      mapped.push(toSnakeCase(customValues.professions[0]));
    }
    return mapped;
  };

  // Map impact focus to API expected values - handle custom values
  const mapImpactFocus = (focus: string): string[] => {
    if (focus === 'Other' && customValues.impactFocus) {
      return [toSnakeCase(customValues.impactFocus)];
    }
    
    const focusMap: Record<string, string> = {
      'Fully Commercial': 'fully_commercial',
      'Social Venture': 'social_venture',
      'Non-Profit / Foundations': 'non_profit_foundations',
      'Social Impact': 'social_impact',
      'Environmental': 'environmental',
      'Economic': 'economic_development',
      'Education': 'education',
      'Healthcare': 'healthcare',
      'Gender Equality': 'gender_equality',
      'Rural Development': 'rural_development',
      'Technology': 'technology'
    };
    
    const mapped = focusMap[focus] || toSnakeCase(focus);
    if (!focusMap[focus]) {
      console.warn(`Unmapped impact focus: ${focus}`);
    }
    return [mapped];
  };

  // Map product types to API expected values - include custom values
  const mapProductTypes = (types: string[]): string[] => {
    const typeMap: Record<string, string> = {
      'Digital / tech products or services': 'digital_tech',
      'Physical products': 'physical_products',
      'Hardware products': 'hardware',
      'Creative Products / Services': 'creative_services',
      'Hybrid (digital + physical)': 'hybrid'
    };
    
    const mapped = types.filter(t => t !== 'Other').map(type => {
      const mappedType = typeMap[type] || toSnakeCase(type);
      if (!typeMap[type]) {
        console.warn(`Unmapped product type: ${type}`);
      }
      return mappedType;
    });
    
    if (types.includes('Other') && customValues.productTypes?.[0]) {
      mapped.push(toSnakeCase(customValues.productTypes[0]));
    }
    
    return mapped;
  };

  // Map target customers to API expected values - include custom values
  const mapTargetCustomers = (customers: string[]): string[] => {
    const customerMap: Record<string, string> = {
      'Businesses (B2B)': 'b2b',
      'Consumers (B2C)': 'b2c',
      'Both (B2B2C)': 'b2b2c',
      'Non-profits': 'non_profits',
      'Government': 'government'
    };
    
    const mapped = customers.filter(c => c !== 'Other').map(customer => {
      const mappedCustomer = customerMap[customer] || toSnakeCase(customer);
      if (!customerMap[customer]) {
        console.warn(`Unmapped target customer: ${customer}`);
      }
      return mappedCustomer;
    });
    
    if (customers.includes('Other') && customValues.targetCustomers?.[0]) {
      mapped.push(toSnakeCase(customValues.targetCustomers[0]));
    }
    
    return mapped;
  };

  return {
    industry: mapIndustries(formData.industries),
    geography: [formData.country],
    background: mapBackground(formData.professions),
    product_type: mapProductTypes(formData.productTypes),
    target_customer: mapTargetCustomers(formData.targetCustomers),
    impact_focus: mapImpactFocus(formData.impactFocus),
    num_problems: 3,
    creativity_level: 0.7,
    custom_constraints: '' // Optional field
  };
};

const OnboardingForm = ( { path }: { path: string } ) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<FormData>({
    industries: [],
    country: '',
    professions: [],
    productTypes: [],
    targetCustomers: [],
    impactFocus: '',
    customValues: {
      industries: [],
      professions: [],
      productTypes: [],
      targetCustomers: [],
      impactFocus: ''
    }
  });
  const [generationState, setGenerationState] = useState<GenerationState>({
    status: 'idle',
    progress: 0,
    message: ''
  });
  const [isInsufficientCreditsModalOpen, setIsInsufficientCreditsModalOpen] = useState(false);
  const [results, setResults] = useState<Problem[] | null>(null);
  const [showResults, setShowResults] = useState(false);
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false);
  const [isAutoSaving, setIsAutoSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout>();
  const router = useRouter();
  
  // Use Zustand store instead of old useAuth hook
  const { user, isAuthenticated, isLoading: authLoading } = useAuthStore();
  const abortControllerRef = useRef<AbortController | null>(null);

  // Load saved form data on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
          const { formData: savedFormData, currentStep: savedStep } = JSON.parse(saved);
          setFormData(savedFormData);
          setCurrentStep(savedStep);
        }
      } catch (error) {
        console.error('Error loading saved form data:', error);
        localStorage.removeItem(STORAGE_KEY);
      }
    }
  }, []);

  // Auto-save functionality
  const autoSave = useCallback(() => {
    if (typeof window !== 'undefined') {
      setIsAutoSaving(true);
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ formData, currentStep }));
      setLastSaved(new Date());
      setTimeout(() => setIsAutoSaving(false), 1000);
    }
  }, [formData, currentStep]);

  // Debounced auto-save (reduced to 1000ms)
  useEffect(() => {
    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current);
    }
    autoSaveTimeoutRef.current = setTimeout(autoSave, 1000);
    return () => {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current);
      }
    };
  }, [formData, currentStep, autoSave]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      
      if (e.key === 'ArrowRight' && currentStep < 6 && isStepValid(currentStep)) {
        e.preventDefault();
        handleNext();
      } else if (e.key === 'ArrowLeft' && currentStep > 1) {
        e.preventDefault();
        handleBack();
      } else if (e.key === 'Enter' && currentStep === 6 && isStepValid(currentStep)) {
        e.preventDefault();
        handleSubmit();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentStep, formData]);

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      toast.error('Please sign in to continue');
      router.push('/signin');
    }
  }, [isAuthenticated, authLoading, router]);

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const toggleSelection = (field: keyof FormData, value: string, isMultiSelect = true, maxSelections = Infinity) => {
    if (field === 'country' || field === 'impactFocus') {
      setFormData(prev => ({
        ...prev,
        [field]: prev[field] === value ? '' : value
      }));
    } else if (isMultiSelect) {
      setFormData(prev => {
        const currentValues = Array.isArray(prev[field]) ? [...(prev[field] as string[])] : [];
        
        if (currentValues.includes(value)) {
          return { ...prev, [field]: currentValues.filter(item => item !== value) };
        }
        
        if (currentValues.length >= maxSelections) {
          toast.error(`Maximum ${maxSelections} selections allowed`);
          return prev;
        }
        
        return { ...prev, [field]: [...currentValues, value] };
      });
    }
  };

  const renderSelectionGrid = useMemo(() => (options: string[], field: keyof FormData, isMultiSelect = true, maxSelections = 1) => {
    let currentValues: string[] = [];
    let isAtMax = false;

    if (field === 'country' || field === 'impactFocus') {
      currentValues = formData[field] ? [formData[field] as string] : [];
      isAtMax = false;
    } else {
      currentValues = Array.isArray(formData[field]) ? formData[field] as string[] : [];
      isAtMax = isMultiSelect && currentValues.length >= maxSelections;
    }
    
    return (
      <div className="space-y-4">
        {isMultiSelect && maxSelections !== Infinity && field !== 'country' && field !== 'impactFocus' && (
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground dark:text-gray-400">
              {currentValues.length}/{maxSelections} selected
            </p>
            {currentValues.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setFormData(prev => ({ ...prev, [field]: [] }))}
                className="text-xs h-6 px-2 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-white"
              >
                Clear all
              </Button>
            )}
          </div>
        )}
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
          {options.map((option, index) => {
            const isSelected = currentValues.includes(option);
            const isDisabled = isAtMax && !isSelected;
            
            return (
              <motion.div
                key={option}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => !isDisabled && toggleSelection(field, option, isMultiSelect, maxSelections)}
                  className={cn(
                    "h-auto py-2 px-4 text-left justify-start transition-all duration-200 border-2 w-full group",
                    isSelected 
                      ? "border-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-500/20 dark:text-brand-300 dark:border-brand-400 shadow-md scale-[1.02] ring-2 ring-brand-200 dark:ring-brand-400/50" 
                      : "border-gray-200 dark:border-gray-700 hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-sm dark:bg-gray-800/50 dark:text-gray-300 dark:hover:bg-gray-700/50",
                    isDisabled && "opacity-50 cursor-not-allowed"
                  )}
                  aria-pressed={isSelected}
                  aria-disabled={isDisabled}
                  disabled={isDisabled}
                >
                  <span className="flex-1 text-sm font-medium">{option}</span>
                  <div className="flex items-center gap-2">
                    {isSelected && (
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="flex items-center"
                      >
                        <CheckCircle className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                      </motion.div>
                    )}
                  </div>
                </Button>
              </motion.div>
            );
          })}
        </div>
        
        {/* Enhanced validation error message - now live */}
        <AnimatePresence>
          {hasAttemptedSubmit && !isStepValid(currentStep) && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="flex items-center gap-2 text-red-500 dark:text-red-400 text-sm mt-4 p-3 bg-red-50 dark:bg-red-500/10 rounded-lg border border-red-200 dark:border-red-500/20"
            >
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{getStepValidationError(currentStep)}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  }, [formData, currentStep, hasAttemptedSubmit]);

  const handleNext = () => {
    if (!isStepValid(currentStep)) {
      setHasAttemptedSubmit(true);
      toast.error(getStepValidationError(currentStep));
      return;
    }
    
    if (currentStep < 6) {
      setCurrentStep(prev => prev + 1);
      setHasAttemptedSubmit(false);
    } else {
      handleSubmit();
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1);
      setHasAttemptedSubmit(false);
    }
  };

  const isFormValid = (): boolean => {
    const customValues = getCustomValues();
    
    // Check if custom values are provided when "Other" is selected
    const hasValidCustomIndustries = !formData.industries.includes('Other') || 
      (customValues.industries?.[0]?.trim() !== '');
    
    const hasValidCustomProfessions = !formData.professions.includes('Other') || 
      (customValues.professions?.[0]?.trim() !== '');
    
    const hasValidCustomProductTypes = !formData.productTypes.includes('Other') || 
      (customValues.productTypes?.[0]?.trim() !== '');
    
    const hasValidCustomTargetCustomers = !formData.targetCustomers.includes('Other') || 
      (customValues.targetCustomers?.[0]?.trim() !== '');
    
    const hasValidCustomImpactFocus = formData.impactFocus !== 'Other' || 
      ((customValues.impactFocus ?? '').trim() !== '');

    return (
      formData.industries.length > 0 && formData.industries.length <= 2 && hasValidCustomIndustries &&
      formData.country !== '' &&
      formData.professions.length > 0 && hasValidCustomProfessions &&
      formData.productTypes.length > 0 && hasValidCustomProductTypes &&
      formData.targetCustomers.length > 0 && formData.targetCustomers.length <= 3 && hasValidCustomTargetCustomers &&
      formData.impactFocus !== '' && hasValidCustomImpactFocus
    );
  };

  const handleSubmit = async () => {
    if (!user) {
      toast.error('Please sign in to continue');
      router.push('/signin');
      return;
    }

    try {
      // Set initial loading state
      setGenerationState({ 
        status: 'validating', 
        progress: 0, 
        message: 'Validating form data...',
        startTime: Date.now()
      });
      setHasAttemptedSubmit(true);

      // Validate entire form
      if (!isFormValid()) {
        throw new Error('Please complete all required fields before submitting.');
      }

      // Map form data to API parameters using the mapping function
      const parameters = mapFormDataToApiParameters(formData);

      // Start the problem generation process
      // Important: do not carry over any previous error when moving back to a non-error state
      setGenerationState(prev => ({
        status: 'submitting',
        progress: 10,
        message: 'Submitting your request...',
        jobId: prev.jobId,
        startTime: prev.startTime,
        error: undefined,
      }));

      abortControllerRef.current = new AbortController();

      // Generate problems with progress updates (force fresh results)
      const response = await generateProblemsComplete(
        parameters,
        (progressValue, status, message) => {
          let mappedStatus: 'processing' | 'completed' | 'error' = 'processing';
          if (status === 'completed') {
            mappedStatus = 'completed';
          } else if (status === 'error') {
            mappedStatus = 'error';
          }
          
          setGenerationState(prev => {
  if (mappedStatus === 'error') {
    return {
      status: 'error',
      progress: Math.min(progressValue, 90),
      message: message || prev.message || 'An error occurred while generating problems.',
      error: message || prev.message || 'Unknown error',
      jobId: prev.jobId,
      startTime: prev.startTime,
    };
  }

  return {
    ...prev,
    status: mappedStatus,          // 'processing' | 'completed'
    progress: Math.min(progressValue, 90),
    message: message || prev.message,
    error: undefined,              // makes this clearly the non-error variant
  };
});
        },
        abortControllerRef.current.signal,
        true // forceRefresh: always generate fresh problems for onboarding
      );

      // Handle the completed response
      if (response.status === 'completed' && response.problems) {
        const endTime = Date.now();
        const processingTime = endTime - (generationState.startTime || endTime);
        
        const seconds = Math.round(processingTime / 1000);
        
        setGenerationState({
          status: 'completed',
          progress: 100,
          message: `Generated ${response.problems.length} problems`,
          jobId: response.job_id,
          startTime: generationState.startTime
        });
        
        // Navigate to problem explorer instead of showing results inline
        if (response.job_id) {
          toast.success(`Successfully generated ${response.problems.length} problems! Redirecting...`);
          setTimeout(() => {
            router.push(`/${path}/problem-explorer/${response.job_id}`);
          }, 1000);
        } else {
          toast.success(`Successfully generated ${response.problems.length} problems in ${seconds}s`);
        }
        
        localStorage.removeItem(STORAGE_KEY);
      } else {
        throw new Error(response.message || 'Problem generation failed. Please try again.');
      }
    } catch (error: unknown) {
      // Type guard for Error
     // inside catch (error: unknown) { ... }

const errorMessage =
  error instanceof Error ? error.message : 'An unexpected error occurred';

if (error instanceof Error && error.name === 'AbortError') {
  return;
}
console.error('Error in problem generation:', error);

// Explicit handling for insufficient credits (HTTP 402 mapped in problemGeneration.ts)
if (errorMessage === 'Problem generation failed: INSUFFICIENT_CREDITS_ERROR') {
  setGenerationState({
    status: 'error',
    progress: 0,
    message: 'Insufficient credits to generate problems',
    error: errorMessage,
  });
  setIsInsufficientCreditsModalOpen(true);
  // toast.error(
  //   'You do not have enough credits to generate new problems. Please purchase more credits or upgrade your plan.'
  // );
  return;
}

// Generic error handling (existing logic)
setGenerationState({
  status: 'error',
  progress: 0,
  message: 'Failed to generate problems',
  error: errorMessage,
});

const lower = errorMessage.toLowerCase();
if (lower.includes('authentication')) {
  toast.error('Session expired. Please sign in again.');
  router.push('/signin');
} else if (lower.includes('validation')) {
  toast.error(`Validation error: ${errorMessage}`);
} else {
  toast.error(errorMessage || 'Failed to generate problems. Please try again.');
}
    }
  };

  const getCustomValues = () => {
    return formData.customValues || {
      industries: [],
      professions: [],
      productTypes: [],
      targetCustomers: [],
      impactFocus: ''
    };
  };

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-4">
            <div className="space-y-1">
              <Label className="text-xl font-semibold text-brand-500 dark:text-brand-400">Which industry do you want to focus on? <span className='text-red-500 dark:text-red-400'>*</span></Label>
              <p className="text-sm text-muted-foreground dark:text-gray-400">Select up to two industry sectors you're most interested in. This helps us generate targeted problem statements.</p>
            </div>
            {renderSelectionGrid(industryOptions, 'industries', true, 2)}
            {formData.industries.includes('Other') && (
              <div className="space-y-1">
                <Label className="text-md font-medium text-brand-500 mb-2 dark:text-brand-400">Enter your custom industry:</Label>
                <input
                  type="text"
                  value={getCustomValues().industries?.[0] || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, customValues: { ...prev.customValues, industries: [e.target.value] } }))}
                  className="w-full p-2 border border-gray-200 dark:border-gray-700 rounded-lg"
                  placeholder="Enter your industry..."
                />
              </div>
            )}
          </div>
        );
      case 2:
        return (
          <div className="space-y-4">
            <div className="space-y-1">
              <Label className="text-xl font-semibold text-brand-500 dark:text-brand-400">Which country do you want to focus on? <span className='text-red-500 dark:text-red-400'>*</span></Label>
              <p className="text-sm text-muted-foreground dark:text-gray-400">Select the African country you want to focus on. This helps tailor problems to specific market conditions.</p>
            </div>
            <CountrySelection
              value={formData.country}
              onValueChange={(value) => setFormData(prev => ({ ...prev, country: value }))}
            />
          </div>
        );
      case 3:
        return (
          <div className="space-y-4">
            <div className="space-y-1">
              <Label className="text-xl font-semibold text-brand-500 dark:text-brand-400">What's your professional background? <span className='text-red-500 dark:text-red-400'>*</span></Label>
              <p className="text-sm text-muted-foreground dark:text-gray-400">Your professional background helps generate problems that match your skills and expertise.</p>
            </div>
            {renderSelectionGrid(professionOptions, 'professions', true, 2)}
            {formData.professions.includes('Other') && (
              <div className="space-y-1">
                <Label className="text-md font-medium text-brand-500 mb-2 dark:text-brand-400">Enter your custom profession:</Label>
                <input
                  type="text"
                  value={getCustomValues().professions?.[0] || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, customValues: { ...prev.customValues, professions: [e.target.value] } }))}
                  className="w-full p-2 border border-gray-200 dark:border-gray-700 rounded-lg"
                  placeholder="Enter your profession..."
                />
              </div>
            )}
          </div>
        );
      case 4:
        return (
          <div className="space-y-4">
            <div className="space-y-1">
              <Label className="text-xl font-semibold text-brand-500 dark:text-brand-400">What type of product do you see yourself building? <span className='text-red-500 dark:text-red-400'>*</span></Label>
              <p className="text-sm text-muted-foreground dark:text-gray-400">Based on your background, indicate the type of product you want to build.</p>
            </div>
            {renderSelectionGrid(productTypeOptions, 'productTypes', true, Infinity)}
            {formData.productTypes.includes('Other') && (
              <div className="space-y-1">
                <Label className="text-md font-medium text-brand-500 mb-2 dark:text-brand-400">Enter your custom product type:</Label>
                <input
                  type="text"
                  value={getCustomValues().productTypes?.[0] || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, customValues: { ...prev.customValues, productTypes: [e.target.value] } }))}
                  className="w-full p-2 border border-gray-200 dark:border-gray-700 rounded-lg"
                  placeholder="Enter your product type..."
                />
              </div>
            )}
          </div>
        );
      case 5:
        return (
          <div className="space-y-4">
            <div className="space-y-1">
              <Label className="text-xl font-semibold text-brand-500 dark:text-brand-400">Who is your target customer? <span className='text-red-500 dark:text-red-400'>*</span></Label>
              <p className="text-sm text-muted-foreground dark:text-gray-400">Select the customer segments you want to focus on.</p>
            </div>
            {renderSelectionGrid(targetCustomerOptions, 'targetCustomers', true, 3)}
            {formData.targetCustomers.includes('Other') && (
              <div className="space-y-1">
                <Label className="text-md font-medium text-brand-500 mb-2 dark:text-brand-400">Enter your custom target customer:</Label>
                <input
                  type="text"
                  value={getCustomValues().targetCustomers?.[0] || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, customValues: { ...prev.customValues, targetCustomers: [e.target.value] } }))}
                  className="w-full p-2 border border-gray-200 dark:border-gray-700 rounded-lg"
                  placeholder="Enter your target customer..."
                />
              </div>
            )}
          </div>
        );
      case 6:
        return (
          <div className="space-y-4">
            <div className="space-y-1">
              <Label className="text-xl font-semibold text-brand-500 dark:text-brand-400">What is your impact focus? <span className='text-red-500 dark:text-red-400'>*</span></Label>
              <p className="text-sm text-muted-foreground dark:text-gray-400">Select your impact focus to define the nature of your venture's objectives.</p>
            </div>
            {renderSelectionGrid(impactFocusOptions, 'impactFocus', false, 1)}
            {formData.impactFocus === 'Other' && (
              <div className="space-y-1">
                <Label className="text-md font-medium text-brand-500 mb-2 dark:text-brand-400">Enter your custom impact focus:</Label>
                <input
                  type="text"
                  value={getCustomValues().impactFocus || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, customValues: { ...prev.customValues, impactFocus: e.target.value } }))}
                  className="w-full p-2 border border-gray-200 dark:border-gray-700 rounded-lg"
                  placeholder="Enter your impact focus..."
                />
              </div>
            )}
          </div>
        );
      default:
        return null;
    }
  };

  const isStepValid = (step: number) => {
    switch (step) {
      case 1:
        const hasValidIndustries = formData.industries.length > 0 && formData.industries.length <= 2;
        const hasValidCustomIndustry = !formData.industries.includes('Other') || 
          (getCustomValues().industries?.[0] && getCustomValues().industries[0].trim() !== '');
        return hasValidIndustries && hasValidCustomIndustry;
      case 2:
        return formData.country !== '';
      case 3:
        const hasValidProfessions = formData.professions.length > 0;
        const hasValidCustomProfession = !formData.professions.includes('Other') || 
          (getCustomValues().professions?.[0] && getCustomValues().professions[0].trim() !== '');
        return hasValidProfessions && hasValidCustomProfession;
      case 4:
        const hasValidProductTypes = formData.productTypes.length > 0;
        const hasValidCustomProductType = !formData.productTypes.includes('Other') || 
          (getCustomValues().productTypes?.[0] && getCustomValues().productTypes[0].trim() !== '');
        return hasValidProductTypes && hasValidCustomProductType;
      case 5:
        const hasValidTargetCustomers = formData.targetCustomers.length > 0 && formData.targetCustomers.length <= 3;
        const hasValidCustomTargetCustomer = !formData.targetCustomers.includes('Other') || 
          (getCustomValues().targetCustomers?.[0] && getCustomValues().targetCustomers[0].trim() !== '');
        return hasValidTargetCustomers && hasValidCustomTargetCustomer;
      case 6:
        const hasValidImpactFocus = formData.impactFocus !== '';
        const hasValidCustomImpactFocus = formData.impactFocus !== 'Other' || 
          (getCustomValues().impactFocus && getCustomValues().impactFocus.trim() !== '');
        return hasValidImpactFocus && hasValidCustomImpactFocus;
      default:
        return false;
    }
  };

  const getStepValidationError = (step: number) => {
    switch (step) {
      case 1:
        if (formData.industries.length === 0) return 'Please select at least one industry';
        if (formData.industries.length > 2) return 'Please select no more than two industries';
        if (formData.industries.includes('Other') && (!getCustomValues().industries?.[0] || getCustomValues().industries[0].trim() === '')) {
          return 'Please enter your custom industry';
        }
        return 'Please complete this step';
      case 2:
        return 'Please select your country';
      case 3:
        if (formData.professions.length === 0) return 'Please select at least one profession';
        if (formData.professions.includes('Other') && (!getCustomValues().professions?.[0] || getCustomValues().professions[0].trim() === '')) {
          return 'Please enter your custom profession';
        }
        return 'Please complete this step';
      case 4:
        if (formData.productTypes.length === 0) return 'Please select at least one product type';
        if (formData.productTypes.includes('Other') && (!getCustomValues().productTypes?.[0] || getCustomValues().productTypes[0].trim() === '')) {
          return 'Please enter your custom product type';
        }
        return 'Please complete this step';
      case 5:
        if (formData.targetCustomers.length === 0) return 'Please select at least one target customer';
        if (formData.targetCustomers.length > 3) return 'Please select no more than three target customers';
        if (formData.targetCustomers.includes('Other') && (!getCustomValues().targetCustomers?.[0] || getCustomValues().targetCustomers[0].trim() === '')) {
          return 'Please enter your custom target customer';
        }
        return 'Please complete this step';
      case 6:
        if (formData.impactFocus === '') return 'Please select an impact focus';
        if (formData.impactFocus === 'Other' && (!getCustomValues().impactFocus || getCustomValues().impactFocus.trim() === '')) {
          return 'Please enter your custom impact focus';
        }
        return 'Please complete this step';
      default:
        return 'Please complete this step';
    }
  };

  const handleCloseInsufficientCreditsModal = () => {
    setIsInsufficientCreditsModalOpen(false);
    // Reset generation state to allow users to try again
    setGenerationState({
      status: 'idle',
      progress: 0,
      message: ''
    });
  };

  const renderResults = () => {
    if (!results) return null;

    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="space-y-4"
        id="generation-results"
      >
        <div className="text-center space-y-2">
          <div>
            <h2 className="text-2xl font-bold text-brand-500 dark:text-brand-300">
              Problems Generated Successfully!
            </h2>
            <p className="text-muted-foreground dark:text-gray-400">
              We've identified {results.length} key problems for your consideration
            </p>
          </div>
        </div>

        <div className="grid gap-6">
          {results.map((problem, index) => (
            <Card key={problem.id || index} className="border border-brand-100 dark:border-brand-700/50 dark:bg-gray-900/30">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <span className="bg-brand-100 text-brand-700 dark:bg-brand-500/20 dark:text-brand-300 px-4 py-1 rounded-full text-sm font-medium">
                        Problem #{index + 1}
                      </span>
                    </div>
                    <CardTitle className="text-lg leading-tight dark:text-white">
                      {problem.title}
                    </CardTitle>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-8">
                <p className="text-muted-foreground dark:text-gray-300 leading-relaxed text-sm -mt-4">
                  {problem.description}
                </p>
                
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="space-y-4 p-4 bg-brand-25 rounded-lg dark:bg-brand-500/10 dark:border dark:border-brand-500/20">
                    <div className="flex items-center gap-2 text-md font-medium text-brand-600 dark:text-brand-300">
                      <Target className="w-4 h-4" />
                      Root Causes
                    </div>
                    <ul className="space-y-1 text-sm text-muted-foreground dark:text-gray-300">
                      {(problem.root_causes ?? []).slice(0, 3).map((cause, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="w-1.5 h-1.5 bg-brand-500 dark:bg-brand-400 rounded-full mt-2 flex-shrink-0" />
                          {cause}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="space-y-4 p-4 bg-red-50 rounded-lg dark:bg-red-500/10 dark:border dark:border-red-500/20">
                    <div className="flex items-center gap-2 text-md font-medium text-brand-600 dark:text-brand-300">
                      <Users className="w-4 h-4" />
                      Key Stakeholders
                    </div>
                    <ul className="space-y-1 text-sm text-muted-foreground dark:text-gray-300">
                      {(problem.stakeholders ?? []).slice(0, 3).map((stakeholder, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="w-1.5 h-1.5 bg-green-500 dark:bg-green-400 rounded-full mt-2 flex-shrink-0" />
                          {stakeholder}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="space-y-4 p-4 bg-amber-50 rounded-lg dark:bg-amber-500/10 dark:border dark:border-amber-500/20">
                  <div className="flex items-center gap-2 text-md font-medium text-brand-600 dark:text-brand-300">
                    <Lightbulb className="w-4 h-4" />
                    Success Metrics
                  </div>
                  <div className="grid md:grid-cols-2 gap-2">
                    {(problem.success_metrics ?? []).slice(0, 4).map((metric, idx) => (
                      <div key={idx} className="bg-green-50 dark:bg-green-500/10 text-green-700 dark:text-green-300 px-3 py-2 rounded-lg text-sm border dark:border-green-500/20">
                        {metric}
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="flex justify-center pt-6">
          <Button
            onClick={() => {
              setShowResults(false);
              setResults(null);
              setCurrentStep(1);
              setFormData({
                industries: [],
                country: '',
                professions: [],
                productTypes: [],
                targetCustomers: [],
                impactFocus: '',
                customValues: {
                  industries: [],
                  professions: [],
                  productTypes: [],
                  targetCustomers: [],
                  impactFocus: ''
                }
              });
              setGenerationState({
                status: 'idle',
                progress: 0,
                message: ''
              });
            }}
            variant="outline"
            className="flex items-center gap-2 bg-brand-500 text-white px-8 dark:bg-brand-500 dark:hover:bg-brand-400 dark:border-brand-500"
          >
            Generate New Problems
          </Button>
        </div>
      </motion.div>
    );
  };

  const renderLoadingState = () => {
    const timeElapsed = generationState.startTime ? Math.round((Date.now() - generationState.startTime) / 1000) : 0;
    
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-center space-y-4"
      >
        <div className="flex justify-center">
          <div className="relative">
            <Loader2 className="w-16 h-16 text-brand-500 dark:text-brand-400 animate-spin" />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xs font-medium text-brand-600 dark:text-brand-300">
                {Math.round(generationState.progress)}%
              </span>
            </div>
          </div>
        </div>
        
        <div>
          <h3 className="text-xl font-semibold text-brand-700 dark:text-brand-300">
            Generating Your Problems
          </h3>
        </div>

        <div className="max-w-md mx-auto space-y-2">
          <Progress value={generationState.progress} className="h-2 dark:bg-gray-800" />
          <p className="text-xs text-muted-foreground dark:text-gray-400">
            This may take a few minutes. Please don't close this window.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-4 max-w-sm mx-auto text-center">
          <div className="space-y-2">
            <div className={cn(
              "w-8 h-8 rounded-full mx-auto flex items-center justify-center",
              generationState.progress >= 10 ? "bg-brand-500 text-white dark:bg-brand-400" : "bg-gray-200 text-gray-400 dark:bg-gray-700 dark:text-gray-500"
            )}>
              <CheckCircle className="w-4 h-4" />
            </div>
            <p className="text-xs text-muted-foreground dark:text-gray-400">
              Analyzing
            </p>
          </div>
          <div className="space-y-2">
            <div className={cn(
              "w-8 h-8 rounded-full mx-auto flex items-center justify-center",
              generationState.progress >= 50 ? "bg-brand-500 text-white dark:bg-brand-400" : "bg-gray-200 text-gray-400 dark:bg-gray-700 dark:text-gray-500"
            )}>
              <Zap className="w-4 h-4" />
            </div>
            <p className="text-xs text-muted-foreground dark:text-gray-400">
              Processing
            </p>
          </div>
          <div className="space-y-2">
            <div className={cn(
              "w-8 h-8 rounded-full mx-auto flex items-center justify-center",
              generationState.progress >= 100 ? "bg-brand-500 text-white dark:bg-brand-400" : "bg-gray-200 text-gray-400 dark:bg-gray-700 dark:text-gray-500"
            )}>
              <Lightbulb className="w-4 h-4" />
            </div>
            <p className="text-xs text-muted-foreground dark:text-gray-400">
              Finalizing
            </p>
          </div>
        </div>
      </motion.div>
    );
  };

  const handleStepClick = useCallback((step: number) => {
    // Only allow navigation to completed steps or current step
    if (step <= currentStep || isStepValid(step - 1)) {
      setCurrentStep(step);
      setHasAttemptedSubmit(false);
    }
  }, [currentStep]);

  const isStepClickable = useCallback((step: number) => {
    if (step === currentStep) return false; // Current step is not clickable
    if (step > currentStep) return false; // Future steps are not clickable
    
    // Check if all previous steps are valid
    for (let i = 1; i < step; i++) {
      if (!isStepValid(i)) return false;
    }
    return true;
  }, [currentStep]);

  if (showResults) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        {renderResults()}
      </div>
    );
  }

  if (generationState.status === 'submitting' || generationState.status === 'processing') {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <Card className="shadow-md dark:bg-gray-900/50 dark:border-gray-800">
          <CardContent className="p-8">
            {renderLoadingState()}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-4">
      <Card className="shadow-md p-4 dark:bg-gray-900/50 dark:border-gray-800">
        <CardHeader>
          <p className="text-sm text-brand-500 dark:text-brand-400 sm:text-base text-center mb-4">
            Let's now walk with you to identify the problems you want to work on.
          </p>
          {/* Progress Steps */}
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              {[1, 2, 3, 4, 5, 6].map((step) => {
                const isClickable = isStepClickable(step);
                const isCompleted = step < currentStep && isStepValid(step);
                const isCurrent = step === currentStep;
                
                return (
                  <div key={step} className="flex flex-col items-center space-y-2">
                    <div
                      className={cn(
                        "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all duration-200",
                        isCurrent
                          ? "bg-brand-500 text-white shadow-sm ring-2 ring-brand-200 dark:ring-brand-400/50"
                          : isCompleted
                          ? "bg-brand-600 text-white shadow-sm cursor-pointer hover:bg-brand-700 hover:scale-105 dark:bg-brand-500 dark:hover:bg-brand-400"
                          : "bg-muted text-muted-foreground border-2 border-muted dark:bg-gray-800 dark:border-gray-700 dark:text-gray-400",
                        isClickable && "cursor-pointer hover:shadow-md dark:hover:shadow-brand-500/20"
                      )}
                      onClick={() => isClickable && handleStepClick(step)}
                      aria-current={isCurrent ? "step" : undefined}
                      role={isClickable ? "button" : undefined}
                      tabIndex={isClickable ? 0 : -1}
                      onKeyDown={(e) => {
                        if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
                          e.preventDefault();
                          handleStepClick(step);
                        }
                      }}
                      title={isClickable ? `Go to ${stepLabels[step - 1]} step` : undefined}
                    >
                      {React.createElement(STEP_ICONS[step - 1], { 
                        className: "w-4 h-4" 
                      })}
                    </div>
                    <span 
                      className={cn(
                        "text-xs font-medium transition-colors",
                        isCurrent 
                          ? "text-brand-600 dark:text-brand-400 font-semibold" 
                          : isCompleted
                          ? "text-brand-500 dark:text-brand-300"
                          : "text-muted-foreground dark:text-gray-500",
                        isClickable && "cursor-pointer hover:text-brand-600 dark:hover:text-brand-400"
                      )}
                      onClick={() => isClickable && handleStepClick(step)}
                      role={isClickable ? "button" : undefined}
                      tabIndex={isClickable ? 0 : -1}
                      onKeyDown={(e) => {
                        if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
                          e.preventDefault();
                          handleStepClick(step);
                        }
                      }}
                      title={isClickable ? `Go to ${stepLabels[step - 1]} step` : undefined}
                    >
                      {stepLabels[step - 1]}
                    </span>
                  </div>
                );
              })}
            </div>
            <Progress 
              value={(currentStep / 6) * 100} 
              className="h-2 dark:bg-gray-800"
              aria-label={`Step ${currentStep} of 6`}
            />
          </div>
        </CardHeader>

        <CardContent className="space-y-2">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
            >
              {renderStep()}
            </motion.div>
          </AnimatePresence>

          {/* Navigation */}
          <div className="flex justify-between items-center pt-6 border-t dark:border-gray-800">
            <Button
              type="button"
              variant="outline"
              onClick={handleBack}
              disabled={currentStep === 1 || generationState.status === 'submitting'}
              className="flex items-center gap-2 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-white"
            >
              <ChevronLeft className="w-4 h-4" />
              Back
            </Button>
            
            <div className="text-sm text-muted-foreground dark:text-gray-400">
              Step {currentStep} of 6
            </div>

            <Button
              type="button"
              onClick={handleNext}
              disabled={generationState.status === 'submitting' || !isStepValid(currentStep)}
              className={cn(
                "flex items-center gap-2 bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-400",
                !isStepValid(currentStep) && "opacity-50 cursor-not-allowed"
              )}
            >
              {currentStep === 6 ? (
                'Generate Problems'
              ) : (
                <>
                  Next
                  <ChevronRight className="w-4 h-4" />
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
      
      {/* Insufficient Credits Modal */}
      <InsufficientCreditsModal
        isOpen={isInsufficientCreditsModalOpen}
        onClose={handleCloseInsufficientCreditsModal}
        title="Insufficient Credits"
        description="You don't have enough credits to generate problems. Please purchase more credits to continue."
        buttonText1="Request Credit"
        buttonText2="Close"
      />
    </div>
  );
};

export default OnboardingForm;