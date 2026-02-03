"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { organizationService } from '@/lib/api/organizationService';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores/authStore';
import { toast } from "react-hot-toast";
import { Settings, Building2, Mail, Phone, MapPin, Globe, Users, Trash2, Save, AlertTriangle } from 'lucide-react';

interface Organization {
  id: string;
  name: string;
  description?: string;
  website?: string;
  industry?: string;
  size?: string;
  country: string;
  city: string;
  contact_email: string;
  phone_number: string;
  type?: 'prepay_org' | 'grant_org';
  monthly_credit_limit?: number;
  created_at: string;
  updated_at: string;
  status: 'active' | 'suspended' | 'frozen';
}

export default function OrganizationSettingsPage() {
  const router = useRouter();
  const params = useParams();
  const organizationId = params.id as string;
  const { isAuthenticated } = useAuthStore();
  
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [formData, setFormData] = useState<Partial<Organization>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    // if (!isAuthenticated) {
    //   router.push('/signin?redirect=/admin/organizations/' + organizationId + '/settings');
    //   return;
    // }
    
    if (organizationId) {
      fetchOrganizationData();
    }
  }, [organizationId, isAuthenticated]);

  const fetchOrganizationData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch organization details
      const organizations = await organizationService.fetchOrganizations();
      const org = organizations.find((o: any) => o.id === organizationId) || null;
      
      if (!org) {
        throw new Error('Organization not found');
      }
      
      setOrganization(org);
      setFormData(org);
    } catch (err: any) {
      console.error('Error fetching organization data:', err);
      setError(err.message || 'Failed to fetch organization data');
      toast.error(err.message || 'Failed to fetch organization data');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      
      // Prepare update data - only send changed fields
      const updateData: any = {};
      const fieldsToCheck = ['name', 'description', 'website', 'industry', 'size', 'country', 'city', 'contact_email', 'phone_number'];
      
      fieldsToCheck.forEach(field => {
        if (formData[field as keyof typeof formData] !== organization?.[field as keyof Organization]) {
          updateData[field] = formData[field as keyof typeof formData];
        }
      });
      
      // If no changes, just show a message
      if (Object.keys(updateData).length === 0) {
        toast.info('No changes to save');
        return;
      }
      
      // Call the backend API to update organization
      const result = await organizationService.updateOrganization(organizationId, updateData);
      
      if (result.success) {
        toast.success('Organization settings updated successfully');
        
        // Update local state with the returned data
        if (result.data) {
          setOrganization(result.data);
          setFormData(result.data);
        }
        
        // Refresh the data to ensure consistency
        await fetchOrganizationData();
      }
    } catch (err: any) {
      console.error('Error saving organization settings:', err);
      toast.error(err.message || 'Failed to update organization settings');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      await organizationService.deleteOrganization(organizationId);
      toast.success('Organization deleted successfully');
      router.push('/admin/organizations');
    } catch (err: any) {
      toast.error(err.message || 'Failed to delete organization');
    }
  };

  const handleBack = () => {
    router.push(`/admin/organizations/${organizationId}`);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  if (error || !organization) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
        <div className="text-red-800 dark:text-red-200">
          <h3 className="font-medium">Error loading organization settings</h3>
          <p className="mt-1 text-sm">{error}</p>
          <div className="flex space-x-3 mt-3">
            <button
              onClick={handleBack}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-sm"
            >
              Back to Organization
            </button>
            <button
              onClick={fetchOrganizationData}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button 
            variant="ghost" 
            size="icon"
            onClick={handleBack}
          >
            <span className="text-lg">⬅️</span>
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Organization Settings
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Manage organization details and configuration
            </p>
          </div>
        </div>
        <div className="flex space-x-3">
          <Button onClick={handleSave} disabled={saving}>
            <Save className="w-4 h-4 mr-2" />
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      {/* Organization Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Building2 className="w-5 h-5" />
            <span>Organization Status</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Current Status</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Organization operational status</p>
            </div>
            <Badge className={
              organization.status === 'active' 
                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
            }>
              {organization.status}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Organization Type</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Billing and credit model</p>
            </div>
            <Badge className={
              organization.type === 'prepay_org' 
                ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' 
                : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
            }>
              {organization.type === 'prepay_org' ? 'Prepayment' : 'Grant'}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Basic Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Settings className="w-5 h-5" />
            <span>Basic Information</span>
          </CardTitle>
          <CardDescription>
            Update organization details and contact information
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Organization Name *
              </label>
              <input
                type="text"
                name="name"
                value={formData.name || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-gray-700 dark:text-white"
                placeholder="Enter organization name"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Industry
              </label>
              <input
                type="text"
                name="industry"
                value={formData.industry || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-gray-700 dark:text-white"
                placeholder="e.g., Technology, Healthcare"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Organization Size
              </label>
              <select
                name="size"
                value={formData.size || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-gray-700 dark:text-white"
              >
                <option value="">Select size</option>
                <option value="startup">Startup (1-10 employees)</option>
                <option value="small">Small (11-50 employees)</option>
                <option value="medium">Medium (51-200 employees)</option>
                <option value="large">Large (201-1000 employees)</option>
                <option value="enterprise">Enterprise (1000+ employees)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Website
              </label>
              <input
                type="url"
                name="website"
                value={formData.website || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-gray-700 dark:text-white"
                placeholder="https://example.com"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Description
            </label>
            <textarea
              name="description"
              value={formData.description || ''}
              onChange={handleInputChange}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-gray-700 dark:text-white"
              placeholder="Brief description of your organization"
            />
          </div>
        </CardContent>
      </Card>

      {/* Contact Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Mail className="w-5 h-5" />
            <span>Contact Information</span>
          </CardTitle>
          <CardDescription>
            Organization contact details and location
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Contact Email *
              </label>
              <input
                type="email"
                name="contact_email"
                value={formData.contact_email || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-gray-700 dark:text-white"
                placeholder="contact@organization.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Phone Number *
              </label>
              <input
                type="tel"
                name="phone_number"
                value={formData.phone_number || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-gray-700 dark:text-white"
                placeholder="+1 (555) 123-4567"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Country *
              </label>
              <input
                type="text"
                name="country"
                value={formData.country || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-gray-700 dark:text-white"
                placeholder="United States"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                City *
              </label>
              <input
                type="text"
                name="city"
                value={formData.city || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-gray-700 dark:text-white"
                placeholder="New York"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-red-200 dark:border-red-800">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2 text-red-600 dark:text-red-400">
            <AlertTriangle className="w-5 h-5" />
            <span>Danger Zone</span>
          </CardTitle>
          <CardDescription>
            Irreversible actions that will permanently affect your organization
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-red-800 dark:text-red-200">Delete Organization</h4>
                <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                  Permanently delete this organization and all associated data. This action cannot be undone.
                </p>
              </div>
              <Button
                variant="destructive"
                onClick={() => setShowDeleteConfirm(true)}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center space-x-3 mb-4">
              <AlertTriangle className="w-6 h-6 text-red-500" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Delete Organization
              </h3>
            </div>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Are you sure you want to delete "{organization.name}"? This action cannot be undone and will permanently remove all organization data, teams, and member access.
            </p>
            <div className="flex space-x-3">
              <Button
                variant="outline"
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDelete}
                className="flex-1"
              >
                Delete Organization
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
