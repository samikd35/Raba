'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { toast } from 'sonner';
import { Loader2, Building2, ChevronDown, Search } from 'lucide-react';
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

// ============================================================================
// Types matching API contract exactly
// ============================================================================

interface OrganizationLocation {
  country: string;
  city: string;
}

interface Organization {
  name: string;
  type: string;
  size: string;
  location: OrganizationLocation;
}

interface DemoRequestMetadata {
  requested_tier: string;
  source: string;
}

interface DemoRequestPayload {
  demo_request: {
    full_name: string;
    email: string;
    phone_number: string;
    job_title: string;
    organization: Organization;
    expected_users: string;
    additional_notes: string;
    metadata: DemoRequestMetadata;
    submitted_at: string;
  };
}

// ============================================================================
// Form field options
// ============================================================================

const ORGANIZATION_SIZES = [
  { value: '1-10', label: '1-10 employees' },
  { value: '11-50', label: '11-50 employees' },
  { value: '51-200', label: '51-200 employees' },
  { value: '201-500', label: '201-500 employees' },
  { value: '501-1000', label: '501-1000 employees' },
  { value: '1000+', label: '1000+ employees' },
];

const ORGANIZATION_TYPES = [
  { value: 'accelerator', label: 'Accelerator' },
  { value: 'incubator', label: 'Incubator' },
  { value: 'venture_studio', label: 'Venture Studio' },
  { value: 'corporate', label: 'Corporate Innovation' },
  { value: 'university', label: 'University / Academic' },
  { value: 'government', label: 'Government Agency' },
  { value: 'ngo', label: 'NGO / Non-profit' },
  { value: 'investment_fund', label: 'Investment Fund / VC' },
  { value: 'other', label: 'Other' },
];

const EXPECTED_USERS_OPTIONS = [
  { value: '1-10', label: '1-10 users' },
  { value: '11-50', label: '11-50 users' },
  { value: '51-200', label: '51-200 users' },
  { value: '201-500', label: '201-500 users' },
  { value: '500+', label: '500+ users' },
];

const COUNTRY_CODES = [
  { code: '+93', country: 'AF', name: 'Afghanistan' },
  { code: '+355', country: 'AL', name: 'Albania' },
  { code: '+213', country: 'DZ', name: 'Algeria' },
  { code: '+376', country: 'AD', name: 'Andorra' },
  { code: '+244', country: 'AO', name: 'Angola' },
  { code: '+54', country: 'AR', name: 'Argentina' },
  { code: '+374', country: 'AM', name: 'Armenia' },
  { code: '+61', country: 'AU', name: 'Australia' },
  { code: '+43', country: 'AT', name: 'Austria' },
  { code: '+994', country: 'AZ', name: 'Azerbaijan' },
  { code: '+973', country: 'BH', name: 'Bahrain' },
  { code: '+880', country: 'BD', name: 'Bangladesh' },
  { code: '+375', country: 'BY', name: 'Belarus' },
  { code: '+32', country: 'BE', name: 'Belgium' },
  { code: '+229', country: 'BJ', name: 'Benin' },
  { code: '+975', country: 'BT', name: 'Bhutan' },
  { code: '+591', country: 'BO', name: 'Bolivia' },
  { code: '+387', country: 'BA', name: 'Bosnia' },
  { code: '+267', country: 'BW', name: 'Botswana' },
  { code: '+55', country: 'BR', name: 'Brazil' },
  { code: '+673', country: 'BN', name: 'Brunei' },
  { code: '+359', country: 'BG', name: 'Bulgaria' },
  { code: '+226', country: 'BF', name: 'Burkina Faso' },
  { code: '+257', country: 'BI', name: 'Burundi' },
  { code: '+855', country: 'KH', name: 'Cambodia' },
  { code: '+237', country: 'CM', name: 'Cameroon' },
  { code: '+1', country: 'CA', name: 'Canada' },
  { code: '+238', country: 'CV', name: 'Cape Verde' },
  { code: '+236', country: 'CF', name: 'Central African Rep.' },
  { code: '+235', country: 'TD', name: 'Chad' },
  { code: '+56', country: 'CL', name: 'Chile' },
  { code: '+86', country: 'CN', name: 'China' },
  { code: '+57', country: 'CO', name: 'Colombia' },
  { code: '+269', country: 'KM', name: 'Comoros' },
  { code: '+242', country: 'CG', name: 'Congo' },
  { code: '+243', country: 'CD', name: 'Congo (DRC)' },
  { code: '+506', country: 'CR', name: 'Costa Rica' },
  { code: '+225', country: 'CI', name: "Côte d'Ivoire" },
  { code: '+385', country: 'HR', name: 'Croatia' },
  { code: '+53', country: 'CU', name: 'Cuba' },
  { code: '+357', country: 'CY', name: 'Cyprus' },
  { code: '+420', country: 'CZ', name: 'Czech Republic' },
  { code: '+45', country: 'DK', name: 'Denmark' },
  { code: '+253', country: 'DJ', name: 'Djibouti' },
  { code: '+593', country: 'EC', name: 'Ecuador' },
  { code: '+20', country: 'EG', name: 'Egypt' },
  { code: '+503', country: 'SV', name: 'El Salvador' },
  { code: '+240', country: 'GQ', name: 'Equatorial Guinea' },
  { code: '+291', country: 'ER', name: 'Eritrea' },
  { code: '+372', country: 'EE', name: 'Estonia' },
  { code: '+268', country: 'SZ', name: 'Eswatini' },
  { code: '+251', country: 'ET', name: 'Ethiopia' },
  { code: '+679', country: 'FJ', name: 'Fiji' },
  { code: '+358', country: 'FI', name: 'Finland' },
  { code: '+33', country: 'FR', name: 'France' },
  { code: '+241', country: 'GA', name: 'Gabon' },
  { code: '+220', country: 'GM', name: 'Gambia' },
  { code: '+995', country: 'GE', name: 'Georgia' },
  { code: '+49', country: 'DE', name: 'Germany' },
  { code: '+233', country: 'GH', name: 'Ghana' },
  { code: '+30', country: 'GR', name: 'Greece' },
  { code: '+502', country: 'GT', name: 'Guatemala' },
  { code: '+224', country: 'GN', name: 'Guinea' },
  { code: '+245', country: 'GW', name: 'Guinea-Bissau' },
  { code: '+592', country: 'GY', name: 'Guyana' },
  { code: '+509', country: 'HT', name: 'Haiti' },
  { code: '+504', country: 'HN', name: 'Honduras' },
  { code: '+852', country: 'HK', name: 'Hong Kong' },
  { code: '+36', country: 'HU', name: 'Hungary' },
  { code: '+354', country: 'IS', name: 'Iceland' },
  { code: '+91', country: 'IN', name: 'India' },
  { code: '+62', country: 'ID', name: 'Indonesia' },
  { code: '+98', country: 'IR', name: 'Iran' },
  { code: '+964', country: 'IQ', name: 'Iraq' },
  { code: '+353', country: 'IE', name: 'Ireland' },
  { code: '+972', country: 'IL', name: 'Israel' },
  { code: '+39', country: 'IT', name: 'Italy' },
  { code: '+1876', country: 'JM', name: 'Jamaica' },
  { code: '+81', country: 'JP', name: 'Japan' },
  { code: '+962', country: 'JO', name: 'Jordan' },
  { code: '+7', country: 'KZ', name: 'Kazakhstan' },
  { code: '+254', country: 'KE', name: 'Kenya' },
  { code: '+965', country: 'KW', name: 'Kuwait' },
  { code: '+996', country: 'KG', name: 'Kyrgyzstan' },
  { code: '+856', country: 'LA', name: 'Laos' },
  { code: '+371', country: 'LV', name: 'Latvia' },
  { code: '+961', country: 'LB', name: 'Lebanon' },
  { code: '+266', country: 'LS', name: 'Lesotho' },
  { code: '+231', country: 'LR', name: 'Liberia' },
  { code: '+218', country: 'LY', name: 'Libya' },
  { code: '+423', country: 'LI', name: 'Liechtenstein' },
  { code: '+370', country: 'LT', name: 'Lithuania' },
  { code: '+352', country: 'LU', name: 'Luxembourg' },
  { code: '+853', country: 'MO', name: 'Macau' },
  { code: '+261', country: 'MG', name: 'Madagascar' },
  { code: '+265', country: 'MW', name: 'Malawi' },
  { code: '+60', country: 'MY', name: 'Malaysia' },
  { code: '+960', country: 'MV', name: 'Maldives' },
  { code: '+223', country: 'ML', name: 'Mali' },
  { code: '+356', country: 'MT', name: 'Malta' },
  { code: '+222', country: 'MR', name: 'Mauritania' },
  { code: '+230', country: 'MU', name: 'Mauritius' },
  { code: '+52', country: 'MX', name: 'Mexico' },
  { code: '+373', country: 'MD', name: 'Moldova' },
  { code: '+377', country: 'MC', name: 'Monaco' },
  { code: '+976', country: 'MN', name: 'Mongolia' },
  { code: '+382', country: 'ME', name: 'Montenegro' },
  { code: '+212', country: 'MA', name: 'Morocco' },
  { code: '+258', country: 'MZ', name: 'Mozambique' },
  { code: '+95', country: 'MM', name: 'Myanmar' },
  { code: '+264', country: 'NA', name: 'Namibia' },
  { code: '+977', country: 'NP', name: 'Nepal' },
  { code: '+31', country: 'NL', name: 'Netherlands' },
  { code: '+64', country: 'NZ', name: 'New Zealand' },
  { code: '+505', country: 'NI', name: 'Nicaragua' },
  { code: '+227', country: 'NE', name: 'Niger' },
  { code: '+234', country: 'NG', name: 'Nigeria' },
  { code: '+850', country: 'KP', name: 'North Korea' },
  { code: '+389', country: 'MK', name: 'North Macedonia' },
  { code: '+47', country: 'NO', name: 'Norway' },
  { code: '+968', country: 'OM', name: 'Oman' },
  { code: '+92', country: 'PK', name: 'Pakistan' },
  { code: '+970', country: 'PS', name: 'Palestine' },
  { code: '+507', country: 'PA', name: 'Panama' },
  { code: '+675', country: 'PG', name: 'Papua New Guinea' },
  { code: '+595', country: 'PY', name: 'Paraguay' },
  { code: '+51', country: 'PE', name: 'Peru' },
  { code: '+63', country: 'PH', name: 'Philippines' },
  { code: '+48', country: 'PL', name: 'Poland' },
  { code: '+351', country: 'PT', name: 'Portugal' },
  { code: '+1787', country: 'PR', name: 'Puerto Rico' },
  { code: '+974', country: 'QA', name: 'Qatar' },
  { code: '+40', country: 'RO', name: 'Romania' },
  { code: '+7', country: 'RU', name: 'Russia' },
  { code: '+250', country: 'RW', name: 'Rwanda' },
  { code: '+966', country: 'SA', name: 'Saudi Arabia' },
  { code: '+221', country: 'SN', name: 'Senegal' },
  { code: '+381', country: 'RS', name: 'Serbia' },
  { code: '+248', country: 'SC', name: 'Seychelles' },
  { code: '+232', country: 'SL', name: 'Sierra Leone' },
  { code: '+65', country: 'SG', name: 'Singapore' },
  { code: '+421', country: 'SK', name: 'Slovakia' },
  { code: '+386', country: 'SI', name: 'Slovenia' },
  { code: '+252', country: 'SO', name: 'Somalia' },
  { code: '+27', country: 'ZA', name: 'South Africa' },
  { code: '+82', country: 'KR', name: 'South Korea' },
  { code: '+211', country: 'SS', name: 'South Sudan' },
  { code: '+34', country: 'ES', name: 'Spain' },
  { code: '+94', country: 'LK', name: 'Sri Lanka' },
  { code: '+249', country: 'SD', name: 'Sudan' },
  { code: '+597', country: 'SR', name: 'Suriname' },
  { code: '+46', country: 'SE', name: 'Sweden' },
  { code: '+41', country: 'CH', name: 'Switzerland' },
  { code: '+963', country: 'SY', name: 'Syria' },
  { code: '+886', country: 'TW', name: 'Taiwan' },
  { code: '+992', country: 'TJ', name: 'Tajikistan' },
  { code: '+255', country: 'TZ', name: 'Tanzania' },
  { code: '+66', country: 'TH', name: 'Thailand' },
  { code: '+670', country: 'TL', name: 'Timor-Leste' },
  { code: '+228', country: 'TG', name: 'Togo' },
  { code: '+676', country: 'TO', name: 'Tonga' },
  { code: '+1868', country: 'TT', name: 'Trinidad' },
  { code: '+216', country: 'TN', name: 'Tunisia' },
  { code: '+90', country: 'TR', name: 'Turkey' },
  { code: '+993', country: 'TM', name: 'Turkmenistan' },
  { code: '+256', country: 'UG', name: 'Uganda' },
  { code: '+380', country: 'UA', name: 'Ukraine' },
  { code: '+971', country: 'AE', name: 'UAE' },
  { code: '+44', country: 'GB', name: 'United Kingdom' },
  { code: '+1', country: 'US', name: 'United States' },
  { code: '+598', country: 'UY', name: 'Uruguay' },
  { code: '+998', country: 'UZ', name: 'Uzbekistan' },
  { code: '+58', country: 'VE', name: 'Venezuela' },
  { code: '+84', country: 'VN', name: 'Vietnam' },
  { code: '+967', country: 'YE', name: 'Yemen' },
  { code: '+260', country: 'ZM', name: 'Zambia' },
  { code: '+263', country: 'ZW', name: 'Zimbabwe' },
];

// ============================================================================
// Component Props
// ============================================================================

interface DemoRequestModalProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  requestedTier?: string;
  source?: string;
}

// ============================================================================
// Form State Interface
// ============================================================================

interface FormState {
  fullName: string;
  email: string;
  countryCode: string;
  phoneNumber: string;
  jobTitle: string;
  organizationName: string;
  organizationType: string;
  organizationSize: string;
  country: string;
  city: string;
  expectedUsers: string;
  additionalNotes: string;
}

const initialFormState: FormState = {
  fullName: '',
  email: '',
  countryCode: '+251',
  phoneNumber: '',
  jobTitle: '',
  organizationName: '',
  organizationType: '',
  organizationSize: '',
  country: '',
  city: '',
  expectedUsers: '',
  additionalNotes: '',
};

// ============================================================================
// Validation
// ============================================================================

interface ValidationErrors {
  [key: string]: string;
}

const validateForm = (form: FormState): ValidationErrors => {
  const errors: ValidationErrors = {};

  if (!form.fullName.trim()) {
    errors.fullName = 'Full name is required';
  }

  if (!form.email.trim()) {
    errors.email = 'Email is required';
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    errors.email = 'Please enter a valid email address';
  }

  if (!form.phoneNumber.trim()) {
    errors.phoneNumber = 'Phone number is required';
  }

  if (!form.jobTitle.trim()) {
    errors.jobTitle = 'Job title is required';
  }

  if (!form.organizationName.trim()) {
    errors.organizationName = 'Organization name is required';
  }

  if (!form.organizationType) {
    errors.organizationType = 'Organization type is required';
  }

  if (!form.organizationSize) {
    errors.organizationSize = 'Organization size is required';
  }

  if (!form.country.trim()) {
    errors.country = 'Country is required';
  }

  if (!form.city.trim()) {
    errors.city = 'City is required';
  }

  // expectedUsers is now optional - no validation needed

  return errors;
};

// ============================================================================
// Select Component (styled consistently)
// ============================================================================

interface SelectFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  placeholder: string;
  error?: string;
  disabled?: boolean;
  required?: boolean;
}

function SelectField({ id, label, value, onChange, options, placeholder, error, disabled, required = true }: SelectFieldProps) {
  return (
    <div className="space-y-1">
      <Label htmlFor={id} className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">
        {label} {required && <span className="text-red-500">*</span>}
        {!required && <span className="text-gray-400 text-[10px] lowercase tracking-normal">(optional)</span>}
      </Label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={`w-full h-10 px-3 rounded-lg border bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 disabled:opacity-50 disabled:cursor-not-allowed hover:border-gray-300 dark:hover:border-gray-600 ${
          error 
            ? 'border-red-400 focus:ring-red-500/20 focus:border-red-500' 
            : 'border-gray-200 dark:border-gray-700'
        }`}
      >
        <option value="" className="text-gray-400">{placeholder}</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && <p className="text-xs text-red-500 mt-0.5">{error}</p>}
    </div>
  );
}

// ============================================================================
// Country Code Phone Input Component
// ============================================================================

interface CountryCodePhoneInputProps {
  countryCode: string;
  phoneNumber: string;
  onCountryCodeChange: (code: string) => void;
  onPhoneNumberChange: (num: string) => void;
  error?: string;
  disabled?: boolean;
}

function CountryCodePhoneInput({ 
  countryCode, 
  phoneNumber, 
  onCountryCodeChange, 
  onPhoneNumberChange, 
  error, 
  disabled 
}: CountryCodePhoneInputProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selectedCountry = COUNTRY_CODES.find(c => c.code === countryCode) || COUNTRY_CODES.find(c => c.code === '+251');

  const filteredCountries = COUNTRY_CODES.filter(c => 
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.code.includes(search) ||
    c.country.toLowerCase().includes(search.toLowerCase())
  );

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setSearch('');
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  return (
    <div className="space-y-1">
      <Label className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">
        Phone Number <span className="text-red-500">*</span>
      </Label>
      <div className="flex">
        <div className="relative" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => !disabled && setIsOpen(!isOpen)}
            disabled={disabled}
            className="h-10 pl-2.5 pr-6 rounded-l-lg border border-r-0 border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white text-xs font-medium cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex items-center gap-1.5 min-w-[85px]"
          >
            <span className="text-sm">{selectedCountry?.country}</span>
            <span className="text-gray-500">{selectedCountry?.code}</span>
          </button>
          <ChevronDown className={`absolute right-1.5 top-1/2 -translate-y-1/2 h-3 w-3 text-gray-400 pointer-events-none transition-transform ${isOpen ? 'rotate-180' : ''}`} />
          
          {isOpen && (
            <div className="absolute top-full left-0 mt-1 w-56 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl z-[200] overflow-hidden">
              <div className="p-2 border-b border-gray-100 dark:border-gray-800">
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
                  <input
                    ref={inputRef}
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search..."
                    className="w-full h-8 pl-8 pr-3 text-xs rounded-md border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
              </div>
              <div className="max-h-48 overflow-y-auto">
                {filteredCountries.map((c) => (
                  <button
                    key={`${c.country}-${c.code}`}
                    type="button"
                    onClick={() => {
                      onCountryCodeChange(c.code);
                      setIsOpen(false);
                      setSearch('');
                    }}
                    className={`w-full px-3 py-1.5 text-left text-xs flex items-center gap-2 hover:bg-brand-50 dark:hover:bg-gray-800 transition-colors ${
                      countryCode === c.code ? 'bg-brand-50 dark:bg-gray-800 text-brand-600' : 'text-gray-700 dark:text-gray-300'
                    }`}
                  >
                    <span className="w-6 text-[10px] text-gray-400 font-medium">{c.country}</span>
                    <span className="flex-1 truncate">{c.name}</span>
                    <span className="text-gray-400 font-mono text-[11px]">{c.code}</span>
                  </button>
                ))}
                {filteredCountries.length === 0 && (
                  <div className="px-3 py-4 text-xs text-gray-400 text-center">No countries found</div>
                )}
              </div>
            </div>
          )}
        </div>
        <Input
          type="tel"
          value={phoneNumber}
          onChange={(e) => onPhoneNumberChange(e.target.value)}
          placeholder="988 490 096"
          disabled={disabled}
          className={`h-10 flex-1 rounded-l-none transition-all duration-200 hover:border-gray-300 dark:hover:border-gray-600 ${error ? 'border-red-400 focus:ring-red-500/20 focus:border-red-500' : ''}`}
        />
      </div>
      {error && <p className="text-xs text-red-500 mt-0.5">{error}</p>}
    </div>
  );
}

// ============================================================================
// Input Field Component
// ============================================================================

interface InputFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  placeholder: string;
  error?: string;
  disabled?: boolean;
  required?: boolean;
}

function InputField({ id, label, value, onChange, type = 'text', placeholder, error, disabled, required = true }: InputFieldProps) {
  return (
    <div className="space-y-1">
      <Label htmlFor={id} className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">
        {label} {required && <span className="text-red-500">*</span>}
      </Label>
      <Input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className={`h-10 transition-all duration-200 hover:border-gray-300 dark:hover:border-gray-600 ${error ? 'border-red-400 focus:ring-red-500/20 focus:border-red-500' : ''}`}
      />
      {error && <p className="text-xs text-red-500 mt-0.5">{error}</p>}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function DemoRequestModal({
  isOpen,
  onOpenChange,
  requestedTier = 'organization',
  source = 'pricing_page',
}: DemoRequestModalProps) {
  const [form, setForm] = useState<FormState>(initialFormState);
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Reset form when modal closes
  const handleOpenChange = useCallback((open: boolean) => {
    if (!open) {
      setForm(initialFormState);
      setErrors({});
    }
    onOpenChange(open);
  }, [onOpenChange]);

  // Update form field
  const updateField = useCallback((field: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  }, [errors]);

  // Handle form submission
  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate form
    const validationErrors = validateForm(form);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      toast.error('Please fill in all required fields');
      return;
    }

    setIsSubmitting(true);

    try {
      // Build payload matching API contract exactly
      const payload: DemoRequestPayload = {
        demo_request: {
          full_name: form.fullName.trim(),
          email: form.email.trim().toLowerCase(),
          phone_number: `${form.countryCode} ${form.phoneNumber.trim()}`,
          job_title: form.jobTitle.trim(),
          organization: {
            name: form.organizationName.trim(),
            type: form.organizationType,
            size: form.organizationSize,
            location: {
              country: form.country.trim(),
              city: form.city.trim(),
            },
          },
          expected_users: form.expectedUsers,
          additional_notes: form.additionalNotes.trim(),
          metadata: {
            requested_tier: requestedTier,
            source: source,
          },
          submitted_at: new Date().toISOString(),
        },
      };

      // Submit to API
      const response = await fetch('/api/demo-request', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || errorData.detail || `Request failed (${response.status})`);
      }

      // Success!
      toast.success('Demo request submitted successfully!', {
        description: 'Our team will contact you shortly.',
        duration: 5000,
      });

      // Reset and close
      setForm(initialFormState);
      setErrors({});
      onOpenChange(false);

    } catch (error) {
      console.error('Demo request error:', error);
      toast.error(
        error instanceof Error ? error.message : 'Failed to submit demo request. Please try again.',
        { duration: 5000 }
      );
    } finally {
      setIsSubmitting(false);
    }
  }, [form, requestedTier, source, onOpenChange]);

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogPortal>
        {/* Custom overlay with higher z-index and better opacity */}
        <DialogOverlay className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        
        <DialogContent className="fixed left-[50%] top-[50%] z-[101] grid w-[calc(100%-2rem)] max-w-[540px] md:max-w-[640px] lg:max-w-[720px] translate-x-[-50%] translate-y-[-50%] gap-0 border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-2xl duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] rounded-2xl max-h-[90vh] sm:max-h-[85vh] overflow-hidden">
          {/* Header with gradient accent */}
          <div className="bg-gradient-to-r from-brand-500/5 via-brand-500/10 to-transparent px-6 py-5 border-b border-gray-100 dark:border-gray-800">
            <DialogHeader className="space-y-1">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-500 shadow-lg shadow-brand-500/25">
                  <Building2 className="h-5 w-5 text-white" />
                </div>
                <div>
                  <DialogTitle className="text-lg font-semibold text-gray-900 dark:text-white">
                    Book a Demo
                  </DialogTitle>
                  <DialogDescription className="text-sm text-gray-500 dark:text-gray-400">
                    Let's discuss how Yuba can help your organization
                  </DialogDescription>
                </div>
              </div>
            </DialogHeader>
          </div>

          {/* Scrollable form area */}
          <div className="overflow-y-auto max-h-[calc(85vh-180px)] px-6 py-5">
            <form onSubmit={handleSubmit} className="space-y-6" id="demo-request-form">
            {/* Personal Information */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
                Personal Information
              </h3>
            
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <InputField
                  id="fullName"
                  label="Full Name"
                  value={form.fullName}
                  onChange={(v) => updateField('fullName', v)}
                  placeholder="John Doe"
                  error={errors.fullName}
                  disabled={isSubmitting}
                />
                <InputField
                  id="email"
                  label="Work Email"
                  type="email"
                  value={form.email}
                  onChange={(v) => updateField('email', v)}
                  placeholder="john@company.com"
                  error={errors.email}
                  disabled={isSubmitting}
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Phone Number with Country Code Selector */}
                <CountryCodePhoneInput
                  countryCode={form.countryCode}
                  phoneNumber={form.phoneNumber}
                  onCountryCodeChange={(code) => updateField('countryCode', code)}
                  onPhoneNumberChange={(num) => updateField('phoneNumber', num)}
                  error={errors.phoneNumber}
                  disabled={isSubmitting}
                />
                <InputField
                  id="jobTitle"
                  label="Job Title"
                  value={form.jobTitle}
                  onChange={(v) => updateField('jobTitle', v)}
                  placeholder="Program Manager"
                  error={errors.jobTitle}
                  disabled={isSubmitting}
                />
              </div>
            </div>

            {/* Organization Information */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
                Organization Information
              </h3>

              <InputField
                id="organizationName"
                label="Organization Name"
                value={form.organizationName}
                onChange={(v) => updateField('organizationName', v)}
                placeholder="Acme Accelerator"
                error={errors.organizationName}
                disabled={isSubmitting}
              />

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <SelectField
                  id="organizationType"
                  label="Organization Type"
                  value={form.organizationType}
                  onChange={(v) => updateField('organizationType', v)}
                  options={ORGANIZATION_TYPES}
                  placeholder="Select type..."
                  error={errors.organizationType}
                  disabled={isSubmitting}
                />
                <SelectField
                  id="organizationSize"
                  label="Organization Size"
                  value={form.organizationSize}
                  onChange={(v) => updateField('organizationSize', v)}
                  options={ORGANIZATION_SIZES}
                  placeholder="Select size..."
                  error={errors.organizationSize}
                  disabled={isSubmitting}
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <InputField
                  id="country"
                  label="Country"
                  value={form.country}
                  onChange={(v) => updateField('country', v)}
                  placeholder="Kenya"
                  error={errors.country}
                  disabled={isSubmitting}
                />
                <InputField
                  id="city"
                  label="City"
                  value={form.city}
                  onChange={(v) => updateField('city', v)}
                  placeholder="Nairobi"
                  error={errors.city}
                  disabled={isSubmitting}
                />
              </div>
            </div>

            {/* Usage Information - Optional */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
                Additional Information
              </h3>

              <SelectField
                id="expectedUsers"
                label="Expected Number of Users"
                value={form.expectedUsers}
                onChange={(v) => updateField('expectedUsers', v)}
                options={EXPECTED_USERS_OPTIONS}
                placeholder="Select expected users..."
                error={errors.expectedUsers}
                disabled={isSubmitting}
                required={false}
              />

              <div className="space-y-1">
                <Label htmlFor="additionalNotes" className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">
                  Additional Notes <span className="text-gray-400 text-[10px] lowercase tracking-normal">(optional)</span>
                </Label>
                <textarea
                  id="additionalNotes"
                  value={form.additionalNotes}
                  onChange={(e) => updateField('additionalNotes', e.target.value)}
                  placeholder="Tell us about your goals, timeline, or any specific requirements..."
                  disabled={isSubmitting}
                  rows={2}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 disabled:opacity-50 disabled:cursor-not-allowed resize-none hover:border-gray-300 dark:hover:border-gray-600"
                />
              </div>
            </div>
          </form>
        </div>

        {/* Fixed Footer */}
        <div className="px-6 py-4 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/50">
          <DialogFooter className="gap-3 sm:gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={isSubmitting}
              className="flex-1 sm:flex-none h-10"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              form="demo-request-form"
              disabled={isSubmitting}
              className="flex-1 sm:flex-none h-10 bg-brand-500 hover:bg-brand-600 text-white shadow-lg shadow-brand-500/25 hover:shadow-brand-500/40 transition-all duration-200"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Submitting...
                </>
              ) : (
                'Submit Request'
              )}
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </DialogPortal>
  </Dialog>
  );
}
