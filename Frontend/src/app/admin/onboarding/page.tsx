"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { FormValidator } from "@/lib/validation";
import { organizationService } from "@/lib/api/organizationService";
import {
  Building2,
  Gift,
  ClipboardList,
  Rocket,
  Clock,
  ChevronDown,
  Globe,
  Phone,
  Info,
  CheckCircle2,
} from "lucide-react";
import { toast, Toaster } from "react-hot-toast";
import Link from "next/link";
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
  const orgType = searchParams.get("type") || "grant_org"; // currently only grant orgs
  const token = searchParams.get("token") || undefined;

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
    settings: {},
    settingsRaw: '{\n  "additionalProp1": {}\n}',
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
      const payload = {
        name: formData.name,
        country: formData.country,
        city: formData.city,
        contact_email: formData.contact_email,
        phone_number: formData.phone_number,
        description: extra.description,
        website: extra.website,
        industry: extra.industry,
        size: extra.size,
        invite_token: token,
      };

      const createdOrg = await organizationService.createOrganization(payload as any);
      const orgId = createdOrg && (createdOrg as any).id ? (createdOrg as any).id : undefined;

      if (orgId) {
        try {
          const { authService } = await import("@/services/authService");
          await authService.switchToTenant(orgId);
          await new Promise((r) => setTimeout(r, 500));
          toast.success(`Organization created!`);
          window.location.href = `/admin/organizations/${orgId}`;
        } catch (switchError) {
          toast.error("Organization created but failed to switch context. Please refresh.");
          window.location.href = `/admin/organizations/${orgId}`;
        }
      } else {
        toast.success("Organization created successfully");
        window.location.href = "/admin/organization-dashboard";
      }
    } catch (err: any) {
      const message = err?.message || "Failed to create organization";
      setInviteError(message);
      toast.error(message);
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
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-5xl px-4 py-10">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm text-muted-foreground">
            <Building2 className="h-4 w-4" />
            <span>Administrator</span>
          </div>
          <h1 className="flex items-center justify-center gap-2 text-3xl font-semibold text-brand-500">
            <span>Create your organization</span>
          </h1>
          <p className=" max-w-2xl text-muted-foreground">
            Complete a few details to set up your organization and start using Yuba.
          </p>
        </div>

        <Card className="border bg-white">
          <CardHeader className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="gap-1">
                  <Gift className="h-3.5 w-3.5" /> Grant organization
                </Badge>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Info className="h-4 w-4" />
                No credit card required. Monthly credits via Yuba grants.
              </div>
            </div>
            <Separator />
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              Secure and private. Only admins can view and edit organization settings.
            </div>
          </CardHeader>
          <CardContent>
            {inviteError && (
              <div
                role="alert"
                className="mb-6 rounded-md border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive"
              >
                {inviteError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-8">
              <section className="space-y-4">
                <div className="flex items-center gap-2">
                  <ClipboardList className="h-5 w-5 text-primary" />
                  <h3 className="text-lg font-medium">Organization details</h3>
                </div>

                <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="name">Organization name *</Label>
                    <Input
                      id="name"
                      name="name"
                      placeholder="e.g., Yuba Foundation"
                      value={formData.name}
                      onChange={handleInputChange}
                      aria-invalid={!!errors.name}
                      aria-describedby={errors.name ? "name-error" : undefined}
                    />
                    {errors.name && (
                      <p id="name-error" className="text-sm text-destructive">
                        {errors.name}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label>Country *</Label>
                    <Select
                      value={formData.country}
                      onValueChange={(v) => setFormData((p) => ({ ...p, country: v }))}
                    >
                      <SelectTrigger aria-invalid={!!errors.country}>
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
                      <p className="text-sm text-destructive">{errors.country}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="city">City *</Label>
                    <Input
                      id="city"
                      name="city"
                      placeholder="e.g., Accra"
                      value={formData.city}
                      onChange={handleInputChange}
                      aria-invalid={!!errors.city}
                      aria-describedby={errors.city ? "city-error" : undefined}
                    />
                    {errors.city && (
                      <p id="city-error" className="text-sm text-destructive">
                        {errors.city}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="contact_email">Contact email *</Label>
                    <Input
                      id="contact_email"
                      type="email"
                      name="contact_email"
                      placeholder="org-contact@example.org"
                      value={formData.contact_email}
                      onChange={handleInputChange}
                      aria-invalid={!!errors.contact_email}
                      aria-describedby={errors.contact_email ? "email-error" : undefined}
                    />
                    {errors.contact_email && (
                      <p id="email-error" className="text-sm text-destructive">
                        {errors.contact_email}
                      </p>
                    )}
                  </div>

                  <div className="md:col-span-2 space-y-2">
                    <Label>Phone number *</Label>
                    <div className="flex gap-2">
                      {/* Country code searchable popover */}
                      <Popover open={isPhoneCcpOpen} onOpenChange={setIsPhoneCcpOpen}>
                        <PopoverTrigger asChild>
                          <Button
                            variant="outline"
                            role="combobox"
                            aria-expanded={isPhoneCcpOpen}
                            className="w-44 justify-between"
                          >
                            <span className="flex items-center gap-2">
                              <Phone className="h-4 w-4 text-muted-foreground" />
                              {selectedCcp ? (
                                <>
                                  <span>{selectedCcp.flag}</span>
                                  <span className="font-medium">{selectedCcp.code}</span>
                                </>
                              ) : (
                                "Code"
                              )}
                            </span>
                            <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-80 p-0" align="start">
                          <Command>
                            <CommandInput placeholder="Search country or code..." />
                            <CommandList>
                              <CommandEmpty>No results found.</CommandEmpty>
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
                        aria-invalid={!!errors.phone_number}
                        aria-describedby={errors.phone_number ? "phone-error" : undefined}
                        className="flex-1"
                      />
                    </div>
                    {errors.phone_number && (
                      <p id="phone-error" className="text-sm text-destructive">
                        {errors.phone_number}
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      Full number: {phoneData.countryCode}
                      {phoneData.localNumber || "___"}
                    </p>
                  </div>
                </div>
              </section>

              <section className="space-y-4">
                <div className="flex items-center gap-2">
                  <ClipboardList className="h-5 w-5 text-primary" />
                  <h3 className="text-lg font-medium">Additional details</h3>
                </div>

                <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="description">Description *</Label>
                    <Input
                      id="description"
                      name="description"
                      placeholder="Short description of your organization"
                      value={extra.description}
                      onChange={handleExtraChange}
                      aria-invalid={!!errors.description}
                      aria-describedby={errors.description ? "desc-error" : undefined}
                    />
                    {errors.description && (
                      <p id="desc-error" className="text-sm text-destructive">
                        {errors.description}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="website">Website *</Label>
                    <Input
                      id="website"
                      type="url"
                      name="website"
                      placeholder="https://example.org"
                      value={extra.website}
                      onChange={handleExtraChange}
                      aria-invalid={!!errors.website}
                      aria-describedby={errors.website ? "website-error" : undefined}
                    />
                    {errors.website && (
                      <p id="website-error" className="text-sm text-destructive">
                        {errors.website}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="industry">Industry *</Label>
                    <Input
                      id="industry"
                      name="industry"
                      placeholder="e.g., Non-profit, Education, Tech"
                      value={extra.industry}
                      onChange={handleExtraChange}
                      aria-invalid={!!errors.industry}
                      aria-describedby={errors.industry ? "industry-error" : undefined}
                    />
                    {errors.industry && (
                      <p id="industry-error" className="text-sm text-destructive">
                        {errors.industry}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label>Organization size *</Label>
                    <Select
                      value={extra.size}
                      onValueChange={(v) => setExtra((p) => ({ ...p, size: v }))}
                    >
                      <SelectTrigger aria-invalid={!!errors.size}>
                        <SelectValue placeholder="Select size" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="startup">Startup (1-10)</SelectItem>
                        <SelectItem value="small">Small (11-50)</SelectItem>
                        <SelectItem value="medium">Medium (51-200)</SelectItem>
                        <SelectItem value="large">Large (201-1000)</SelectItem>
                        <SelectItem value="enterprise">Enterprise (1000+)</SelectItem>
                      </SelectContent>
                    </Select>
                    {errors.size && (
                      <p className="text-sm text-destructive">{errors.size}</p>
                    )}
                  </div>
                </div>
              </section>

              <div className="pt-2">
                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting ? (
                    <span className="inline-flex items-center gap-2">
                      <Clock className="h-4 w-4 animate-spin" /> Creating organization...
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-2">
                      <Rocket className="h-4 w-4" /> Create organization
                    </span>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <div className="mt-8 text-center text-sm text-muted-foreground">
          <p>
            By creating an organization, you agree to our {" "}
            <Link href="/terms" className="underline underline-offset-4">
              Terms of Service
            </Link>{" "}
            and {" "}
            <Link href="/privacy" className="underline underline-offset-4">
              Privacy Policy
            </Link>
            .
          </p>
        </div>
      </div>
    </div>
  );
}