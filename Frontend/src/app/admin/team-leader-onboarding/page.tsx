"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
import { useTeamStore } from '@/stores/teamStore';
import { teamService } from '@/lib/api/teamService';
import { InvitationFlowManager } from '@/lib/auth/invitationFlowManager';
import { toast } from "react-hot-toast";
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, Building2, CheckCircle, AlertCircle } from 'lucide-react';

// Zod validation schema for team creation form
const teamCreationSchema = z.object({
  name: z.string()
    .min(2, 'Team name must be at least 2 characters')
    .max(100, 'Team name must be less than 100 characters'),
  description: z.string()
    .max(500, 'Description must be less than 500 characters')
    .optional()
    .or(z.literal('')),
  website: z.string()
    .url('Please enter a valid URL')
    .optional()
    .or(z.literal('')),
  industry: z.string()
    .min(1, 'Please select an industry'),
  size: z.enum(['startup', 'small', 'medium', 'large', 'enterprise']),
  country: z.string()
    .min(1, 'Please select a country'),
});

type TeamCreationFormData = z.infer<typeof teamCreationSchema>;

// Industry options
const industryOptions = [
  'Technology',
  'Healthcare',
  'Finance',
  'Education',
  'Manufacturing',
  'Retail',
  'Agriculture',
  'Energy',
  'Transportation',
  'Real Estate',
  'Media & Entertainment',
  'Hospitality',
  'Other',
];

// Team size options - Updated to match database constraints
const teamSizeOptions = [
  { value: '1-10', label: '1-10 members' },
  { value: '11-50', label: '11-50 members' },
];

// Country options (African countries)
const countryOptions = [
  'Algeria', 'Angola', 'Benin', 'Botswana', 'Burkina Faso', 'Burundi', 'Cape Verde', 'Cameroon',
  'Central African Republic', 'Chad', 'Comoros', 'Congo (Congo-Brazzaville)', 'Côte d\'Ivoire',
  'Democratic Republic of the Congo', 'Djibouti', 'Egypt', 'Equatorial Guinea', 'Eritrea',
  'Eswatini', 'Ethiopia', 'Gabon', 'Gambia', 'Ghana', 'Guinea', 'Guinea-Bissau', 'Kenya',
  'Lesotho', 'Liberia', 'Libya', 'Madagascar', 'Malawi', 'Mali', 'Mauritania', 'Mauritius',
  'Morocco', 'Mozambique', 'Namibia', 'Niger', 'Nigeria', 'Rwanda', 'Sao Tome and Principe',
  'Senegal', 'Seychelles', 'Sierra Leone', 'Somalia', 'South Africa', 'South Sudan', 'Sudan',
  'Tanzania', 'Togo', 'Tunisia', 'Uganda', 'Zambia', 'Zimbabwe',
];

export default function TeamLeaderOnboarding() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuthStore();
  const { setCurrentTeam } = useTeamStore();

  const [formData, setFormData] = useState<TeamCreationFormData>({
    name: '',
    description: '',
    website: '',
    industry: '',
    size: 'startup',
    country: '',
  });

  const [errors, setErrors] = useState<Partial<Record<keyof TeamCreationFormData, string>>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isCheckingExistingTeam, setIsCheckingExistingTeam] = useState(true);
  const [retryCount, setRetryCount] = useState(0);

  // Check authentication and existing team ownership
  useEffect(() => {
    const checkAuthAndTeam = async () => {
      // Wait for auth to initialize
      if (authLoading) {
        return;
      }

      // Redirect to sign-in if not authenticated
      if (!isAuthenticated || !user) {
        toast.error('Please sign in to continue');
        router.push('/signin');
        return;
      }

      // Check if user already owns a team
      try {
        setIsCheckingExistingTeam(true);
        const organizationId = user.tenant_id;

        if (!organizationId) {
          toast.error('No organization found. Please contact support.');
          router.push('/admin/organization-dashboard');
          return;
        }

        // Fetch teams for the organization
        const teams = await teamService.fetchTeams(organizationId);
        
        // Check if user is already a team leader
        const userTeam = teams.find(
          (team) => team.team_leader_email === user.email || team.team_leader_id === user.id
        );

        if (userTeam) {
          toast.info('You already have a team. Redirecting to dashboard...');
          // Type assertion since TeamResponse has optional fields that Team requires
          setCurrentTeam(userTeam as any);
          router.push('/admin/team-leader-dashboard');
          return;
        }
      } catch (error: any) {
        console.error('Error checking existing team:', error);
        // Don't block the user if there's an error checking teams
        // They might be creating their first team
      } finally {
        setIsCheckingExistingTeam(false);
      }
    };

    checkAuthAndTeam();
  }, [isAuthenticated, authLoading, user, router, setCurrentTeam]);

  // Handle form field changes
  const handleChange = (field: keyof TeamCreationFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  // Real-time field validation
  const validateField = (field: keyof TeamCreationFormData, value: string) => {
    try {
      const fieldSchema = teamCreationSchema.shape[field];
      fieldSchema.parse(value);
      
      // Clear error if validation passes
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    } catch (error) {
      if (error instanceof z.ZodError) {
        setErrors((prev) => ({
          ...prev,
          [field]: error.issues[0]?.message || 'Invalid value',
        }));
      }
    }
  };

  // Handle form submission with retry logic
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate entire form
    try {
      teamCreationSchema.parse(formData);
      setErrors({});
    } catch (error) {
      if (error instanceof z.ZodError) {
        const fieldErrors: Partial<Record<keyof TeamCreationFormData, string>> = {};
        error.issues.forEach((err: any) => {
          if (err.path[0]) {
            fieldErrors[err.path[0] as keyof TeamCreationFormData] = err.message;
          }
        });
        setErrors(fieldErrors);
        toast.error('Please fix the errors in the form');
        return;
      }
    }

    if (!user?.tenant_id) {
      toast.error('Organization context not found');
      return;
    }

    setIsLoading(true);

    try {
      // Call team creation API
      const response = await teamService.createTeam(user.tenant_id, {
        name: formData.name,
        description: formData.description || '',
        website: formData.website || '',
        industry: formData.industry,
        size: formData.size,
        country: formData.country,
        settings: { additionalProp1: {} },
      });

      // Success: clear token, show success toast
      InvitationFlowManager.clearInvitationToken();
      toast.success('Team created successfully! Redirecting to your team workspace...');
      
      // Fetch the newly created team details while still in organization context
      const teams = await teamService.fetchTeams(user.tenant_id);
      const newTeam = teams.find((team) => team.id === response.id);
      
      if (newTeam) {
        // Set team in store (still using org token)
        setCurrentTeam({
          id: newTeam.id,
          name: newTeam.name || 'Unnamed Team',
          organization_id: newTeam.organization_id,
          organization_name: newTeam.organization_name || '',
          team_leader_id: newTeam.team_leader_id || '',
          team_leader_name: newTeam.team_leader_name || '',
          team_leader_email: newTeam.team_leader_email || '',
          member_count: newTeam.member_count || 0,
          credit_pool_total: newTeam.credit_pool_total || 0,
          credit_pool_used: newTeam.credit_pool_used || 0,
          credit_pool_remaining: newTeam.credit_pool_remaining || 0,
          pool_reset_date: newTeam.pool_reset_date || '',
          status: newTeam.status || 'active',
          created_at: newTeam.created_at || ''
        });
      }
      
      // Redirect to team workspace dashboard
      // The dashboard will auto-switch to team tenant context
      console.log(`📍 Redirecting to team dashboard: ${response.id}`);
      router.push(`/team-workspace/${response.id}/dashboard`);
    } catch (error: any) {
      console.error('Error creating team:', error);
      
      // Handle network failures with retry logic (max 2 retries)
      if (
        (error.message?.includes('network') || error.message?.includes('fetch')) &&
        retryCount < 2
      ) {
        setRetryCount((prev) => prev + 1);
        toast.error(`Network error. Retrying... (${retryCount + 1}/2)`);
        
        // Retry after a short delay
        setTimeout(() => {
          handleSubmit(e);
        }, 1000);
        return;
      }

      // Display field-specific errors or general error message
      if (error.message?.includes('name')) {
        setErrors({ name: 'Team name already exists or is invalid' });
      } else if (error.message?.includes('already exists')) {
        toast.error('You already have a team in this organization');
        router.push('/admin/team-leader-dashboard');
      } else {
        toast.error(error.message || 'Failed to create team. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Show loading state while checking authentication and existing team
  if (authLoading || isCheckingExistingTeam) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-4">
          <Loader2 className="w-12 h-12 animate-spin text-brand-500 mx-auto" />
          <p className="text-gray-600 dark:text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 rounded-full bg-brand-500 flex items-center justify-center">
              <Building2 className="w-8 h-8 text-white" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Create Your Team
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Set up your team workspace to start collaborating with your members
          </p>
        </div>

        {/* Form Card */}
        <Card>
          <CardHeader>
            <CardTitle>Team Information</CardTitle>
            <CardDescription>
              Provide details about your team. You can update these later in settings.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Team Name */}
              <div className="space-y-2">
                <Label htmlFor="name">
                  Team Name <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="name"
                  type="text"
                  placeholder="e.g., Engineering Team"
                  value={formData.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  onBlur={(e) => validateField('name', e.target.value)}
                  aria-invalid={!!errors.name}
                  className={errors.name ? 'border-red-500' : ''}
                />
                {errors.name && (
                  <div className="flex items-center gap-2 text-red-500 text-sm">
                    <AlertCircle className="w-4 h-4" />
                    <span>{errors.name}</span>
                  </div>
                )}
              </div>

              {/* Description */}
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <textarea
                  id="description"
                  placeholder="Brief description of your team's purpose and goals"
                  value={formData.description}
                  onChange={(e) => handleChange('description', e.target.value)}
                  onBlur={(e) => validateField('description', e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
                {errors.description && (
                  <div className="flex items-center gap-2 text-red-500 text-sm">
                    <AlertCircle className="w-4 h-4" />
                    <span>{errors.description}</span>
                  </div>
                )}
              </div>

              {/* Website */}
              <div className="space-y-2">
                <Label htmlFor="website">Website</Label>
                <Input
                  id="website"
                  type="url"
                  placeholder="https://example.com"
                  value={formData.website}
                  onChange={(e) => handleChange('website', e.target.value)}
                  onBlur={(e) => validateField('website', e.target.value)}
                  aria-invalid={!!errors.website}
                  className={errors.website ? 'border-red-500' : ''}
                />
                {errors.website && (
                  <div className="flex items-center gap-2 text-red-500 text-sm">
                    <AlertCircle className="w-4 h-4" />
                    <span>{errors.website}</span>
                  </div>
                )}
              </div>

              {/* Industry */}
              <div className="space-y-2">
                <Label htmlFor="industry">
                  Industry <span className="text-red-500">*</span>
                </Label>
                <Select
                  value={formData.industry}
                  onValueChange={(value) => handleChange('industry', value)}
                >
                  <SelectTrigger
                    id="industry"
                    className={`w-full ${errors.industry ? 'border-red-500' : ''}`}
                  >
                    <SelectValue placeholder="Select an industry" />
                  </SelectTrigger>
                  <SelectContent>
                    {industryOptions.map((industry) => (
                      <SelectItem key={industry} value={industry}>
                        {industry}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.industry && (
                  <div className="flex items-center gap-2 text-red-500 text-sm">
                    <AlertCircle className="w-4 h-4" />
                    <span>{errors.industry}</span>
                  </div>
                )}
              </div>

              {/* Team Size */}
              <div className="space-y-2">
                <Label htmlFor="size">
                  Team Size <span className="text-red-500">*</span>
                </Label>
                <Select
                  value={formData.size}
                  onValueChange={(value) => handleChange('size', value as TeamCreationFormData['size'])}
                >
                  <SelectTrigger
                    id="size"
                    className={`w-full ${errors.size ? 'border-red-500' : ''}`}
                  >
                    <SelectValue placeholder="Select team size" />
                  </SelectTrigger>
                  <SelectContent>
                    {teamSizeOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.size && (
                  <div className="flex items-center gap-2 text-red-500 text-sm">
                    <AlertCircle className="w-4 h-4" />
                    <span>{errors.size}</span>
                  </div>
                )}
              </div>

              {/* Country */}
              <div className="space-y-2">
                <Label htmlFor="country">
                  Country <span className="text-red-500">*</span>
                </Label>
                <Select
                  value={formData.country}
                  onValueChange={(value) => handleChange('country', value)}
                >
                  <SelectTrigger
                    id="country"
                    className={`w-full ${errors.country ? 'border-red-500' : ''}`}
                  >
                    <SelectValue placeholder="Select a country" />
                  </SelectTrigger>
                  <SelectContent>
                    {countryOptions.map((country) => (
                      <SelectItem key={country} value={country}>
                        {country}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.country && (
                  <div className="flex items-center gap-2 text-red-500 text-sm">
                    <AlertCircle className="w-4 h-4" />
                    <span>{errors.country}</span>
                  </div>
                )}
              </div>

              {/* Submit Button */}
              <div className="flex items-center justify-end gap-4 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => router.back()}
                  disabled={isLoading}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isLoading}
                  className="min-w-[150px]"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      Create Team
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Help Text */}
        <div className="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
          <p>
            Need help? Contact support at{' '}
            <a href="mailto:support@yuba.com" className="text-brand-500 hover:underline">
              support@yuba.com
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
