"use client";

import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { FormValidator } from "@/lib/validation";
import SignInModal from "@/components/auth/SignInModal";
import { useAuthStore } from "@/stores/authStore";
import {
  Building2,
  Gift,
  ClipboardList,
  Rocket,
  Clock,
  ChevronDown,
  Phone,
  Info,
  CheckCircle2,
  Loader2,
  Shield,
  AlertCircle,
} from "lucide-react";
import { toast } from "react-hot-toast";
import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription } from "@/components/ui/alert";

// Country code data (Africa focused)
const countryCodes = [
  { code: "+213", country: "Algeria", flag: "🇩🇿" },
  { code: "+244", country: "Angola", flag: "🇦🇴" },
  { code: "+229", country: "Benin", flag: "🇧🇯" },
  { code: "+267", country: "Botswana", flag: "🇧🇼" },
  { code: "+226", country: "Burkina Faso", flag: "🇧🇫" },
  { code: "+257", country: "Burundi", flag: "🇧🇮" },
  { code: "+238", country: "Cabo Verde", flag: "🇨🇻" },
  { code: "+237", country: "Cameroon", flag: "🇨🇲" },
  { code: "+236", country: "Central African Republic", flag: "🇨🇫" },
  { code: "+235", country: "Chad", flag: "🇹🇩" },
  { code: "+269", country: "Comoros", flag: "🇰🇲" },
  { code: "+242", country: "Congo", flag: "🇨🇬" },
  { code: "+243", country: "DR Congo", flag: "🇨🇩" },
  { code: "+225", country: "Côte d'Ivoire", flag: "🇨🇮" },
  { code: "+253", country: "Djibouti", flag: "🇩🇯" },
  { code: "+20", country: "Egypt", flag: "🇪🇬" },
  { code: "+240", country: "Equatorial Guinea", flag: "🇬🇶" },
  { code: "+291", country: "Eritrea", flag: "🇪🇷" },
  { code: "+268", country: "Eswatini", flag: "🇸🇿" },
  { code: "+251", country: "Ethiopia", flag: "🇪🇹" },
  { code: "+241", country: "Gabon", flag: "🇬🇦" },
  { code: "+220", country: "Gambia", flag: "🇬🇲" },
  { code: "+233", country: "Ghana", flag: "🇬🇭" },
  { code: "+224", country: "Guinea", flag: "🇬🇳" },
  { code: "+245", country: "Guinea-Bissau", flag: "🇬🇼" },
  { code: "+254", country: "Kenya", flag: "🇰🇪" },
  { code: "+266", country: "Lesotho", flag: "🇱🇸" },
  { code: "+231", country: "Liberia", flag: "🇱🇷" },
  { code: "+218", country: "Libya", flag: "🇱🇾" },
  { code: "+261", country: "Madagascar", flag: "🇲🇬" },
  { code: "+265", country: "Malawi", flag: "🇲🇼" },
  { code: "+223", country: "Mali", flag: "🇲🇱" },
  { code: "+222", country: "Mauritania", flag: "🇲🇷" },
  { code: "+230", country: "Mauritius", flag: "🇲🇺" },
  { code: "+212", country: "Morocco", flag: "🇲🇦" },
  { code: "+258", country: "Mozambique", flag: "🇲🇿" },
  { code: "+264", country: "Namibia", flag: "🇳🇦" },
  { code: "+227", country: "Niger", flag: "🇳🇪" },
  { code: "+234", country: "Nigeria", flag: "🇳🇬" },
  { code: "+250", country: "Rwanda", flag: "🇷🇼" },
  { code: "+239", country: "São Tomé and Príncipe", flag: "🇸🇹" },
  { code: "+221", country: "Senegal", flag: "🇸🇳" },
  { code: "+248", country: "Seychelles", flag: "🇸🇨" },
  { code: "+232", country: "Sierra Leone", flag: "🇸🇱" },
  { code: "+252", country: "Somalia", flag: "🇸🇴" },
  { code: "+27", country: "South Africa", flag: "🇿🇦" },
  { code: "+211", country: "South Sudan", flag: "🇸🇸" },
  { code: "+249", country: "Sudan", flag: "🇸🇩" },
  { code: "+255", country: "Tanzania", flag: "🇹🇿" },
  { code: "+228", country: "Togo", flag: "🇹🇬" },
  { code: "+216", country: "Tunisia", flag: "🇹🇳" },
  { code: "+256", country: "Uganda", flag: "🇺🇬" },
  { code: "+260", country: "Zambia", flag: "🇿🇲" },
  { code: "+263", country: "Zimbabwe", flag: "🇿🇼" },
];

export default function OrganizationalAdminOnboarding() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const orgType = searchParams.get("type") || "grant_org";
  const inviteToken = searchParams.get("token") || undefined;

  // Auth state
  const { token, user, isAuthenticated } = useAuthStore();
  const [showSignInModal, setShowSignInModal] = useState(false);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    name: "",
    country: "",
    city: "",
    contact_email: "",
    phone_number: "",
  });

  const [extra, setExtra] = useState({
    description: "",
    website: "",
    industry: "",
    size: "",
  });

  const [phoneData, setPhoneData] = useState({
    countryCode: "+233", // Ghana default
    localNumber: "",
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [isPhoneCcpOpen, setIsPhoneCcpOpen] = useState(false);

  const allCountries = useMemo(() => countryCodes.map((c) => c.country), []);

  // Check authentication on mount
  useEffect(() => {
    if (isAuthenticated && token) {
      setAuthToken(token);
      if (process.env.NODE_ENV === 'development') {
        console.log('✅ User authenticated:', { email: user?.email });
      }
    } else {
      setShowSignInModal(true);
    }
  }, [isAuthenticated, token, user]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Handle SignIn success
  const handleSignInSuccess = useCallback(() => {
    const currentToken = useAuthStore.getState().token;
    if (currentToken) {
      setAuthToken(currentToken);
      setShowSignInModal(false);
      toast.success("Signed in successfully! You can now create your organization.");
    }
  }, []);

  // Handle SignIn close
  const handleSignInClose = useCallback(() => {
    setShowSignInModal(false);
  }, []);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleExtraChange = (
    e:
      | React.ChangeEvent<HTMLInputElement>
      | React.ChangeEvent<HTMLTextAreaElement>
      | React.ChangeEvent<HTMLSelectElement>
  ) => {
    const { name, value } = e.target as HTMLInputElement | HTMLTextAreaElement;
    setExtra((prev) => ({ ...prev, [name]: value }));
  };

  const handlePhoneLocalNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setPhoneData((prev) => ({ ...prev, localNumber: value }));
    setFormData((prev) => ({ ...prev, phone_number: `${phoneData.countryCode}${value}` }));
  };

  const handleCountryCodeSelect = (code: string) => {
    setPhoneData((prev) => ({ ...prev, countryCode: code }));
    setFormData((prev) => ({ ...prev, phone_number: `${code}${phoneData.localNumber}` }));
    setIsPhoneCcpOpen(false);
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!FormValidator.validateRequired(formData.name)) newErrors.name = "Organization name is required";
    if (!FormValidator.validateRequired(formData.country)) newErrors.country = "Country is required";
    if (!FormValidator.validateRequired(formData.city)) newErrors.city = "City is required";

    if (!FormValidator.validateRequired(formData.contact_email)) {
      newErrors.contact_email = "Contact email is required";
    } else if (!FormValidator.validateEmail(formData.contact_email)) {
      newErrors.contact_email = "Please enter a valid email address";
    }

    if (!FormValidator.validateRequired(phoneData.localNumber)) {
      newErrors.phone_number = "Phone number is required";
    } else if (!FormValidator.validatePhoneNumber(`${phoneData.countryCode}${phoneData.localNumber}`)) {
      newErrors.phone_number = "Please enter a valid phone number";
    }

    if (!FormValidator.validateRequired(extra.description)) newErrors.description = "Description is required";
    if (!FormValidator.validateRequired(extra.website)) newErrors.website = "Website is required";
    if (!FormValidator.validateRequired(extra.industry)) newErrors.industry = "Industry is required";
    if (!FormValidator.validateRequired(extra.size)) newErrors.size = "Organization size is required";

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const currentToken = authToken || token;

      // Check authentication
      if (!currentToken) {
        toast.error("Please sign in to continue");
        setShowSignInModal(true);
        setIsSubmitting(false);
        return;
      }

      if (process.env.NODE_ENV === 'development') {
        console.log('🚀 Creating organization:', { name: formData.name, country: formData.country });
      }

      const payload = {
        name: formData.name.trim(),
        country: formData.country,
        city: formData.city.trim(),
        contact_email: formData.contact_email.trim(),
        phone_number: formData.phone_number,
        description: extra.description.trim(),
        website: extra.website.trim(),
        industry: extra.industry.trim(),
        size: extra.size,
        ...(inviteToken && { invite_token: inviteToken }),
      };

      const response = await fetch(`${API_URL}/api/organization/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${currentToken}`,
        },
        body: JSON.stringify(payload),
      });

      // Handle API errors
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.message || errorData.detail || `Failed to create organization (${response.status})`;
        throw new Error(errorMessage);
      }

      const result = await response.json();

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Organization created:', result);
      }

      // Extract organization data from wrapped response
      let organizationData;
      if (result.success && result.data) {
        organizationData = result.data;
      } else {
        organizationData = result;
      }

      const orgId = organizationData.id;

      if (!orgId) {
        throw new Error('Invalid response format from organization creation endpoint');
      }

      // Success!
      toast.success("Organization created successfully! Redirecting to your organization dashboard...");

      // Small delay before redirect
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // Redirect to organization dashboard
      if (process.env.NODE_ENV === 'development') {
        console.log('🔄 Redirecting to organization:', orgId);
      }

      router.push(`/signin`);

    } catch (err: any) {
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Organization creation error:', err);
      }

      let errorMessage = "Failed to create organization";

      if (err.message) {
        if (err.message.includes('401') || err.message.includes('Unauthorized')) {
          errorMessage = "Authentication failed. Please sign in again.";
          setShowSignInModal(true);
        } else if (err.message.includes('403') || err.message.includes('Forbidden')) {
          errorMessage = "You don't have permission to create an organization.";
        } else if (err.message.includes('409') || err.message.includes('already exists')) {
          errorMessage = "An organization with this name already exists.";
        } else if (err.message.includes('Network') || err.message.includes('fetch')) {
          errorMessage = "Network error. Please check your connection and try again.";
        } else if (err.message.includes('500')) {
          errorMessage = "Server error. Please try again later.";
        } else {
          errorMessage = err.message;
        }
      }

      setInviteError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    if (formData.country) {
      const countryData = countryCodes.find((c) => c.country === formData.country);
      if (countryData) {
        setPhoneData((prev) => ({ ...prev, countryCode: countryData.code }));
        setFormData((prev) => ({ ...prev, phone_number: `${countryData.code}${phoneData.localNumber}` }));
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formData.country]);

  const selectedCcp = countryCodes.find((c) => c.code === phoneData.countryCode);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50 dark:from-gray-950 dark:via-brand-500 dark:to-gray-950">
      {/* Header */}
      <div className="border-b bg-white/50 dark:bg-brand-500/50 backdrop-blur-sm">
        <div className="mx-auto max-w-5xl px-4 py-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Image src="/images/logo/yuba-logo-icon-colored.png" alt="Yuba" width={50} height={50} priority />
              
              <div>
                <h1 className="text-lg font-semibold text-brand-500 dark:text-white">
                  Create Organization
                </h1>
                <p className="text-sm text-muted-foreground">
                  Set up your organization to get started
                </p>
              </div>
            </div>
            <Badge variant="secondary" className="gap-1.5 px-3 py-1 bg-brand-500 text-white">
              <Gift className="h-3.5 w-3.5" />
              Grant Organization
            </Badge>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-4xl px-4 py-4">
        

        <Card className="border-gray-200 shadow-sm dark:border-gray-800 bg-white/50 dark:bg-brand-500/50 backdrop-blur-sm">
          <CardHeader className="pb-4 border-b">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xl font-semibold text-brand-500 dark:text-white">Organization Details</CardTitle>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Info className="h-3.5 w-3.5" />
                <span>No credit card required</span>
              </div>
            </div>
            <CardDescription>
              Complete the information below to create your organization
            </CardDescription>
          </CardHeader>

          <CardContent>
            {inviteError && (
              <Alert variant="destructive" className="mb-6">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{inviteError}</AlertDescription>
              </Alert>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Basic Information Section */}
              <div className="space-y-2">
                <div className="grid gap-2 md:grid-cols-3">
                  <div className="space-y-2">
                    <Label htmlFor="name" className="text-sm font-medium text-brand-500 dark:text-white">
                      Organization Name <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="name"
                      name="name"
                      placeholder="e.g., Acme Foundation"
                      value={formData.name}
                      onChange={handleInputChange}
                      className={errors.name ? "border-destructive" : ""}
                      disabled={isSubmitting}
                    />
                    {errors.name && (
                      <p className="text-xs text-destructive">{errors.name}</p>
                    )}
                  </div>

                  <div className="space-y-2 w-full">
                    <Label className="text-sm font-medium text-brand-500 dark:text-white">
                      Country <span className="text-destructive">*</span>
                    </Label>
                    <Select
                      value={formData.country}
                      onValueChange={(v) => setFormData((p) => ({ ...p, country: v }))}
                      disabled={isSubmitting}
                    >
                      <SelectTrigger className={errors.country ? "border-destructive" : ""}>
                        <SelectValue placeholder="Select country" />
                      </SelectTrigger>
                      <SelectContent className="max-h-72">
                        {countryCodes.map((c) => (
                          <SelectItem key={c.country} value={c.country}>
                            <span className="mr-2">{c.flag}</span>
                            {c.country}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.country && (
                      <p className="text-xs text-destructive">{errors.country}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="city" className="text-sm font-medium text-brand-500 dark:text-white">
                      City <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="city"
                      name="city"
                      placeholder="e.g., Accra"
                      value={formData.city}
                      onChange={handleInputChange}
                      className={errors.city ? "border-destructive" : ""}
                      disabled={isSubmitting}
                    />
                    {errors.city && (
                      <p className="text-xs text-destructive">{errors.city}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="contact_email" className="text-sm font-medium text-brand-500 dark:text-white">
                      Contact Email <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="contact_email"
                      type="email"
                      name="contact_email"
                      placeholder="contact@organization.org"
                      value={formData.contact_email}
                      onChange={handleInputChange}
                      className={errors.contact_email ? "border-destructive" : ""}
                      disabled={isSubmitting}
                    />
                    {errors.contact_email && (
                      <p className="text-xs text-destructive">{errors.contact_email}</p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      Primary contact email for your organization
                    </p>
                  </div>

                  <div className="md:col-span-2 space-y-2">
                    <Label className="text-sm font-medium text-brand-500 dark:text-white">
                      Phone Number <span className="text-destructive">*</span>
                    </Label>
                    <div className="flex gap-2">
                      <Popover open={isPhoneCcpOpen} onOpenChange={setIsPhoneCcpOpen}>
                        <PopoverTrigger asChild>
                          <Button
                            variant="outline"
                            role="combobox"
                            disabled={isSubmitting}
                            className="w-40 justify-between"
                          >
                            <span className="flex items-center gap-2">
                              {selectedCcp ? (
                                <>
                                  <span>{selectedCcp.flag}</span>
                                  <span className="font-medium">{selectedCcp.code}</span>
                                </>
                              ) : (
                                <>
                                  <Phone className="h-4 w-4" />
                                  <span>Code</span>
                                </>
                              )}
                            </span>
                            <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-80 p-0" align="start">
                          <Command>
                            <CommandInput placeholder="Search country..." />
                            <CommandList>
                              <CommandEmpty>No country found.</CommandEmpty>
                              <CommandGroup>
                                <ScrollArea className="h-60">
                                  {countryCodes.map((item) => (
                                    <CommandItem
                                      key={item.code}
                                      onSelect={() => handleCountryCodeSelect(item.code)}
                                    >
                                      <span className="mr-2">{item.flag}</span>
                                      <span className="flex-1">{item.country}</span>
                                      <span className="text-muted-foreground">{item.code}</span>
                                    </CommandItem>
                                  ))}
                                </ScrollArea>
                              </CommandGroup>
                            </CommandList>
                          </Command>
                        </PopoverContent>
                      </Popover>

                      <Input
                        inputMode="tel"
                        placeholder="Local number"
                        value={phoneData.localNumber}
                        onChange={handlePhoneLocalNumberChange}
                        className={`flex-1 ${errors.phone_number ? "border-destructive" : ""}`}
                        disabled={isSubmitting}
                      />
                    </div>
                    {errors.phone_number && (
                      <p className="text-xs text-destructive">{errors.phone_number}</p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      Full number: <span className="font-mono">{phoneData.countryCode}{phoneData.localNumber || "___"}</span>
                    </p>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Additional Details Section */}
              <div className="space-y-5">
                <div className="grid gap-2 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="description" className="text-sm font-medium text-brand-500 dark:text-white">
                      Description <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="description"
                      name="description"
                      placeholder="Brief description of your organization"
                      value={extra.description}
                      onChange={handleExtraChange}
                      className={errors.description ? "border-destructive" : ""}
                      disabled={isSubmitting}
                    />
                    {errors.description && (
                      <p className="text-xs text-destructive">{errors.description}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="website" className="text-sm font-medium text-brand-500 dark:text-white">
                      Website <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="website"
                      type="url"
                      name="website"
                      placeholder="https://example.org"
                      value={extra.website}
                      onChange={handleExtraChange}
                      className={errors.website ? "border-destructive" : ""}
                      disabled={isSubmitting}
                    />
                    {errors.website && (
                      <p className="text-xs text-destructive">{errors.website}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="industry" className="text-sm font-medium text-brand-500 dark:text-white">
                      Industry <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="industry"
                      name="industry"
                      placeholder="e.g., Non-profit, Education"
                      value={extra.industry}
                      onChange={handleExtraChange}
                      className={errors.industry ? "border-destructive" : ""}
                      disabled={isSubmitting}
                    />
                    {errors.industry && (
                      <p className="text-xs text-destructive">{errors.industry}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-brand-500 dark:text-white">
                      Organization Size <span className="text-destructive">*</span>
                    </Label>
                    <Select
                      value={extra.size}
                      onValueChange={(v) => setExtra((p) => ({ ...p, size: v }))}
                      disabled={isSubmitting}
                    >
                      <SelectTrigger className={errors.size ? "border-destructive" : ""}>
                        <SelectValue placeholder="Select organization size" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="startup">Startup (1-10 employees)</SelectItem>
                        <SelectItem value="small">Small (11-50 employees)</SelectItem>
                        <SelectItem value="medium">Medium (51-200 employees)</SelectItem>
                        <SelectItem value="large">Large (201-1000 employees)</SelectItem>
                        <SelectItem value="enterprise">Enterprise (1000+ employees)</SelectItem>
                      </SelectContent>
                    </Select>
                    {errors.size && (
                      <p className="text-xs text-destructive">{errors.size}</p>
                    )}
                  </div>
                </div>
              </div>

              <Separator />

              {/* Submit Button */}
              <div className="flex flex-col gap-4 pt-2">
                <Button 
                  type="submit" 
                  className="w-full h-11 text-base font-medium" 
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      Creating organization...
                    </>
                  ) : (
                    <>
                      <Rocket className="mr-2 h-5 w-5" />
                      Create Organization
                    </>
                  )}
                </Button>

                <p className="text-center text-xs text-muted-foreground">
                  By creating an organization, you agree to our{" "}
                  <Link href="/terms" className="font-medium underline underline-offset-4 hover:text-brand-600">
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link href="/privacy" className="font-medium underline underline-offset-4 hover:text-brand-600">
                    Privacy Policy
                  </Link>
                </p>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>

      {showSignInModal && (
        <SignInModal
          isOpen={showSignInModal}
          onClose={handleSignInClose}
          onSuccess={handleSignInSuccess}
        />
      )}
    </div>
  );
}