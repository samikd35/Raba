"use client";

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Users, 
  Building2, 
  Globe, 
  Briefcase, 
  Hash, 
  Settings, 
  ArrowRight,
  CheckCircle2,
  Sparkles,
  MapPin,
  Target,
  Rocket,
  Shield,
  AlertCircle
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';

export default function TeamOnboarding() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const orgId = searchParams.get('org_id');

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    website: '',
    industry: '',
    size: '',
    country: ''
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [currentStep, setCurrentStep] = useState(1);
  const [isLoading, setIsLoading] = useState(true);

  const steps = [
    { number: 1, title: 'Basic Info', description: 'Team name and purpose' },
    { number: 2, title: 'Details', description: 'Industry and location' },
    { number: 3, title: 'Review', description: 'Confirm and create' }
  ];

  // Validate required parameters
  useEffect(() => {
    const validateInvitation = async () => {
      if (!token || !orgId) {
        toast.error('Invalid team leader invitation link');
        router.push('/signin');
        return;
      }

      // Validate the invitation token
      try {
        // Add any token validation logic here if needed
        setIsLoading(false);
      } catch (error) {
        toast.error('Invalid or expired invitation link');
        router.push('/signin');
      }
    };

    validateInvitation();
  }, [token, orgId, router]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const handleSelectChange = (name: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear error when user selects an option
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const validateStep = (step: number) => {
    const newErrors: Record<string, string> = {};

    if (step === 1) {
      if (!formData.name.trim()) {
        newErrors.name = 'Team name is required';
      } else if (formData.name.length < 2) {
        newErrors.name = 'Team name must be at least 2 characters';
      }

      if (!formData.description.trim()) {
        newErrors.description = 'Description is required';
      } else if (formData.description.length < 10) {
        newErrors.description = 'Description must be at least 10 characters';
      }
    }

    if (step === 2) {
      if (!formData.industry) {
        newErrors.industry = 'Industry is required';
      }

      if (!formData.size) {
        newErrors.size = 'Team size is required';
      }

      if (!formData.country) {
        newErrors.country = 'Country is required';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const nextStep = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, 3));
    }
  };

  const prevStep = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
  };

  const validateForm = () => {
    return validateStep(1) && validateStep(2);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm() || !orgId) {
      toast.error('Please fill in all required fields');
      return;
    }

    if (!token) {
      toast.error('Authentication token is missing');
      return;
    }

    setIsSubmitting(true);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL;
      
      if (process.env.NODE_ENV === 'development') {
        console.log('🚀 Creating team with:', {
          orgId,
          name: formData.name,
          hasToken: !!token
        });
      }

      // Create team via backend API
      const response = await fetch(`${API_URL}/api/teams/${orgId}/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: formData.name.trim(),
          description: formData.description.trim() || `${formData.name} team workspace`,
          website: formData.website.trim() || '',
          industry: formData.industry,
          size: formData.size,
          country: formData.country,
          settings: { additionalProp1: {} },
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.message || errorData.detail || `Failed to create team (${response.status})`;
        throw new Error(errorMessage);
      }

      const data = await response.json();

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Team created successfully:', data);
      }

      toast.success('Team created successfully! Redirecting to your team workspace...');
      
      // Redirect to team workspace dashboard
      setTimeout(() => {
        router.push(`/signin`);
      }, 1500);

    } catch (error: any) {
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Error creating team:', error);
      }
      
      // Display field-specific errors or general error message
      if (error.message?.includes('name')) {
        setErrors({ name: 'Team name already exists or is invalid' });
        toast.error('Team name already exists. Please choose a different name.');
      } else if (error.message?.includes('already exists')) {
        toast.error('You already have a team in this organization');
      } else if (error.message?.includes('tenants_size_check')) {
        toast.error('Invalid team size selected. Please choose a valid team size.');
        setErrors({ size: 'Please select a valid team size' });
      } else if (error.message?.includes('401') || error.message?.includes('unauthorized')) {
        toast.error('Your session has expired. Please sign in again.');
        router.push('/signin');
      } else if (error.message?.includes('403') || error.message?.includes('forbidden')) {
        toast.error('You do not have permission to create a team in this organization.');
      } else {
        toast.error(error.message || 'Failed to create team. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="w-full max-w-2xl border-0 shadow-lg">
          <CardHeader>
            <Skeleton className="h-8 w-3/4 mb-2" />
            <Skeleton className="h-4 w-full" />
          </CardHeader>
          <CardContent className="space-y-6">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-12 w-full" />
            <div className="flex justify-between pt-6">
              <Skeleton className="h-10 w-24" />
              <Skeleton className="h-10 w-32" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!token || !orgId) {
    return (
      <div className="min-h-screen bg-background flex justify-center items-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
         
          <h1 className="text-2xl font-bold text-brand-500 dark:text-white -2">
            Create Your Team Workspace
          </h1>
          <p className="text-muted-foreground max-w-2xl mx-auto text-sm">
            Set up your team workspace to start collaborating and managing projects with your members
          </p>
        </motion.div>

        {/* Progress Steps */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8"
        >
          <div className="flex justify-center mb-8">
            <div className="flex items-center space-x-8">
              {steps.map((step, index) => (
                <div key={step.number} className="flex items-center">
                  <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${
                    currentStep >= step.number
                      ? 'bg-brand-500 border-brand-500 text-white'
                      : 'border-gray-300 dark:border-gray-600 text-gray-500'
                  } transition-all duration-300`}>
                    {currentStep > step.number ? (
                      <CheckCircle2 className="w-5 h-5" />
                    ) : (
                      <span className="font-semibold">{step.number}</span>
                    )}
                  </div>
                  <div className="ml-3">
                    <div className={`text-sm font-medium ${
                      currentStep >= step.number
                        ? 'text-brand-600 dark:text-brand-400'
                        : 'text-gray-500'
                    }`}>
                      {step.title}
                    </div>
                    <div className="text-xs text-gray-500">{step.description}</div>
                  </div>
                  {index < steps.length - 1 && (
                    <div className={`w-16 h-0.5 mx-4 ${
                      currentStep > step.number ? 'bg-brand-500' : 'bg-gray-300 dark:bg-gray-600'
                    }`} />
                  )}
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Form */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm border-0 shadow-lg rounded-2xl overflow-hidden">
            <CardHeader className="pb-6 border-b border-gray-200 dark:border-gray-700">
              <CardTitle className="flex items-center text-xl">
                <Building2 className="w-6 h-6 mr-3 text-brand-500" />
                {steps[currentStep - 1].title}
              </CardTitle>
              <CardDescription className="text-md">
                {currentStep === 1 && "Let's start with the basics about your team"}
                {currentStep === 2 && "Tell us more about your team's focus and location"}
                {currentStep === 3 && "Review your information before creating the team"}
              </CardDescription>
            </CardHeader>
            <CardContent className="px-6 ">
              <form onSubmit={handleSubmit} className="space-y-6">
                <AnimatePresence mode="wait">
                  {/* Step 1: Basic Information */}
                  {currentStep === 1 && (
                    <motion.div
                      key="step-1"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      className="space-y-6"
                    >
                      <div className="grid grid-cols-1 gap-6">
                        {/* Team Name */}
                        <div className="space-y-2">
                          <Label htmlFor="name" className="text-sm font-semibold flex items-center  text-brand-500">
                            <Users className="w-4 h-4 mr-2 text-brand-500" />
                            Team Name *
                          </Label>
                          <Input
                            type="text"
                            id="name"
                            name="name"
                            value={formData.name}
                            onChange={handleInputChange}
                            placeholder="e.g., Marketing Team, Engineering Squad"
                            className={`text-lg py-3 ${errors.name ? 'border-red-500' : ''}`}
                          />
                          {errors.name && (
                            <p className="text-sm text-red-600 flex items-center">
                              <Shield className="w-3 h-3 mr-1" />
                              {errors.name}
                            </p>
                          )}
                          <p className="text-sm text-gray-500">
                            Choose a descriptive name that represents your team's purpose
                          </p>
                        </div>

                        {/* Description */}
                        <div className="space-y-2">
                          <Label htmlFor="description" className="text-sm font-semibold flex items-center text-brand-500">
                            <Target className="w-4 h-4 mr-2 text-brand-500" />
                            Team Description *
                          </Label>
                          <Textarea
                            id="description"
                            name="description"
                            value={formData.description}
                            onChange={handleInputChange}
                            rows={4}
                            placeholder="Describe your team's mission, goals, and what you'll be working on..."
                            className={`resize-none ${errors.description ? 'border-red-500' : ''}`}
                          />
                          {errors.description && (
                            <p className="text-sm text-red-600 flex items-center">
                              <Shield className="w-3 h-3 mr-1" />
                              {errors.description}
                            </p>
                          )}
                          <p className="text-sm text-gray-500">
                            This helps team members understand the team's purpose and objectives
                          </p>
                        </div>

                        {/* Website */}
                        <div className="space-y-2">
                          <Label htmlFor="website" className="text-sm font-semibold flex items-center text-brand-500">
                            <Globe className="w-4 h-4 mr-2 text-brand-500" />
                            Team Website
                          </Label>
                          <Input
                            type="url"
                            id="website"
                            name="website"
                            value={formData.website}
                            onChange={handleInputChange}
                            placeholder="https://example.com"
                            className="py-3"
                          />
                          <p className="text-sm text-gray-500">
                            Optional: Your team's website or relevant project page
                          </p>
                        </div>
                      </div>
                    </motion.div>
                  )}

                  {/* Step 2: Additional Details */}
                  {currentStep === 2 && (
                    <motion.div
                      key="step-2"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      className="space-y-6"
                    >
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Industry */}
                        <div className="space-y-2">
                          <Label htmlFor="industry" className="text-sm font-semibold flex items-center text-brand-500">
                            <Briefcase className="w-4 h-4 mr-2 text-brand-500" />
                            Industry *
                          </Label>
                          <Select
                            value={formData.industry}
                            onValueChange={(value) => handleSelectChange('industry', value)}
                          >
                            <SelectTrigger className={`w-full ${errors.industry ? 'border-red-500' : ''}`}>
                              <SelectValue placeholder="Select Industry" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="Technology">Technology</SelectItem>
                              <SelectItem value="Healthcare">Healthcare</SelectItem>
                              <SelectItem value="Finance">Finance</SelectItem>
                              <SelectItem value="Education">Education</SelectItem>
                              <SelectItem value="Retail">Retail</SelectItem>
                              <SelectItem value="Manufacturing">Manufacturing</SelectItem>
                              <SelectItem value="Consulting">Consulting</SelectItem>
                              <SelectItem value="Media">Media</SelectItem>
                              <SelectItem value="Non-profit">Non-profit</SelectItem>
                              <SelectItem value="Other">Other</SelectItem>
                            </SelectContent>
                          </Select>
                          {errors.industry && (
                            <p className="text-sm text-red-600 flex items-center">
                              <Shield className="w-3 h-3 mr-1" />
                              {errors.industry}
                            </p>
                          )}
                        </div>

                        {/* Team Size */}
                        <div className="space-y-2">
                          <Label htmlFor="size" className="text-sm font-semibold flex items-center text-brand-500">
                            <Hash className="w-4 h-4 mr-2 text-brand-500" />
                            Team Size *
                          </Label>
                          <Select
                            value={formData.size}
                            onValueChange={(value) => handleSelectChange('size', value)}
                          >
                            <SelectTrigger className={`w-full ${errors.size ? 'border-red-500' : ''}`}>
                              <SelectValue placeholder="Select Team Size" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="startup">Startup (1-10 members)</SelectItem>
                              <SelectItem value="small">Small (11-50 members)</SelectItem>
                              <SelectItem value="medium">Medium (51-200 members)</SelectItem>
                              <SelectItem value="large">Large (201-500 members)</SelectItem>
                              <SelectItem value="enterprise">Enterprise (500+ members)</SelectItem>
                            </SelectContent>
                          </Select>
                          {errors.size && (
                            <p className="text-sm text-red-600 flex items-center">
                              <Shield className="w-3 h-3 mr-1" />
                              {errors.size}
                            </p>
                          )}
                        </div>
                      </div>

                      {/* Country */}
                      <div className="space-y-2">
                        <Label htmlFor="country" className="text-sm font-semibold flex items-center text-brand-500">
                          <MapPin className="w-4 h-4 mr-2 text-brand-500" />
                          Country *
                        </Label>
                        <Select
                          value={formData.country}
                          onValueChange={(value) => handleSelectChange('country', value)}
                        >
                          <SelectTrigger className={`w-full ${errors.country ? 'border-red-500' : ''}`}>
                            <SelectValue placeholder="Select Country" />
                          </SelectTrigger>
                          <SelectContent className="max-h-[300px]">
                            <SelectItem value="Algeria">Algeria</SelectItem>
                            <SelectItem value="Angola">Angola</SelectItem>
                            <SelectItem value="Benin">Benin</SelectItem>
                            <SelectItem value="Botswana">Botswana</SelectItem>
                            <SelectItem value="Burkina Faso">Burkina Faso</SelectItem>
                            <SelectItem value="Burundi">Burundi</SelectItem>
                            <SelectItem value="Cape Verde">Cape Verde</SelectItem>
                            <SelectItem value="Cameroon">Cameroon</SelectItem>
                            <SelectItem value="Central African Republic">Central African Republic</SelectItem>
                            <SelectItem value="Chad">Chad</SelectItem>
                            <SelectItem value="Comoros">Comoros</SelectItem>
                            <SelectItem value="Congo">Congo</SelectItem>
                            <SelectItem value="Côte d'Ivoire">Côte d'Ivoire</SelectItem>
                            <SelectItem value="Democratic Republic of the Congo">Democratic Republic of the Congo</SelectItem>
                            <SelectItem value="Djibouti">Djibouti</SelectItem>
                            <SelectItem value="Egypt">Egypt</SelectItem>
                            <SelectItem value="Equatorial Guinea">Equatorial Guinea</SelectItem>
                            <SelectItem value="Eritrea">Eritrea</SelectItem>
                            <SelectItem value="Eswatini">Eswatini</SelectItem>
                            <SelectItem value="Ethiopia">Ethiopia</SelectItem>
                            <SelectItem value="Gabon">Gabon</SelectItem>
                            <SelectItem value="Gambia">Gambia</SelectItem>
                            <SelectItem value="Ghana">Ghana</SelectItem>
                            <SelectItem value="Guinea">Guinea</SelectItem>
                            <SelectItem value="Guinea-Bissau">Guinea-Bissau</SelectItem>
                            <SelectItem value="Kenya">Kenya</SelectItem>
                            <SelectItem value="Lesotho">Lesotho</SelectItem>
                            <SelectItem value="Liberia">Liberia</SelectItem>
                            <SelectItem value="Libya">Libya</SelectItem>
                            <SelectItem value="Madagascar">Madagascar</SelectItem>
                            <SelectItem value="Malawi">Malawi</SelectItem>
                            <SelectItem value="Mali">Mali</SelectItem>
                            <SelectItem value="Mauritania">Mauritania</SelectItem>
                            <SelectItem value="Mauritius">Mauritius</SelectItem>
                            <SelectItem value="Morocco">Morocco</SelectItem>
                            <SelectItem value="Mozambique">Mozambique</SelectItem>
                            <SelectItem value="Namibia">Namibia</SelectItem>
                            <SelectItem value="Niger">Niger</SelectItem>
                            <SelectItem value="Nigeria">Nigeria</SelectItem>
                            <SelectItem value="Rwanda">Rwanda</SelectItem>
                            <SelectItem value="Sao Tome and Principe">Sao Tome and Principe</SelectItem>
                            <SelectItem value="Senegal">Senegal</SelectItem>
                            <SelectItem value="Seychelles">Seychelles</SelectItem>
                            <SelectItem value="Sierra Leone">Sierra Leone</SelectItem>
                            <SelectItem value="Somalia">Somalia</SelectItem>
                            <SelectItem value="South Africa">South Africa</SelectItem>
                            <SelectItem value="South Sudan">South Sudan</SelectItem>
                            <SelectItem value="Sudan">Sudan</SelectItem>
                            <SelectItem value="Tanzania">Tanzania</SelectItem>
                            <SelectItem value="Togo">Togo</SelectItem>
                            <SelectItem value="Tunisia">Tunisia</SelectItem>
                            <SelectItem value="Uganda">Uganda</SelectItem>
                            <SelectItem value="Zambia">Zambia</SelectItem>
                            <SelectItem value="Zimbabwe">Zimbabwe</SelectItem>
                          </SelectContent>
                        </Select>
                        {errors.country && (
                          <p className="text-sm text-red-600 flex items-center">
                            <Shield className="w-3 h-3 mr-1" />
                            {errors.country}
                          </p>
                        )}
                      </div>
                    </motion.div>
                  )}

                  {/* Step 3: Review */}
                  {currentStep === 3 && (
                    <motion.div
                      key="step-3"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      className="space-y-6"
                    >
                      <div className="bg-brand-50 dark:bg-brand-900/20 rounded-lg p-6 border border-brand-200 dark:border-brand-800">
                        <h3 className="font-semibold text-brand-900 dark:text-brand-100 mb-4 flex items-center">
                          <CheckCircle2 className="w-5 h-5 mr-2" />
                          Review Your Team Information
                        </h3>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          <div className="space-y-4">
                            <div>
                              <Label className="text-sm font-medium text-gray-600 dark:text-gray-400">Team Name</Label>
                              <p className="font-semibold text-gray-900 dark:text-white">{formData.name}</p>
                            </div>
                            <div>
                              <Label className="text-sm font-medium text-gray-600 dark:text-gray-400">Description</Label>
                              <p className="text-gray-700 dark:text-gray-300">{formData.description}</p>
                            </div>
                            <div>
                              <Label className="text-sm font-medium text-gray-600 dark:text-gray-400">Website</Label>
                              <p className="text-gray-700 dark:text-gray-300">{formData.website || 'Not provided'}</p>
                            </div>
                          </div>
                          
                          <div className="space-y-4">
                            <div>
                              <Label className="text-sm font-medium text-gray-600 dark:text-gray-400">Industry</Label>
                              <Badge variant="secondary" className="mt-1">
                                {formData.industry}
                              </Badge>
                            </div>
                            <div>
                              <Label className="text-sm font-medium text-gray-600 dark:text-gray-400">Team Size</Label>
                              <Badge variant="secondary" className="mt-1">
                                {formData.size}
                              </Badge>
                            </div>
                            <div>
                              <Label className="text-sm font-medium text-gray-600 dark:text-gray-400">Country</Label>
                              <Badge variant="secondary" className="mt-1">
                                {formData.country}
                              </Badge>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-4 border border-amber-200 dark:border-amber-800">
                        <div className="flex items-start space-x-3">
                          <Sparkles className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <h4 className="font-medium text-amber-800 dark:text-amber-200">
                              Ready to Launch Your Team
                            </h4>
                            <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                              Your team workspace will be created with you as the team leader. 
                              You'll be able to invite members and manage projects immediately.
                            </p>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Navigation Buttons */}
                <div className="flex justify-between pt-6 border-t border-gray-200 dark:border-gray-700">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={currentStep === 1 ? () => router.push('/signin') : prevStep}
                    disabled={isSubmitting}
                    className="flex items-center gap-2"
                  >
                    {currentStep === 1 ? 'Cancel' : 'Back'}
                  </Button>

                  <div className="flex gap-3">
                    {currentStep < 3 ? (
                      <Button
                        type="button"
                        onClick={nextStep}
                        className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700"
                      >
                        Continue
                        <ArrowRight className="w-4 h-4" />
                      </Button>
                    ) : (
                      <Button
                        type="submit"
                        disabled={isSubmitting}
                        className="flex items-center gap-2 bg-green-600 hover:bg-green-700 min-w-[150px]"
                      >
                        {isSubmitting ? (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                            Creating Team...
                          </>
                        ) : (
                          <>
                            <Rocket className="w-4 h-4" />
                            Launch Team Workspace
                          </>
                        )}
                      </Button>
                    )}
                  </div>
                </div>
              </form>
            </CardContent>
          </Card>
        </motion.div>

        {/* Help Text */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="mt-8 text-center"
        >
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Need help setting up your team? Contact support at{' '}
            <a href="mailto:support@yuba.com" className="text-brand-600 hover:text-brand-500 font-medium">
              support@yuba.com
            </a>
          </p>
        </motion.div>
      </div>
    </div>
  );
}