'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { toast } from 'sonner';
import { Loader2, Users, ChevronDown, Search, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogOverlay,
  DialogPortal,
} from '@/components/ui/dialog';
import { COUNTRY_CODES, COUNTRIES_LIST } from '@/lib/countryCodes';

// ============================================================================
// Enum Options
// ============================================================================

const COACHING_EXPERIENCE_OPTIONS = [
  { value: 'none', label: 'No formal experience' },
  { value: '1-2_years', label: '1-2 years' },
  { value: '3-5_years', label: '3-5 years' },
  { value: '5+_years', label: '5+ years' },
];

const WEEKLY_AVAILABILITY_OPTIONS = [
  { value: '2_hrs', label: 'Up to 2 hours' },
  { value: '4_hrs', label: 'Up to 4 hours' },
  { value: '6_hrs', label: 'Up to 6 hours' },
  { value: '8_hrs', label: 'Up to 8 hours' },
  { value: '10_hrs', label: 'Up to 10 hours' },
  { value: 'other', label: 'Other (specify)' },
];

const SUPPORT_AREAS_OPTIONS = [
  { value: 'generalist', label: 'Generalist' },
  { value: 'product_development', label: 'Product Development' },
  { value: 'software_development', label: 'Software Development' },
  { value: 'hardware_development', label: 'Hardware Development' },
  { value: 'strategy', label: 'Strategy' },
  { value: 'management_practices', label: 'Management Practices' },
  { value: 'legal', label: 'Legal' },
  { value: 'execution', label: 'Execution' },
  { value: 'other', label: 'Other' },
];

const INDUSTRIES_OPTIONS = [
  { value: 'generalist', label: 'Generalist' },
  { value: 'financial_systems', label: 'Financial Systems' },
  { value: 'healthcare_systems', label: 'Healthcare Systems' },
  { value: 'agriculture', label: 'Agriculture' },
  { value: 'food_systems', label: 'Food Systems' },
  { value: 'education', label: 'Education' },
  { value: 'climate_action', label: 'Climate Action' },
  { value: 'logistics', label: 'Logistics' },
  { value: 'consumer_tech', label: 'Consumer Tech' },
  { value: 'fmcg', label: 'FMCGs' },
  { value: 'construction', label: 'Construction' },
  { value: 'transportation', label: 'Transportation' },
  { value: 'artificial_intelligence', label: 'Artificial Intelligence' },
  { value: 'conservation', label: 'Conservation' },
  { value: 'legal', label: 'Legal' },
  { value: 'telecommunication', label: 'Telecommunication' },
  { value: 'other', label: 'Other' },
];

const FOUNDER_STAGES_OPTIONS = [
  { value: 'all', label: 'All Stages' },
  { value: 'early_stage', label: 'Early Stage (Pre-revenue)' },
  { value: 'post_pmf', label: 'Post Product-Market Fit' },
  { value: 'growth', label: 'Growth' },
  { value: 'scale', label: 'Scale' },
  { value: 'exit', label: 'Exit' },
  { value: 'other', label: 'Other' },
];

// All founder stages except 'all' and 'other'
const ALL_FOUNDER_STAGES = ['early_stage', 'post_pmf', 'growth', 'scale', 'exit'];

const GEOGRAPHIES_OPTIONS = [
  { value: 'africa_wide', label: 'Whole Africa' },
  { value: 'east_africa', label: 'East Africa' },
  { value: 'west_africa', label: 'West Africa' },
  { value: 'north_africa', label: 'North Africa' },
  { value: 'southern_africa', label: 'Southern Africa' },
  { value: 'specific_countries', label: 'Other (specify country)' },
];

const LANGUAGES_OPTIONS = [
  { value: 'english', label: 'English' },
  { value: 'french', label: 'French' },
  { value: 'swahili', label: 'Swahili' },
  { value: 'arabic', label: 'Arabic' },
  { value: 'amharic', label: 'Amharic' },
  { value: 'igbo', label: 'Igbo' },
  { value: 'zulu', label: 'Zulu' },
  { value: 'lingala', label: 'Lingala' },
  { value: 'kinyarwanda', label: 'Kinyarwanda' },
  { value: 'luganda', label: 'Luganda' },
  { value: 'portuguese', label: 'Portuguese' },
  { value: 'other', label: 'Other' },
];

// Selection limits for multi-select fields
const SELECTION_LIMITS: Record<string, number> = {
  supportAreas: 2,
  industriesOfFocus: 3,
  // founderStages: 2,
  geographies: 1,
  languages: 3,
};

// ============================================================================
// Component Props & Form State
// ============================================================================

interface VentureBuilderInterestModalProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

interface FormState {
  fullName: string;
  workEmail: string;
  countryCode: string;
  phoneNumber: string;
  countryOfResidence: string;
  city: string;
  currentRole: string;
  companyOrganization: string;
  linkedinUrl: string;
  personalWebsite: string;
  hasFoundedVenture: boolean | null;
  venturesFoundedCount: string;
  venturesStageReached: string;
  venturesOutcome: string;
  coachingExperience: string;
  programsWorkedWith: string;
  supportAreas: string[];
  supportAreasOther: string;
  industriesOfFocus: string[];
  industriesOther: string;
  founderStages: string[];
  founderStagesOther: string;
  geographies: string[];
  geographiesSpecificCountries: string;
  languages: string[];
  languagesOther: string;
  weeklyAvailability: string;
  weeklyAvailabilityOther: string;
  hourlyRateUsd: string;
}

const initialFormState: FormState = {
  fullName: '', workEmail: '', countryCode: 'KE', phoneNumber: '', countryOfResidence: '', city: '',
  currentRole: '', companyOrganization: '', linkedinUrl: '', personalWebsite: '',
  hasFoundedVenture: null, venturesFoundedCount: '', venturesStageReached: '', venturesOutcome: '',
  coachingExperience: '', programsWorkedWith: '', supportAreas: [], supportAreasOther: '',
  industriesOfFocus: [], industriesOther: '', founderStages: [], founderStagesOther: '',
  geographies: [], geographiesSpecificCountries: '', languages: [], languagesOther: '',
  weeklyAvailability: '', weeklyAvailabilityOther: '', hourlyRateUsd: '',
};

interface ValidationErrors { [key: string]: string; }

// URL normalization and validation helpers
const normalizeUrl = (url: string): string => {
  const trimmed = url.trim();
  if (!trimmed) return '';
  // Add https:// if no protocol present
  if (!/^https?:\/\//i.test(trimmed)) {
    return `https://${trimmed}`;
  }
  return trimmed;
};

const isValidUrl = (url: string): boolean => {
  if (!url.trim()) return true; // Empty is valid (for optional fields)
  const normalized = normalizeUrl(url);
  try {
    const parsed = new URL(normalized);
    // Must have a valid hostname with at least one dot (domain.tld)
    return parsed.hostname.includes('.') && parsed.hostname.length > 2;
  } catch {
    if (process.env.NODE_ENV === 'development') {
      console.log('[URL Validation] Failed to parse:', url);
    }
    return false;
  }
};

const validateForm = (form: FormState): ValidationErrors => {
  const errors: ValidationErrors = {};
  
  // Defensive helpers
  const safeArray = (arr: unknown): string[] => Array.isArray(arr) ? arr : [];
  const safeString = (str: unknown): string => typeof str === 'string' ? str : '';
  
  if (!safeString(form.fullName).trim()) errors.fullName = 'Full name is required';
  if (!safeString(form.workEmail).trim()) errors.workEmail = 'Work email is required';
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.workEmail)) errors.workEmail = 'Invalid email';
  if (!safeString(form.phoneNumber).trim()) errors.phoneNumber = 'Phone number is required';
  if (!safeString(form.countryOfResidence).trim()) errors.countryOfResidence = 'Country is required';
  if (!safeString(form.city).trim()) errors.city = 'City is required';
  if (!safeString(form.currentRole).trim()) errors.currentRole = 'Current role is required';
  if (!safeString(form.companyOrganization).trim()) errors.companyOrganization = 'Company is required';
  if (!safeString(form.linkedinUrl).trim()) errors.linkedinUrl = 'LinkedIn URL is required';
  else if (!isValidUrl(form.linkedinUrl)) errors.linkedinUrl = 'Please enter a valid link (e.g., linkedin.com/in/name)';
  // Personal website is optional, but validate if provided
  if (safeString(form.personalWebsite).trim() && !isValidUrl(form.personalWebsite)) {
    errors.personalWebsite = 'Please enter a valid link (e.g., example.com or https://example.com)';
  }
  if (form.hasFoundedVenture === null) errors.hasFoundedVenture = 'Please select an option';
  if (form.hasFoundedVenture === true) {
    if (!safeString(form.venturesFoundedCount)) errors.venturesFoundedCount = 'Required';
    if (!safeString(form.venturesStageReached).trim()) errors.venturesStageReached = 'Required';
    if (!safeString(form.venturesOutcome).trim()) errors.venturesOutcome = 'Required';
  }
  if (!form.coachingExperience) errors.coachingExperience = 'Required';
  
  // Multi-select fields with defensive array checks
  const supportAreas = safeArray(form.supportAreas);
  if (supportAreas.length === 0) errors.supportAreas = 'Select at least one';
  if (supportAreas.includes('other') && !safeString(form.supportAreasOther).trim()) errors.supportAreasOther = 'Required';
  
  const industries = safeArray(form.industriesOfFocus);
  if (industries.length === 0) errors.industriesOfFocus = 'Select at least one';
  if (industries.includes('other') && !safeString(form.industriesOther).trim()) errors.industriesOther = 'Required';
  
  const stages = safeArray(form.founderStages);
  if (stages.length === 0) errors.founderStages = 'Select at least one';
  if (stages.includes('other') && !safeString(form.founderStagesOther).trim()) errors.founderStagesOther = 'Required';
  
  const geos = safeArray(form.geographies);
  if (geos.length === 0) errors.geographies = 'Select at least one';
  
  const langs = safeArray(form.languages);
  if (langs.length === 0) errors.languages = 'Select at least one';
  if (langs.includes('other') && !safeString(form.languagesOther).trim()) errors.languagesOther = 'Required';
  
  if (!form.weeklyAvailability) errors.weeklyAvailability = 'Required';
  if (form.weeklyAvailability === 'other' && !safeString(form.weeklyAvailabilityOther).trim()) errors.weeklyAvailabilityOther = 'Required';
  if (!safeString(form.hourlyRateUsd).trim()) errors.hourlyRateUsd = 'Required';
  else { const rate = parseFloat(form.hourlyRateUsd); if (isNaN(rate) || rate < 0 || rate > 10000) errors.hourlyRateUsd = '0-10000 USD'; }
  return errors;
};

// ============================================================================
// Reusable Components
// ============================================================================

function SelectField({ id, label, value, onChange, options, placeholder, error, disabled, required = true }: {
  id: string; label: string; value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[]; placeholder: string; error?: string; disabled?: boolean; required?: boolean;
}) {
  return (
    <div className="space-y-1">
      <Label htmlFor={id} className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">
        {label} {required && <span className="text-red-500">*</span>}
        {!required && <span className="text-gray-400 text-[10px] lowercase tracking-normal">(optional)</span>}
      </Label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled}
        className={`w-full h-10 px-3 rounded-lg border bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm transition-all focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 disabled:opacity-50 ${error ? 'border-red-400' : 'border-gray-200 dark:border-gray-700'}`}>
        <option value="">{placeholder}</option>
        {options.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
      </select>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}

function SearchableSelectField({ id, label, value, onChange, options, placeholder, error, disabled, required = true }: {
  id: string; label: string; value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[]; placeholder: string; error?: string; disabled?: boolean; required?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);
  const selectedOption = options.find(o => o.value === value);
  const filtered = options.filter(o => o.label.toLowerCase().includes(search.toLowerCase()));

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setSearch('');
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div className="space-y-1">
      <Label htmlFor={id} className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">
        {label} {required && <span className="text-red-500">*</span>}
        {!required && <span className="text-gray-400 text-[10px] lowercase tracking-normal">(optional)</span>}
      </Label>
      <div className="relative" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
          className={`w-full h-10 px-3 rounded-lg border bg-white dark:bg-gray-900 text-left text-sm transition-all focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 disabled:opacity-50 flex items-center justify-between ${error ? 'border-red-400' : 'border-gray-200 dark:border-gray-700'}`}
        >
          <span className={selectedOption ? 'text-gray-900 dark:text-white' : 'text-gray-400'}>
            {selectedOption?.label || placeholder}
          </span>
          <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
        {isOpen && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl z-[200] overflow-hidden">
            <div className="p-2 border-b border-gray-100 dark:border-gray-800">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search..."
                  className="w-full h-8 pl-8 pr-3 text-sm rounded-md border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  autoFocus
                />
              </div>
            </div>
            <div className="max-h-48 overflow-y-auto">
              {filtered.length === 0 ? (
                <div className="px-3 py-2 text-sm text-gray-400">No results found</div>
              ) : (
                filtered.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => {
                      onChange(opt.value);
                      setIsOpen(false);
                      setSearch('');
                    }}
                    className={`w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-brand-50 dark:hover:bg-gray-800 transition-colors ${
                      value === opt.value ? 'bg-brand-50 dark:bg-brand-900/20 text-brand-600' : 'text-gray-700 dark:text-gray-300'
                    }`}
                  >
                    <span className="flex-1">{opt.label}</span>
                    {value === opt.value && <Check className="h-4 w-4 text-brand-500" />}
                  </button>
                ))
              )}
            </div>
          </div>
        )}
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}

function SimpleSelectField({ id, label, value, onChange, options, placeholder, error, disabled, required = true }: {
  id: string; label: string; value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[]; placeholder: string; error?: string; disabled?: boolean; required?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const selectedOption = options.find(o => o.value === value);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div className="space-y-1">
      <Label htmlFor={id} className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">
        {label} {required && <span className="text-red-500">*</span>}
        {!required && <span className="text-gray-400 text-[10px] lowercase tracking-normal">(optional)</span>}
      </Label>
      <div className="relative" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
          className={`w-full h-10 px-3 rounded-lg border bg-white dark:bg-gray-900 text-left text-sm transition-all focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 disabled:opacity-50 flex items-center justify-between ${error ? 'border-red-400' : 'border-gray-200 dark:border-gray-700'}`}
        >
          <span className={selectedOption ? 'text-gray-900 dark:text-white' : 'text-gray-400'}>
            {selectedOption?.label || placeholder}
          </span>
          <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
        {isOpen && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl z-[200] overflow-hidden">
            <div className="max-h-48 overflow-y-auto">
              {options.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => {
                    onChange(opt.value);
                    setIsOpen(false);
                  }}
                  className={`w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-brand-50 dark:hover:bg-gray-800 transition-colors ${
                    value === opt.value ? 'bg-brand-50 dark:bg-brand-900/20 text-brand-600' : 'text-gray-700 dark:text-gray-300'
                  }`}
                >
                  <span className="flex-1">{opt.label}</span>
                  {value === opt.value && <Check className="h-4 w-4 text-brand-500" />}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}

function InputField({ id, label, value, onChange, type = 'text', placeholder, error, disabled, required = true }: {
  id: string; label: string; value: string; onChange: (v: string) => void; type?: string;
  placeholder: string; error?: string; disabled?: boolean; required?: boolean;
}) {
  return (
    <div className="space-y-1">
      <Label htmlFor={id} className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">
        {label} {required && <span className="text-red-500">*</span>}
        {!required && <span className="text-gray-400 text-[10px] lowercase tracking-normal">(optional)</span>}
      </Label>
      <Input id={id} type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
        disabled={disabled} className={`h-10 ${error ? 'border-red-400' : ''}`} />
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}

function MultiSelectField({ id, label, value, onChange, options, error, disabled, maxSelections }: {
  id: string; label: string; value: string[]; onChange: (v: string[]) => void;
  options: { value: string; label: string }[]; error?: string; disabled?: boolean; maxSelections?: number;
}) {
  // Defensive: ensure value is always an array
  const safeValue = Array.isArray(value) ? value : [];
  const isAtLimit = maxSelections !== undefined && safeValue.length >= maxSelections;
  
  const toggle = (v: string) => {
    const isSelected = safeValue.includes(v);
    if (isSelected) {
      // Always allow deselection
      onChange(safeValue.filter(x => x !== v));
    } else {
      // Check limit before adding
      if (maxSelections !== undefined && safeValue.length >= maxSelections) {
        return; // Do not add if at limit
      }
      onChange([...safeValue, v]);
    }
  };

  return (
    <div className="space-y-2">
      <Label className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">
        {label} <span className="text-red-500">*</span>
        {maxSelections !== undefined && (
          <span className="text-gray-400 text-[10px] lowercase tracking-normal ml-1">(max {maxSelections})</span>
        )}
      {isAtLimit && !error && (
        <p className="text-[10px] text-amber-600 dark:text-amber-400">You can select up to {maxSelections} {maxSelections === 1 ? 'option' : 'options'}.</p>
      )} 
      </Label>
      <div className={`grid grid-cols-2 gap-2 p-3 rounded-lg border ${error ? 'border-red-400' : 'border-gray-200 dark:border-gray-700'} bg-white dark:bg-gray-900`}>
        {options.map((opt) => {
          const isSelected = safeValue.includes(opt.value);
          const isDisabledByLimit = !isSelected && isAtLimit;
          return (
            <label 
              key={opt.value} 
              className={`flex items-center gap-2 p-2 rounded-md transition-colors ${
                isSelected 
                  ? 'bg-brand-50 dark:bg-brand-900/20 text-brand-700 cursor-pointer' 
                  : isDisabledByLimit 
                    ? 'opacity-40 cursor-not-allowed' 
                    : 'hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer'
              } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <div className={`w-4 h-4 rounded border flex items-center justify-center ${isSelected ? 'bg-brand-500 border-brand-500' : 'border-gray-300'}`}>
                {isSelected && <Check className="w-3 h-3 text-white" />}
              </div>
              <input 
                type="checkbox" 
                checked={isSelected} 
                onChange={() => !disabled && !isDisabledByLimit && toggle(opt.value)} 
                disabled={disabled || isDisabledByLimit} 
                className="sr-only" 
              />
              <span className="text-sm">{opt.label}</span>
            </label>
          );
        })}
      </div>

      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}

function CountryCodePhoneInput({ countryCode, phoneNumber, onCountryCodeChange, onPhoneNumberChange, error, disabled }: {
  countryCode: string; phoneNumber: string; onCountryCodeChange: (c: string) => void;
  onPhoneNumberChange: (n: string) => void; error?: string; disabled?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);
  const selected = COUNTRY_CODES.find(c => c.code === countryCode) || COUNTRY_CODES[0];
  const filtered = COUNTRY_CODES.filter(c => c.name.toLowerCase().includes(search.toLowerCase()) || c.dialCode.includes(search));

  useEffect(() => {
    const handler = (e: MouseEvent) => { if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) { setIsOpen(false); setSearch(''); } };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div className="space-y-1">
      <Label className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">
        Country Code & Phone <span className="text-red-500">*</span>
      </Label>
      <div className="flex">
        <div className="relative" ref={dropdownRef}>
          <button type="button" onClick={() => !disabled && setIsOpen(!isOpen)} disabled={disabled}
            className="h-10 pl-2.5 pr-6 rounded-l-lg border border-r-0 border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-xs font-medium flex items-center gap-1.5 min-w-[95px]">
            <span>{selected?.code}</span><span className="text-gray-500">{selected?.dialCode}</span>
          </button>
          <ChevronDown className={`absolute right-1.5 top-1/2 -translate-y-1/2 h-3 w-3 text-gray-400 pointer-events-none ${isOpen ? 'rotate-180' : ''}`} />
          {isOpen && (
            <div className="absolute top-full left-0 mt-1 w-56 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl z-[200]">
              <div className="p-2 border-b border-gray-100 dark:border-gray-800">
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
                  <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search..."
                    className="w-full h-8 pl-8 pr-3 text-xs rounded-md border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800" />
                </div>
              </div>
              <div className="max-h-48 overflow-y-auto">
                {filtered.map((c) => (
                  <button key={c.code} type="button" onClick={() => { onCountryCodeChange(c.code); setIsOpen(false); setSearch(''); }}
                    className={`w-full px-3 py-1.5 text-left text-xs flex items-center gap-2 hover:bg-brand-50 dark:hover:bg-gray-800 ${countryCode === c.code ? 'bg-brand-50 text-brand-600' : 'text-gray-700'}`}>
                    <span className="w-6 text-[10px] text-gray-400 font-medium">{c.code}</span>
                    <span className="flex-1 truncate">{c.name}</span>
                    <span className="text-gray-400 font-mono text-[11px]">{c.dialCode}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
        <Input type="tel" value={phoneNumber} onChange={(e) => onPhoneNumberChange(e.target.value)} placeholder="712 345 678"
          disabled={disabled} className={`h-10 flex-1 rounded-l-none ${error ? 'border-red-400' : ''}`} />
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}

function BooleanField({ label, value, onChange, error, disabled }: {
  label: string; value: boolean | null; onChange: (v: boolean) => void; error?: string; disabled?: boolean;
}) {
  return (
    <div className="space-y-2">
      <Label className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">
        {label} <span className="text-red-500">*</span>
      </Label>
      <div className="flex gap-4">
        {[true, false].map((v) => (
          <label key={String(v)} className={`flex items-center gap-2 px-4 py-2 rounded-lg border cursor-pointer transition-all ${value === v ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20 text-brand-700' : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'} ${disabled ? 'opacity-50' : ''}`}>
            <input type="radio" checked={value === v} onChange={() => !disabled && onChange(v)} disabled={disabled} className="sr-only" />
            <div className={`w-4 h-4 rounded-full border flex items-center justify-center ${value === v ? 'border-brand-500 bg-brand-500' : 'border-gray-300'}`}>
              {value === v && <div className="w-2 h-2 rounded-full bg-white" />}
            </div>
            <span className="text-sm font-medium">{v ? 'Yes' : 'No'}</span>
          </label>
        ))}
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function VentureBuilderInterestModal({ isOpen, onOpenChange }: VentureBuilderInterestModalProps) {
  const [form, setForm] = useState<FormState>(initialFormState);
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCheckingStatus, setIsCheckingStatus] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [emailStatusError, setEmailStatusError] = useState<string | null>(null);

  const handleOpenChange = useCallback((open: boolean) => {
    if (!open) { setForm(initialFormState); setErrors({}); setSubmitSuccess(false); setEmailStatusError(null); }
    onOpenChange(open);
  }, [onOpenChange]);

  const updateField = useCallback(<K extends keyof FormState>(field: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors((prev) => { const n = { ...prev }; delete n[field]; return n; });
    if (field === 'workEmail') setEmailStatusError(null);
  }, [errors]);

  const checkEmailStatus = useCallback(async (email: string): Promise<boolean> => {
    try {
      setIsCheckingStatus(true);
      const res = await fetch(`/api/venture-builder/interest/status/${encodeURIComponent(email)}`);
      if (res.ok) { const data = await res.json(); if (data.exists || data.already_submitted) { setEmailStatusError('This email has already submitted an application.'); return false; } }
      return true;
    } catch { return true; } finally { setIsCheckingStatus(false); }
  }, []);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    const validationErrors = validateForm(form);
    if (Object.keys(validationErrors).length > 0) { setErrors(validationErrors); toast.error('Please fill in all required fields'); return; }
    const canSubmit = await checkEmailStatus(form.workEmail.trim().toLowerCase());
    if (!canSubmit) return;
    setIsSubmitting(true);
    try {
      const selected = COUNTRY_CODES.find(c => c.code === form.countryCode);
      const safeSupportAreas = Array.isArray(form.supportAreas) ? form.supportAreas : [];
      const safeIndustries = Array.isArray(form.industriesOfFocus) ? form.industriesOfFocus : [];
      const safeStagesRaw = Array.isArray(form.founderStages) ? form.founderStages : [];
      // Expand 'all' to individual stages for backend, exclude 'all' from payload
      const safeStages = safeStagesRaw.includes('all') 
        ? [...ALL_FOUNDER_STAGES, ...(safeStagesRaw.includes('other') ? ['other'] : [])]
        : safeStagesRaw.filter(s => s !== 'all');
      const safeGeos = Array.isArray(form.geographies) ? form.geographies : [];
      const safeLangs = Array.isArray(form.languages) ? form.languages : [];
      
      const payload = {
        full_name: form.fullName.trim(),
        work_email: form.workEmail.trim().toLowerCase(),
        phone_country_code: form.countryCode.toUpperCase(),
        phone_number: `${selected?.dialCode || ''} ${form.phoneNumber.trim()}`,
        country: form.countryOfResidence.trim(),
        city: form.city.trim(),
        primary_role: form.currentRole.trim(),
        company_organization: form.companyOrganization.trim() || null,
        linkedin_url: normalizeUrl(form.linkedinUrl),
        personal_website: form.personalWebsite.trim() ? normalizeUrl(form.personalWebsite) : null,
        has_founded_venture: form.hasFoundedVenture!,
        ventures_founded_count: form.hasFoundedVenture ? parseInt(form.venturesFoundedCount) || null : null,
        ventures_stage_reached: form.hasFoundedVenture ? form.venturesStageReached.trim() || null : null,
        ventures_outcome: form.hasFoundedVenture ? form.venturesOutcome.trim() || null : null,
        coaching_experience: form.coachingExperience,
        programs_worked_with: form.programsWorkedWith.trim() || null,
        support_areas: safeSupportAreas,
        support_areas_other: safeSupportAreas.includes('other') ? form.supportAreasOther.trim() : null,
        industries_of_focus: safeIndustries,
        industries_other: safeIndustries.includes('other') ? form.industriesOther.trim() : null,
        founder_stages: safeStages,
        founder_stages_other: safeStages.includes('other') ? form.founderStagesOther.trim() : null,
        geographies: safeGeos,
        geographies_specific_countries: form.geographiesSpecificCountries.trim() || null,
        languages: safeLangs,
        languages_other: safeLangs.includes('other') ? form.languagesOther.trim() : null,
        weekly_availability: form.weeklyAvailability,
        weekly_availability_other: form.weeklyAvailability === 'other' ? form.weeklyAvailabilityOther.trim() : null,
        hourly_rate_usd: parseFloat(form.hourlyRateUsd),
      };
      const res = await fetch('/api/venture-builder/interest', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.message || err.detail || `Request failed (${res.status})`); }
      setSubmitSuccess(true);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to submit. Please try again.', { duration: 5000 });
    } finally { setIsSubmitting(false); }
  }, [form, checkEmailStatus]);

  // Safe array helpers for rendering
  const supportAreas = Array.isArray(form.supportAreas) ? form.supportAreas : [];
  const industriesOfFocus = Array.isArray(form.industriesOfFocus) ? form.industriesOfFocus : [];
  const founderStages = Array.isArray(form.founderStages) ? form.founderStages : [];
  const languages = Array.isArray(form.languages) ? form.languages : [];

  if (!isOpen) return null;

  // Success screen
  if (submitSuccess) {
    return (
      <div className="fixed inset-0 z-[100]">
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={() => handleOpenChange(false)} />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <div className="relative w-full max-w-md bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 p-8 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30 mx-auto mb-4">
              <Check className="h-8 w-8 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Application Submitted</h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">Your application is currently under review. Our team will reach out within 3-5 business days.</p>
            <Button onClick={() => handleOpenChange(false)} className="bg-brand-500 hover:bg-brand-600 text-white">Close</Button>
          </div>
        </div>
      </div>
    );
  }

  // Main form modal
  return (
    <div className="fixed inset-0 z-[100]">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={() => handleOpenChange(false)} />
      
      {/* Modal container - centered with fixed dimensions */}
      <div className="fixed inset-4 sm:inset-6 md:inset-8 lg:inset-12 flex items-center justify-center pointer-events-none">
        <div 
          className="relative w-full max-w-[720px] bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 pointer-events-auto"
          style={{ height: 'min(85vh, 800px)', display: 'flex', flexDirection: 'column' }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header - fixed height */}
          <div className="bg-gradient-to-r from-brand-500/5 via-brand-500/10 to-transparent px-6 py-5 border-b border-gray-100 dark:border-gray-800 rounded-t-2xl" style={{ flexShrink: 0 }}>
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-500 shadow-lg shadow-brand-500/25">
                <Users className="h-5 w-5 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Venture Builder Expression of Interest</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">Join our network of experienced venture builders</p>
              </div>
            </div>
          </div>

          {/* Scrollable content area */}
          <div className="px-6 py-5" style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
            <form id="venture-builder-form" onSubmit={handleSubmit} className="space-y-6">
              {/* Personal Information */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">Personal Information</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <InputField id="fullName" label="Full Name" value={form.fullName} onChange={(v) => updateField('fullName', v)} placeholder="John Doe" error={errors.fullName} disabled={isSubmitting} />
                  <InputField id="workEmail" label="Work Email" type="email" value={form.workEmail} onChange={(v) => updateField('workEmail', v)} placeholder="john@company.com" error={errors.workEmail || emailStatusError || undefined} disabled={isSubmitting} />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <CountryCodePhoneInput countryCode={form.countryCode} phoneNumber={form.phoneNumber} onCountryCodeChange={(c) => updateField('countryCode', c)} onPhoneNumberChange={(n) => updateField('phoneNumber', n)} error={errors.phoneNumber} disabled={isSubmitting} />
                  <SearchableSelectField id="countryOfResidence" label="Country of Residence" value={form.countryOfResidence} onChange={(v) => updateField('countryOfResidence', v)} options={COUNTRIES_LIST.map(c => ({ value: c, label: c }))} placeholder="Select country..." error={errors.countryOfResidence} disabled={isSubmitting} />
                </div>
                <InputField id="city" label="City" value={form.city} onChange={(v) => updateField('city', v)} placeholder="Nairobi" error={errors.city} disabled={isSubmitting} />
              </div>

              {/* Professional Profile */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">Professional Profile</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <InputField id="currentRole" label="Current Role" value={form.currentRole} onChange={(v) => updateField('currentRole', v)} placeholder="Startup Advisor" error={errors.currentRole} disabled={isSubmitting} />
                  <InputField id="companyOrganization" label="Company or Organization" value={form.companyOrganization} onChange={(v) => updateField('companyOrganization', v)} placeholder="Acme Ventures" error={errors.companyOrganization} disabled={isSubmitting} />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <InputField id="linkedinUrl" label="LinkedIn Profile URL" value={form.linkedinUrl} onChange={(v) => updateField('linkedinUrl', v)} placeholder="linkedin.com/in/johndoe" error={errors.linkedinUrl} disabled={isSubmitting} />
                  <InputField id="personalWebsite" label="Personal Website" value={form.personalWebsite} onChange={(v) => updateField('personalWebsite', v)} placeholder="johndoe.com" error={errors.personalWebsite} disabled={isSubmitting} required={false} />
                </div>
              </div>

              {/* Venture Building Experience */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">Venture Building Experience</h3>
                <BooleanField label="Have you founded or co-founded a venture?" value={form.hasFoundedVenture} onChange={(v) => updateField('hasFoundedVenture', v)} error={errors.hasFoundedVenture} disabled={isSubmitting} />
                {form.hasFoundedVenture === true && (
                  <div className="space-y-3 pl-4 border-l-2 border-brand-200 dark:border-brand-800">
                    <InputField id="venturesFoundedCount" label="Number of Ventures Founded" type="number" value={form.venturesFoundedCount} onChange={(v) => updateField('venturesFoundedCount', v)} placeholder="1" error={errors.venturesFoundedCount} disabled={isSubmitting} />
                    <InputField id="venturesStageReached" label="Highest Venture Stage Reached" value={form.venturesStageReached} onChange={(v) => updateField('venturesStageReached', v)} placeholder="e.g., Seed, Series A, Series B, etc." error={errors.venturesStageReached} disabled={isSubmitting} />
                    <InputField id="venturesOutcome" label="Current Venture(s) Status" value={form.venturesOutcome} onChange={(v) => updateField('venturesOutcome', v)} placeholder="e.g., Operating, Exited" error={errors.venturesOutcome} disabled={isSubmitting} />
                  </div>
                )}
                <SimpleSelectField id="coachingExperience" label="Coaching/Mentoring Experience" value={form.coachingExperience} onChange={(v) => updateField('coachingExperience', v)} options={COACHING_EXPERIENCE_OPTIONS} placeholder="Select experience level..." error={errors.coachingExperience} disabled={isSubmitting} />
                <InputField id="programsWorkedWith" label="Programs Worked With" value={form.programsWorkedWith} onChange={(v) => updateField('programsWorkedWith', v)} placeholder="e.g., Y Combinator, Techstars" error={errors.programsWorkedWith} disabled={isSubmitting} required={false} />
              </div>

              {/* Expertise & Coverage */}
              <div className="space-y-4">
                <h3 className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">Expertise & Coverage</h3>
                
                <MultiSelectField id="supportAreas" label="Areas You Can Support Founders On" value={form.supportAreas} onChange={(v) => updateField('supportAreas', v)} options={SUPPORT_AREAS_OPTIONS} error={errors.supportAreas} disabled={isSubmitting} maxSelections={SELECTION_LIMITS.supportAreas} />
                {supportAreas.includes('other') && (
                  <InputField id="supportAreasOther" label="Other Support Areas" value={form.supportAreasOther} onChange={(v) => updateField('supportAreasOther', v)} placeholder="Specify..." error={errors.supportAreasOther} disabled={isSubmitting} />
                )}
                
                <MultiSelectField id="industriesOfFocus" label="Industries of Focus" value={form.industriesOfFocus} onChange={(v) => updateField('industriesOfFocus', v)} options={INDUSTRIES_OPTIONS} error={errors.industriesOfFocus} disabled={isSubmitting} maxSelections={SELECTION_LIMITS.industriesOfFocus} />
                {industriesOfFocus.includes('other') && (
                  <InputField id="industriesOther" label="Other Industries" value={form.industriesOther} onChange={(v) => updateField('industriesOther', v)} placeholder="Specify..." error={errors.industriesOther} disabled={isSubmitting} />
                )}
                
                <MultiSelectField 
                  id="founderStages" 
                  label="Founder Stages You Work Best With" 
                  value={form.founderStages} 
                  onChange={(v) => {
                    // Handle 'all' selection logic
                    const prevHadAll = form.founderStages.includes('all');
                    const newHasAll = v.includes('all');
                    
                    if (!prevHadAll && newHasAll) {
                      // User just selected 'all' - select all stages (keep 'other' if it was selected)
                      const hasOther = v.includes('other');
                      updateField('founderStages', hasOther ? ['all', ...ALL_FOUNDER_STAGES, 'other'] : ['all', ...ALL_FOUNDER_STAGES]);
                    } else if (prevHadAll && !newHasAll) {
                      // User deselected 'all' - clear all stages except 'other'
                      updateField('founderStages', v.filter(s => s === 'other'));
                    } else if (newHasAll && v.length < ALL_FOUNDER_STAGES.length + 1 + (v.includes('other') ? 1 : 0)) {
                      // User has 'all' but deselected a stage - remove 'all'
                      updateField('founderStages', v.filter(s => s !== 'all'));
                    } else {
                      // Check if all individual stages are now selected, auto-add 'all'
                      const individualStages = v.filter(s => s !== 'all' && s !== 'other');
                      if (individualStages.length === ALL_FOUNDER_STAGES.length && ALL_FOUNDER_STAGES.every(s => individualStages.includes(s))) {
                        updateField('founderStages', ['all', ...v.filter(s => s !== 'all')]);
                      } else {
                        updateField('founderStages', v);
                      }
                    }
                  }} 
                  options={FOUNDER_STAGES_OPTIONS} 
                  error={errors.founderStages} 
                  disabled={isSubmitting} 
                />
                {founderStages.includes('other') && (
                  <InputField id="founderStagesOther" label="Other Stages" value={form.founderStagesOther} onChange={(v) => updateField('founderStagesOther', v)} placeholder="Specify..." error={errors.founderStagesOther} disabled={isSubmitting} />
                )}
                
                <MultiSelectField id="geographies" label="Geographies you are familiar with" value={form.geographies} onChange={(v) => updateField('geographies', v)} options={GEOGRAPHIES_OPTIONS} error={errors.geographies} disabled={isSubmitting} maxSelections={SELECTION_LIMITS.geographies} />
                {form.geographies.includes('specific_countries') && (
                  <InputField id="geographiesSpecificCountries" label="Specify Countries" value={form.geographiesSpecificCountries} onChange={(v) => updateField('geographiesSpecificCountries', v)} placeholder="e.g., Kenya, Nigeria, Ghana" error={errors.geographiesSpecificCountries} disabled={isSubmitting} />
                )}
                {/* <InputField id="geographiesSpecificCountries" label="Specific Countries" value={form.geographiesSpecificCountries} onChange={(v) => updateField('geographiesSpecificCountries', v)} placeholder="e.g., Kenya, Nigeria" error={errors.geographiesSpecificCountries} disabled={isSubmitting} required={false} /> */}
                
                <MultiSelectField id="languages" label="Languages You're Comfortable With" value={form.languages} onChange={(v) => updateField('languages', v)} options={LANGUAGES_OPTIONS} error={errors.languages} disabled={isSubmitting} maxSelections={SELECTION_LIMITS.languages} />
                {languages.includes('other') && (
                  <InputField id="languagesOther" label="Other Languages" value={form.languagesOther} onChange={(v) => updateField('languagesOther', v)} placeholder="Specify..." error={errors.languagesOther} disabled={isSubmitting} />
                )}
                
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <SimpleSelectField id="weeklyAvailability" label="Estimated Weekly Availability" value={form.weeklyAvailability} onChange={(v) => updateField('weeklyAvailability', v)} options={WEEKLY_AVAILABILITY_OPTIONS} placeholder="Select..." error={errors.weeklyAvailability} disabled={isSubmitting} />
                  <InputField id="hourlyRateUsd" label="Hourly Rate (USD)" type="number" value={form.hourlyRateUsd} onChange={(v) => updateField('hourlyRateUsd', v)} placeholder="50" error={errors.hourlyRateUsd} disabled={isSubmitting} />
                </div>
                {form.weeklyAvailability === 'other' && (
                  <InputField id="weeklyAvailabilityOther" label="Specify Availability" value={form.weeklyAvailabilityOther} onChange={(v) => updateField('weeklyAvailabilityOther', v)} placeholder="e.g., 15 hrs/week" error={errors.weeklyAvailabilityOther} disabled={isSubmitting} />
                )}
              </div>
            </form>
          </div>

          {/* Footer - fixed at bottom */}
          <div className="px-6 py-4 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/50 rounded-b-2xl" style={{ flexShrink: 0 }}>
            <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3">
              <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={isSubmitting || isCheckingStatus} className="w-full sm:w-auto h-10">
                Cancel
              </Button>
              <Button type="submit" form="venture-builder-form" disabled={isSubmitting || isCheckingStatus} className="w-full sm:w-auto h-10 bg-brand-500 hover:bg-brand-600 text-white shadow-lg shadow-brand-500/25">
                {isSubmitting || isCheckingStatus ? (<><Loader2 className="w-4 h-4 animate-spin mr-2" />Submitting...</>) : 'Submit Application'}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
