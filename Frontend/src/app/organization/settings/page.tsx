"use client"

import type React from "react"
import { useState, useEffect, useCallback, useMemo } from "react"
import { useRouter } from "next/navigation"
import { organizationService } from "@/lib/api/organizationService"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useAuthStore } from "@/stores/authStore"
import { toast } from "sonner"
import {
  Settings,
  Building2,
  Mail,
  Trash2,
  Save,
  AlertTriangle,
  ArrowLeft,
  RefreshCw,
  Eye,
  EyeOff,
  Shield,
  CreditCard,
  Calendar,
  Download,
  ChevronDown,
} from "lucide-react"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

interface Organization {
  id: string
  name: string
  description?: string
  website?: string
  industry?: string
  size?: string
  country: string
  city: string
  contact_email: string
  phone_number: string
  type?: "prepay_org" | "grant_org"
  monthly_credit_limit?: number
  created_at: string
  updated_at: string
  status: "active" | "suspended" | "frozen"
}

interface FormData {
  name: string
  description: string
  website: string
  industry: string
  size: string
  country: string
  city: string
  contact_email: string
  phone_number: string
}

export default function OrganizationSettingsPage() {
  const router = useRouter()
  const { user, isAuthenticated, token } = useAuthStore()
  const currentWorkspaceTenantId = user?.tenant_id

  // Get organization ID with proper fallback
  const organizationId = currentWorkspaceTenantId

  const [organization, setOrganization] = useState<Organization | null>(null)
  const [formData, setFormData] = useState<FormData>({
    name: "",
    description: "",
    website: "",
    industry: "",
    size: "",
    country: "",
    city: "",
    contact_email: "",
    phone_number: "",
  })
  const [originalData, setOriginalData] = useState<FormData | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [deleteConfirmText, setDeleteConfirmText] = useState("")

  const fetchOrganizationData = useCallback(async () => {
    // Check authentication first
    if (!isAuthenticated) {
      if (process.env.NODE_ENV === "development") {
        console.log("User not authenticated, redirecting to signin")
      }
      router.push("/signin?redirect=" + encodeURIComponent(window.location.pathname))
      return
    }

    // Check organization ID
    if (!organizationId) {
      if (process.env.NODE_ENV === "development") {
        console.log("No organization ID available, redirecting to workspace selection")
      }
      setError("No organization selected. Please select a workspace.")
      toast.error("No organization selected. Please select a workspace.")
      router.push("/team-workspaces")
      return
    }

    let retryAttempts = 0
    const maxRetries = 3
    const baseDelay = 1000

    const attemptFetch = async (): Promise<void> => {
      try {
        setLoading(true)
        setError(null)

        if (process.env.NODE_ENV === "development") {
          console.log("Fetching organization data for ID:", organizationId)
        }

        // Try multiple methods to fetch organization data
        let org: Organization | null = null

        try {
          // Method 1: Direct organization endpoint
          if (typeof organizationService.getOrganizationById === "function") {
            org = await organizationService.getOrganizationById(organizationId)
          }
        } catch (error: any) {
          if (process.env.NODE_ENV === "development") {
            console.warn("Method 1 failed, trying fallback:", error)
          }

          // Handle specific HTTP errors
          if (error.status === 401) {
            toast.error("Authentication expired. Please sign in again.")
            router.push("/signin?redirect=" + encodeURIComponent(window.location.pathname))
            return
          } else if (error.status === 403) {
            toast.error("You do not have permission to access this organization.")
            router.push("/team-workspaces")
            return
          } else if (error.status === 404) {
            toast.error("Organization not found.")
            router.push("/team-workspaces")
            return
          }
        }

        // Method 2: Fallback to list endpoint
        if (!org) {
          try {
            const organizations = await organizationService.fetchOrganizations()
            org = organizations.find((o: any) => o.id === organizationId) || null
          } catch (error: any) {
            if (process.env.NODE_ENV === "development") {
              console.warn("Method 2 failed:", error)
            }

            // Handle specific HTTP errors for fallback method
            if (error.status === 401) {
              toast.error("Authentication expired. Please sign in again.")
              router.push("/signin?redirect=" + encodeURIComponent(window.location.pathname))
              return
            } else if (error.status === 403) {
              toast.error("You do not have permission to access organizations.")
              router.push("/team-workspaces")
              return
            }
          }
        }

        if (!org) {
          throw new Error("Organization not found. Please check if you have access to this organization.")
        }

        setOrganization(org)

        // Initialize form data
        const initialFormData: FormData = {
          name: org.name || "",
          description: org.description || "",
          website: org.website || "",
          industry: org.industry || "",
          size: org.size || "",
          country: org.country || "",
          city: org.city || "",
          contact_email: org.contact_email || "",
          phone_number: org.phone_number || "",
        }

        setFormData(initialFormData)
        setOriginalData(initialFormData)

        if (process.env.NODE_ENV === "development") {
          console.log("Organization data loaded successfully:", org)
        }
      } catch (err: any) {
        console.error("Error fetching organization data:", err)

        // Check if it's a network error and we should retry
        const isNetworkError = !err.status || err.name === "NetworkError" || err.message.includes("fetch")

        if (isNetworkError && retryAttempts < maxRetries) {
          retryAttempts++
          const delay = baseDelay * Math.pow(2, retryAttempts - 1)

          if (process.env.NODE_ENV === "development") {
            console.log(`Retrying in ${delay}ms (attempt ${retryAttempts}/${maxRetries})`)
          }

          setTimeout(() => {
            attemptFetch()
          }, delay)
          return
        }

        const errorMessage = err.message || "Failed to fetch organization data"
        setError(errorMessage)
        toast.error(errorMessage)
      } finally {
        setLoading(false)
      }
    }

    await attemptFetch()
  }, [organizationId, isAuthenticated, router, retryCount])

  useEffect(() => {
    fetchOrganizationData()
  }, [fetchOrganizationData])

  // Check if form has changes
  const hasChanges = useMemo(() => {
    if (!originalData) return false
    return Object.keys(formData).some((key) => formData[key as keyof FormData] !== originalData[key as keyof FormData])
  }, [formData, originalData])

  // Check if delete is confirmed (text matches organization name)
  const isDeleteConfirmed = useMemo(() => {
    return organization && deleteConfirmText === organization.name
  }, [deleteConfirmText, organization])

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
      const { name, value } = e.target
      setFormData((prev) => ({
        ...prev,
        [name]: value,
      }))
    },
    [],
  )

  const handleSave = useCallback(async () => {
    // Check authentication
    if (!isAuthenticated) {
      toast.error("Please sign in to save changes")
      router.push("/signin?redirect=" + encodeURIComponent(window.location.pathname))
      return
    }

    // Check organization ID
    if (!organizationId) {
      toast.error("No organization selected")
      router.push("/team-workspaces")
      return
    }

    try {
      setSaving(true)

      // Basic validation
      if (!formData.name.trim()) {
        toast.error("Organization name is required")
        return
      }
      if (!formData.contact_email.trim()) {
        toast.error("Contact email is required")
        return
      }
      if (!formData.phone_number.trim()) {
        toast.error("Phone number is required")
        return
      }

      // Prepare update data - only send changed fields
      const updateData: any = {}
      const fieldsToCheck = [
        "name",
        "description",
        "website",
        "industry",
        "size",
        "country",
        "city",
        "contact_email",
        "phone_number",
      ]

      fieldsToCheck.forEach((field) => {
        if (formData[field as keyof FormData] !== originalData?.[field as keyof FormData]) {
          updateData[field] = formData[field as keyof FormData]
        }
      })

      // If no changes, just show a message
      if (Object.keys(updateData).length === 0) {
        toast.info("No changes to save")
        return
      }

      if (process.env.NODE_ENV === "development") {
        console.log("Updating organization with data:", updateData)
      }

      // Call the backend API to update organization
      const result = await organizationService.updateOrganization(organizationId, updateData)

      if (result.success) {
        toast.success("Organization settings updated successfully")

        // Update local state with the returned data
        if (result.data) {
          setOrganization(result.data)
          const newFormData: FormData = {
            name: result.data.name || "",
            description: result.data.description || "",
            website: result.data.website || "",
            industry: result.data.industry || "",
            size: result.data.size || "",
            country: result.data.country || "",
            city: result.data.city || "",
            contact_email: result.data.contact_email || "",
            phone_number: result.data.phone_number || "",
          }
          setFormData(newFormData)
          setOriginalData(newFormData)
        } else {
          // Refresh the data to ensure consistency
          await fetchOrganizationData()
        }
      }
    } catch (err: any) {
      console.error("Error saving organization settings:", err)

      // Handle specific HTTP errors
      if (err.status === 401) {
        toast.error("Authentication expired. Please sign in again.")
        router.push("/signin?redirect=" + encodeURIComponent(window.location.pathname))
      } else if (err.status === 403) {
        toast.error("You do not have permission to update this organization.")
      } else if (err.status === 404) {
        toast.error("Organization not found.")
        router.push("/team-workspaces")
      } else {
        toast.error(err.message || "Failed to update organization settings")
      }
    } finally {
      setSaving(false)
    }
  }, [formData, originalData, organizationId, isAuthenticated, router, fetchOrganizationData])

  const handleDelete = useCallback(async () => {
    if (!isDeleteConfirmed) {
      toast.error("Please type the organization name to confirm deletion")
      return
    }

    // Check authentication
    if (!isAuthenticated) {
      toast.error("Please sign in to delete organization")
      router.push("/signin?redirect=" + encodeURIComponent(window.location.pathname))
      return
    }

    // Check organization ID
    if (!organizationId) {
      toast.error("No organization selected")
      router.push("/team-workspaces")
      return
    }

    try {
      if (process.env.NODE_ENV === "development") {
        console.log("Deleting organization:", organizationId)
      }

      await organizationService.deleteOrganization(organizationId)
      toast.success("Organization deleted successfully")
      router.push("/organization")
    } catch (err: any) {
      console.error("Error deleting organization:", err)

      // Handle specific HTTP errors
      if (err.status === 401) {
        toast.error("Authentication expired. Please sign in again.")
        router.push("/signin?redirect=" + encodeURIComponent(window.location.pathname))
      } else if (err.status === 403) {
        toast.error("You do not have permission to delete this organization.")
      } else if (err.status === 404) {
        toast.error("Organization not found.")
        router.push("/team-workspaces")
      } else {
        toast.error(err.message || "Failed to delete organization")
      }
    } finally {
      setShowDeleteConfirm(false)
      setDeleteConfirmText("")
    }
  }, [isDeleteConfirmed, organizationId, isAuthenticated, router])

  const handleBack = useCallback(() => {
    if (hasChanges) {
      if (confirm("You have unsaved changes. Are you sure you want to leave?")) {
        router.push("/organization")
      }
    } else {
      router.push("/organization")
    }
  }, [hasChanges, router])

  const handleBackToWorkspaces = useCallback(() => {
    router.push("/team-workspaces")
  }, [router])

  const handleRetry = useCallback(() => {
    setRetryCount((prev) => prev + 1)
    toast.success("Retrying to fetch organization data...")
  }, [])

  const handleReset = useCallback(() => {
    if (originalData) {
      setFormData(originalData)
      toast.success("Changes reset")
    }
  }, [originalData])

  const handleExportData = useCallback(() => {
    toast.success("Exporting organization data...")
    // Implement export functionality here
  }, [])

  const getOrganizationSizeLabel = useMemo(
    () => (size: string) => {
      switch (size) {
        case "startup":
          return "Startup (1-10 employees)"
        case "small":
          return "Small (11-50 employees)"
        case "medium":
          return "Medium (51-200 employees)"
        case "large":
          return "Large (201-1000 employees)"
        case "enterprise":
          return "Enterprise (1000+ employees)"
        default:
          return size
      }
    },
    [],
  )

  const formatDate = useMemo(
    () => (dateString: string) => {
      return new Date(dateString).toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    },
    [],
  )

  // Loading State
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white dark:from-slate-950 dark:to-slate-900 p-6">
        <div className="max-w-5xl mx-auto space-y-6">
          {/* Header Skeleton */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Skeleton className="h-10 w-10 rounded-md" />
              <div className="space-y-2">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-4 w-96" />
              </div>
            </div>
            <Skeleton className="h-10 w-32" />
          </div>

          {/* Status Card Skeleton */}
          <Skeleton className="h-48 w-full" />

          {/* Basic Info Skeleton */}
          <div className="space-y-4">
            <Skeleton className="h-6 w-48" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[...Array(6)].map((_, i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          </div>

          {/* Contact Info Skeleton */}
          <div className="space-y-4">
            <Skeleton className="h-6 w-48" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Error State
  if (error || !organization) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white dark:from-slate-950 dark:to-slate-900 p-6">
        <div className="max-w-5xl mx-auto space-y-6">
          {/* Header */}
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={handleBack}
              className="hover:bg-slate-200 dark:hover:bg-slate-800"
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Organization Settings</h1>
              <p className="text-slate-600 dark:text-slate-400 mt-1">Manage organization details and configuration</p>
            </div>
          </div>

          {/* Error Card */}
          <Card className="border-red-200 dark:border-red-900 bg-white dark:bg-slate-950 shadow-lg">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0">
                  <AlertTriangle className="w-6 h-6 text-red-500 mt-0.5" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-red-900 dark:text-red-200 text-lg">
                    Unable to Load Organization Settings
                  </h3>
                  <p className="text-red-700 dark:text-red-300 mt-2">{error || "Organization not found"}</p>
                  <div className="flex flex-wrap gap-3 mt-6">
                    <Button
                      onClick={handleRetry}
                      className="flex items-center space-x-2 bg-red-600 hover:bg-red-700 text-white"
                    >
                      <RefreshCw className="w-4 h-4" />
                      <span>Try Again</span>
                    </Button>
                    <Button variant="outline" onClick={handleBack}>
                      Back to Organization
                    </Button>
                    <Button variant="outline" onClick={handleBackToWorkspaces}>
                      Select Workspace
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 py-2">
      <div className="mx-auto space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={handleBack}
              className="hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-brand-500 dark:text-brand-400">Organization Settings</h1>
              <p className="text-slate-500 dark:text-slate-400 ">Manage and configure your organization details</p>
            </div>
          </div>
          <div className="flex gap-2 flex-wrap justify-end">
            {hasChanges && (
              <Button
                variant="outline"
                onClick={handleReset}
                disabled={saving}
                className="transition-all hover:bg-slate-100 dark:hover:bg-slate-800 bg-transparent"
              >
                Reset
              </Button>
            )}
            <Button
              onClick={handleSave}
              disabled={saving || !hasChanges}
              className="flex items-center space-x-2 bg-brand-600 hover:bg-brand-700 text-white disabled:bg-slate-300 disabled:cursor-not-allowed transition-all shadow-sm"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? "Saving..." : "Save Changes"}</span>
            </Button>
          </div>
        </div>

        {/* Organization Overview - Improved Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card className="lg:col-span-1 shadow-sm hover:shadow-md transition-shadow border-slate-200 dark:border-slate-800">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2 text-lg">
                <Building2 className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                <span>Organization Overview </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              

              {/* Type Item */}
              <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-900 rounded-lg">
                <div className="flex items-center space-x-2">
                  <CreditCard className="w-4 h-4 text-slate-400" />
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Type</span>
                </div>
                <Badge
                  className={`${
                    organization.type === "prepay_org"
                      ? "bg-brand-100 text-brand-800 dark:bg-brand-900/30 dark:text-brand-400"
                      : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400"
                  } font-medium`}
                >
                  {organization.type === "prepay_org" ? "Prepayment" : "Grant"}
                </Badge>
              </div>

              {/* Created Date */}
              <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-900 rounded-lg">
                <div className="flex items-center space-x-2">
                  <Calendar className="w-4 h-4 text-slate-400" />
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Created</span>
                </div>
                <span className="text-sm text-slate-600 dark:text-slate-400 font-medium">
                  {formatDate(organization.created_at)}
                </span>
              </div>

              {/* Last Updated */}
              <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-900 rounded-lg">
                <div className="flex items-center space-x-2">
                  <RefreshCw className="w-4 h-4 text-slate-400" />
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Last Updated</span>
                </div>
                <span className="text-sm text-slate-600 dark:text-slate-400 font-medium">
                  {formatDate(organization.updated_at)}
                </span>
              </div>

              {/* Credit Limit */}
              {organization.monthly_credit_limit && (
                <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
                  <div className="flex items-center space-x-2">
                    <CreditCard className="w-4 h-4 text-slate-400" />
                    <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Credit Limit</span>
                  </div>
                  <span className="text-sm font-bold text-brand-600 dark:text-brand-400">
                    ${organization.monthly_credit_limit.toLocaleString()}
                  </span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Basic Information Card */}
          <Card className="lg:col-span-2 shadow-sm hover:shadow-md transition-shadow border-slate-200 dark:border-slate-800">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center space-x-2 text-lg">
                <Settings className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                <span>Basic Information</span>
              </CardTitle>
              <CardDescription className="text-slate-500 dark:text-slate-400">
                Update organization details and contact information
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Organization Name */}
                <div className="space-y-2">
                  <Label htmlFor="name" className="font-semibold text-slate-700 dark:text-slate-300">
                    Organization Name <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder="Enter organization name"
                    className="transition-all focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
                  />
                </div>

                {/* Industry */}
                <div className="space-y-2">
                  <Label htmlFor="industry" className="font-semibold text-slate-700 dark:text-slate-300">
                    Industry
                  </Label>
                  <Input
                    id="industry"
                    name="industry"
                    value={formData.industry}
                    onChange={handleInputChange}
                    placeholder="e.g., Technology, Healthcare"
                    className="transition-all focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
                  />
                </div>

                {/* Organization Size */}
                <div className="space-y-2">
                  <Label htmlFor="size" className="font-semibold text-slate-700 dark:text-slate-300">
                    Organization Size
                  </Label>
                  <select
                    id="size"
                    name="size"
                    value={formData.size}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent dark:bg-slate-800 dark:text-white transition-all"
                  >
                    <option value="">Select size</option>
                    <option value="startup">Startup (1-10 employees)</option>
                    <option value="small">Small (11-50 employees)</option>
                    <option value="medium">Medium (51-200 employees)</option>
                    <option value="large">Large (201-1000 employees)</option>
                    <option value="enterprise">Enterprise (1000+ employees)</option>
                  </select>
                </div>

                {/* Website */}
                <div className="space-y-2">
                  <Label htmlFor="website" className="font-semibold text-slate-700 dark:text-slate-300">
                    Website
                  </Label>
                  <Input
                    id="website"
                    name="website"
                    type="url"
                    value={formData.website}
                    onChange={handleInputChange}
                    placeholder="https://example.com"
                    className="transition-all focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
                  />
                </div>
              </div>

              {/* Description */}
              <div className="space-y-2">
                <Label htmlFor="description" className="font-semibold text-slate-700 dark:text-slate-300">
                  Description
                </Label>
                <Textarea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  rows={3}
                  placeholder="Brief description of your organization"
                  className="transition-all focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 resize-none"
                />
                <div className="flex justify-between items-center">
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Provide a brief overview of your organization
                  </p>
                  <p
                    className={`text-xs font-medium ${formData.description.length > 450 ? "text-orange-600 dark:text-orange-400" : "text-slate-500 dark:text-slate-400"}`}
                  >
                    {formData.description.length}/500
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Contact Information Card */}
        <Card className="shadow-sm hover:shadow-md transition-shadow border-slate-200 dark:border-slate-800">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center space-x-2 text-lg">
              <Mail className="w-5 h-5 text-brand-600 dark:text-brand-400" />
              <span>Contact Information</span>
            </CardTitle>
            <CardDescription className="text-slate-500 dark:text-slate-400">
              Organization contact details and location
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Contact Email */}
              <div className="space-y-2">
                <Label htmlFor="contact_email" className="font-semibold text-slate-700 dark:text-slate-300">
                  Contact Email <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="contact_email"
                  name="contact_email"
                  type="email"
                  value={formData.contact_email}
                  onChange={handleInputChange}
                  placeholder="contact@organization.com"
                  className="transition-all focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
                />
              </div>

              {/* Phone Number */}
              <div className="space-y-2">
                <Label htmlFor="phone_number" className="font-semibold text-slate-700 dark:text-slate-300">
                  Phone Number <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="phone_number"
                  name="phone_number"
                  type="tel"
                  value={formData.phone_number}
                  onChange={handleInputChange}
                  placeholder="+1 (555) 123-4567"
                  className="transition-all focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
                />
              </div>

              {/* Country */}
              <div className="space-y-2">
                <Label htmlFor="country" className="font-semibold text-slate-700 dark:text-slate-300">
                  Country <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="country"
                  name="country"
                  value={formData.country}
                  onChange={handleInputChange}
                  placeholder="United States"
                  className="transition-all focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
                />
              </div>

              {/* City */}
              <div className="space-y-2">
                <Label htmlFor="city" className="font-semibold text-slate-700 dark:text-slate-300">
                  City <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="city"
                  name="city"
                  value={formData.city}
                  onChange={handleInputChange}
                  placeholder="New York"
                  className="transition-all focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Advanced Settings */}
        <Card className="shadow-sm hover:shadow-md transition-shadow border-slate-200 dark:border-slate-800">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center space-x-2 text-lg">
                  <Settings className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                  <span>Advanced Settings</span>
                </CardTitle>
                <CardDescription className="text-slate-500 dark:text-slate-400 mt-2">
                  Advanced organization configuration and settings
                </CardDescription>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center space-x-2 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all"
              >
                {showAdvanced ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                <span className="text-sm font-medium">{showAdvanced ? "Hide" : "Show"}</span>
                <ChevronDown className={`w-4 h-4 transition-transform ${showAdvanced ? "rotate-180" : ""}`} />
              </Button>
            </div>
          </CardHeader>
          {showAdvanced && (
            <CardContent className="space-y-6 border-t border-slate-200 dark:border-slate-800 pt-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Organization ID */}
                <div className="space-y-2">
                  <Label htmlFor="organization_id" className="font-semibold text-slate-700 dark:text-slate-300">
                    Organization ID
                  </Label>
                  <Input
                    id="organization_id"
                    value={organization.id}
                    readOnly
                    className="bg-slate-50 dark:bg-slate-900 font-mono text-sm border-slate-300 dark:border-slate-600 cursor-not-allowed"
                  />
                  <p className="text-xs text-slate-500 dark:text-slate-400">Unique identifier for your organization</p>
                </div>

                {/* API Key */}
                <div className="space-y-2">
                  <Label htmlFor="api_key" className="font-semibold text-slate-700 dark:text-slate-300">
                    API Key
                  </Label>
                  <div className="flex space-x-2">
                    <Input
                      id="api_key"
                      value="••••••••••••••••"
                      type="password"
                      readOnly
                      className="bg-slate-50 dark:bg-slate-900 font-mono border-slate-300 dark:border-slate-600 cursor-not-allowed"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      className="whitespace-nowrap hover:bg-slate-100 dark:hover:bg-slate-800 bg-transparent"
                    >
                      Regenerate
                    </Button>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Used for API integrations</p>
                </div>
              </div>

              {/* Security Settings */}
              <div className="space-y-4 pt-4 border-t border-slate-200 dark:border-slate-800">
                <Label className="font-semibold text-slate-700 dark:text-slate-300">Security Settings</Label>
                <div className="space-y-3">
                  {/* 2FA Option */}
                  <div className="flex items-center justify-between p-4 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                    <div>
                      <p className="font-medium text-slate-900 dark:text-slate-100">Two-Factor Authentication</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                        Require 2FA for all organization members
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      className="whitespace-nowrap hover:bg-slate-100 dark:hover:bg-slate-700 bg-transparent"
                    >
                      Configure
                    </Button>
                  </div>

                  {/* Session Management Option */}
                  <div className="flex items-center justify-between p-4 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                    <div>
                      <p className="font-medium text-slate-900 dark:text-slate-100">Session Management</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                        Manage active sessions and timeout settings
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      className="whitespace-nowrap hover:bg-slate-100 dark:hover:bg-slate-700 bg-transparent"
                    >
                      Manage
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          )}
        </Card>

        {/* Danger Zone */}
        <Card className="border-red-200 dark:border-red-900 shadow-sm hover:shadow-md transition-shadow bg-red-50 dark:bg-red-950/20">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center space-x-2 text-lg text-red-700 dark:text-red-400">
                <AlertTriangle className="w-5 h-5" />
                <span>Danger Zone</span>
              </CardTitle>
            </div>
            <CardDescription className="text-red-600 dark:text-red-400 mt-2">
              Irreversible actions that will permanently affect your organization
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Delete Organization */}
              <div className="bg-red-100 dark:bg-red-900/40 border border-red-300 dark:border-red-800 rounded-lg p-4 transition-all hover:shadow-sm">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h4 className="font-semibold text-red-900 dark:text-red-200">Delete Organization</h4>
                    <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                      Permanently delete this organization and all associated data. This action cannot be undone.
                    </p>
                  </div>
                  <Button
                    variant="destructive"
                    onClick={() => setShowDeleteConfirm(true)}
                    className="flex items-center space-x-2 whitespace-nowrap flex-shrink-0 bg-red-600 hover:bg-red-700 text-white"
                  >
                    <Trash2 className="w-4 h-4" />
                    <span>Delete</span>
                  </Button>
                </div>
              </div>

              {/* Export Data */}
              <div className="bg-amber-100 dark:bg-amber-900/40 border border-amber-300 dark:border-amber-800 rounded-lg p-4 transition-all hover:shadow-sm">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h4 className="font-semibold text-amber-900 dark:text-amber-200">Export Organization Data</h4>
                    <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                      Download all organization data including members, teams, and usage history.
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    onClick={handleExportData}
                    className="flex items-center space-x-2 whitespace-nowrap flex-shrink-0 hover:bg-amber-100 dark:hover:bg-amber-900/50 bg-transparent"
                  >
                    <Download className="w-4 h-4" />
                    <span>Export</span>
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <AlertDialogContent className="border-slate-200 dark:border-slate-800">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center space-x-2 text-red-600 dark:text-red-400 text-xl">
              <AlertTriangle className="w-5 h-5" />
              <span>Delete Organization</span>
            </AlertDialogTitle>
            <AlertDialogDescription className="text-slate-600 dark:text-slate-400">
              <div className="space-y-3 mt-4">
                <p>
                  Are you sure you want to delete{" "}
                  <strong className="text-slate-900 dark:text-slate-100">"{organization.name}"</strong>? This action
                  cannot be undone and will permanently:
                </p>
                <ul className="list-disc list-inside space-y-1 text-sm space-y-2">
                  <li>Remove all organization data</li>
                  <li>Delete all teams and member associations</li>
                  <li>Revoke access for all members</li>
                  <li>Remove credit allocations and usage history</li>
                  <li>Delete all organization settings</li>
                </ul>
                <p className="font-semibold text-slate-900 dark:text-slate-100 mt-4 pt-2 border-t border-slate-200 dark:border-slate-700">
                  Type{" "}
                  <span className="bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded font-mono text-sm">
                    "{organization.name}"
                  </span>{" "}
                  to confirm:
                </p>
                <Input
                  placeholder={`Type "${organization.name}" to confirm`}
                  value={deleteConfirmText}
                  onChange={(e) => setDeleteConfirmText(e.target.value)}
                  className="mt-2 font-mono"
                />
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              onClick={() => {
                setShowDeleteConfirm(false)
                setDeleteConfirmText("")
              }}
              className="hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={!isDeleteConfirmed}
              className="bg-red-600 hover:bg-red-700 text-white disabled:bg-slate-300 disabled:text-slate-500 disabled:cursor-not-allowed transition-all"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete Organization
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
