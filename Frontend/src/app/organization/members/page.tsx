"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import { useRouter } from "next/navigation"
import { organizationService } from "@/lib/api/organizationService"
import { CreditRequestService, CreditRequest } from "@/lib/api/creditRequestService"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useAuthStore } from "@/stores/authStore"
import { toast } from "sonner"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

import {
  Users,
  Mail,
  Shield,
  UserCheck,
  Clock,
  AlertCircle,
  Trash2,
  ArrowLeft,
  RefreshCw,
  Search,
  Download,
  MoreVertical,
  Loader2,
  AlertTriangle,
  CreditCard,
  Coins,
} from "lucide-react"
import { Input } from "@/components/ui/input"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Skeleton } from "@/components/ui/skeleton"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"

interface IndividualMember {
  user_id: string
  individual_tenant_id: string | null  // The tenant ID for credit allocation (null for pending invitations)
  user_email: string
  user_name: string
  role: string
  status: string
  joined_at: string
  credits_allocated: number
  credits_used: number
}

interface OrganizationMetrics {
  total_members?: number
  active_members?: number
  pending_members?: number
  total_credits_allocated?: number
  total_credits_used?: number
  // Backend returns invitations structure
  invitations?: {
    sent: number
    accepted: number
    pending_individual?: number  // Pending individual member invitations
    pending_team_leader?: number  // Pending team leader invitations
  }
  membership?: {
    total: number
    team_members: number
    individual_members: number
  }
}

interface TeamsData {
  teams: any[]
}

interface MembersData {
  members: IndividualMember[]
}

interface DeleteConfirmState {
  isOpen: boolean
  userId: string | null
  userName: string | null
  isDeleting: boolean
}

interface CreditAllocationState {
  isOpen: boolean
  member: IndividualMember | null
  amount: string
  isAllocating: boolean
}

export default function OrganizationMembersPage() {
  const router = useRouter()
  const { user, isAuthenticated } = useAuthStore()
  const currentWorkspaceTenantId = user?.tenant_id

  const organizationId = currentWorkspaceTenantId

  const [members, setMembers] = useState<IndividualMember[]>([])
  const [teamsCount, setTeamsCount] = useState<number>(0)
  const [metrics, setMetrics] = useState<OrganizationMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<DeleteConfirmState>({
    isOpen: false,
    userId: null,
    userName: null,
    isDeleting: false,
  })
  const [creditAllocation, setCreditAllocation] = useState<CreditAllocationState>({
    isOpen: false,
    member: null,
    amount: "",
    isAllocating: false,
  })
  
  // Credit requests state - track pending requests per member
  const [creditRequests, setCreditRequests] = useState<CreditRequest[]>([])
  const [creditRequestsLoading, setCreditRequestsLoading] = useState(false)

  const fetchMembersData = useCallback(async () => {
    if (!organizationId) {
      setError("No organization ID available. Please select a workspace.")
      setLoading(false)
      return
    }

    if (!isAuthenticated) {
      setError("Authentication required. Please sign in.")
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)

      if (process.env.NODE_ENV === "development") {
        console.log("🏢 Fetching members data for organization ID:", organizationId)
      }

      const [metricsRes, teamsRes, individualMembersRes] = await Promise.allSettled([
        organizationService.getOrganizationMetrics(organizationId),
        organizationService.getOrganizationTeams(organizationId),
        organizationService.getIndividualMembers(organizationId),
      ])

      // Metrics
      if (metricsRes.status === "fulfilled") {
        setMetrics(metricsRes.value as OrganizationMetrics)
      } else {
        if (process.env.NODE_ENV === "development") {
          console.warn("⚠️ Failed to load organization metrics:", metricsRes.reason)
        }
      }

      // Teams
      if (teamsRes.status === "fulfilled") {
        setTeamsCount((teamsRes.value as TeamsData).teams?.length || 0)
      } else {
        setTeamsCount(0)
        if (process.env.NODE_ENV === "development") {
          console.warn("⚠️ Failed to load organization teams:", teamsRes.reason)
        }
      }

      // Individual members (server may 500 intermittently). If it fails, continue with empty list
      if (individualMembersRes.status === "fulfilled") {
        const individualMembersData = individualMembersRes.value as MembersData
        const transformedMembers: IndividualMember[] = (individualMembersData.members || []).map((member: any) => ({
          user_id: member.user_id || member.id || "",
          individual_tenant_id: member.individual_tenant_id || "",  // Required for credit allocation
          user_email: member.email || member.user_email || "No email",
          user_name: member.name || member.user_name || "Unknown User",
          role: member.role || "member",
          status: member.status || "pending",
          joined_at: member.joined_at || member.created_at || new Date().toISOString(),
          credits_allocated: Number(member.credits_allocated) || 0,
          credits_used: Number(member.credits_used) || 0,
        }))
        setMembers(transformedMembers)
      } else {
        setMembers([])
        const reason = individualMembersRes.reason
        const msg = reason instanceof Error ? reason.message : String(reason)
        // Detect backend python error string and show a friendly warning instead of failing the page
        if (/(dictionary changed size during iteration|500|Internal Server Error)/i.test(msg)) {
          toast.warning("We couldn't load the individual members list right now. Metrics and teams loaded.")
        } else {
          toast.warning("Some member data couldn't be loaded. Showing what we have.")
        }
        if (process.env.NODE_ENV === "development") {
          console.warn("⚠️ Failed to load individual members:", reason)
        }
      }

      if (process.env.NODE_ENV === "development") {
        console.log("✅ Members data loaded successfully (with graceful fallbacks if needed)")
        if (metricsRes.status === "fulfilled") console.log("🔍 Fetched metrics:", metricsRes.value)
        if (teamsRes.status === "fulfilled") console.log("🔍 Teams count:", (teamsRes.value as TeamsData).teams?.length)
        if (individualMembersRes.status === "fulfilled") console.log("🔍 Individual members:", (individualMembersRes.value as MembersData).members)
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to load members data"

      if (process.env.NODE_ENV === "development") {
        console.error("❌ Error fetching members data:", error)
      }

      if (errorMessage.includes("401") || errorMessage.includes("Unauthorized")) {
        setError("Authentication expired. Please sign in again.")
        toast.error("Session expired. Please sign in again.")
        setTimeout(() => router.push("/signin"), 2000)
        return
      }

      if (errorMessage.includes("403") || errorMessage.includes("Forbidden")) {
        setError("Access denied. You may not have permission to view this organization.")
        toast.error("Access denied to organization data.")
        return
      }

      if (errorMessage.includes("404") || errorMessage.includes("Not Found")) {
        setError("Organization not found. It may have been deleted or you may not have access.")
        toast.error("Organization not found.")
        return
      }

      setError(errorMessage)
      toast.error("Failed to load members data")

      if (retryCount < 3 && (errorMessage.includes("Network") || errorMessage.includes("fetch"))) {
        const retryDelay = Math.pow(2, retryCount) * 1000
        setTimeout(() => {
          setRetryCount((prev) => prev + 1)
          fetchMembersData()
        }, retryDelay)
      }
    } finally {
      setLoading(false)
    }
  }, [organizationId, isAuthenticated, retryCount, router])

  // Fetch credit requests for the organization
  const fetchCreditRequests = useCallback(async () => {
    if (!organizationId) {
      console.log('🔍 DEBUG: No organizationId for credit requests fetch')
      return
    }
    
    console.log('🔍 DEBUG: Fetching credit requests for org:', organizationId)
    setCreditRequestsLoading(true)
    try {
      const response = await CreditRequestService.getOrganizationCreditRequests(organizationId)
      console.log('🔍 DEBUG: Credit requests response:', response)
      setCreditRequests(response.requests || [])
    } catch (err) {
      console.error("Failed to load credit requests:", err)
      setCreditRequests([])
    } finally {
      setCreditRequestsLoading(false)
    }
  }, [organizationId])

  // Helper to get credit request status for a specific member
  const getMemberCreditRequestStatus = useCallback((userId: string) => {
    const memberRequests = creditRequests.filter(r => r.user_id === userId)
    const pendingRequest = memberRequests.find(r => r.status === 'pending')
    const latestRequest = memberRequests.sort((a, b) => 
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )[0]
    
    return {
      hasPendingRequest: !!pendingRequest,
      pendingAmount: pendingRequest?.requested_amount,
      latestStatus: latestRequest?.status,
      totalRequests: memberRequests.length,
    }
  }, [creditRequests])

  useEffect(() => {
    if (!isAuthenticated) {
      if (process.env.NODE_ENV === "development") {
        console.log("🔒 User not authenticated, redirecting to signin")
      }
      router.push("/signin")
      return
    }

    if (!organizationId) {
      if (process.env.NODE_ENV === "development") {
        console.log("🏢 No organization ID available, redirecting to workspace selection")
      }
      router.push("/choose-workspace")
      return
    }

    fetchMembersData()
    fetchCreditRequests()
  }, [isAuthenticated, organizationId, fetchMembersData, fetchCreditRequests, router])

  const filteredMembers = useMemo(() => {
    return members.filter((member) => {
      const matchesSearch =
        member.user_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        member.user_email?.toLowerCase().includes(searchTerm.toLowerCase())
      const matchesStatus = statusFilter === "all" || member.status?.toLowerCase() === statusFilter
      return matchesSearch && matchesStatus
    })
  }, [members, searchTerm, statusFilter])

  const stats = useMemo(() => {
    if (metrics) {
      // Use pending_individual count if available, otherwise fall back to calculation
      const pendingInvitations = metrics.invitations?.pending_individual 
        ?? (metrics.invitations 
          ? Math.max(0, metrics.invitations.sent - metrics.invitations.accepted)
          : 0)
      
      return {
        totalMembers: metrics.membership?.total || metrics.total_members || members.length,
        activeMembers: metrics.membership?.individual_members || metrics.active_members || members.filter((m) => m.status?.toLowerCase() === "active").length,
        pendingMembers: pendingInvitations,  // Pending individual member invitations only
        totalCreditsAllocated:
          metrics.total_credits_allocated || members.reduce((sum, member) => sum + (member.credits_allocated || 0), 0),
        totalCreditsUsed:
          metrics.total_credits_used || members.reduce((sum, member) => sum + (member.credits_used || 0), 0),
      }
    }

    const totalMembers = members.length
    const activeMembers = members.filter((m) => m.status?.toLowerCase() === "active").length
    const pendingMembers = 0  // No pending data available without metrics
    const totalCreditsAllocated = members.reduce((sum, member) => sum + (member.credits_allocated || 0), 0)
    const totalCreditsUsed = members.reduce((sum, member) => sum + (member.credits_used || 0), 0)

    return {
      totalMembers,
      activeMembers,
      pendingMembers,
      totalCreditsAllocated,
      totalCreditsUsed,
    }
  }, [members, metrics])

  const creditsRemaining = stats.totalCreditsAllocated - stats.totalCreditsUsed

  const handleBack = useCallback(() => {
    router.push("/organization")
  }, [router])

  const handleRefresh = useCallback(() => {
    setRetryCount(0)
    fetchMembersData()
    toast.success("Members data refreshed")
  }, [fetchMembersData])

  const handleRetry = useCallback(() => {
    setRetryCount(0)
    fetchMembersData()
  }, [fetchMembersData])

  const handleBackToWorkspaces = useCallback(() => {
    router.push("/choose-workspace")
  }, [router])

  const handleDeleteMemberClick = useCallback((userId: string, userName: string) => {
    setDeleteConfirm({
      isOpen: true,
      userId,
      userName,
      isDeleting: false,
    })
  }, [])

  const confirmDeleteMember = useCallback(async () => {
    if (!organizationId || !deleteConfirm.userId) {
      toast.error("No organization selected")
      return
    }

    try {
      setDeleteConfirm((prev) => ({ ...prev, isDeleting: true }))
      const result = await organizationService.deleteOrganizationMember(organizationId, deleteConfirm.userId)

      if (result.success) {
        toast.success(
          `${deleteConfirm.userName} removed successfully. ${result.credits_returned || 0} credits returned.`,
        )
        fetchMembersData()
      } else {
        toast.error(result.message || "Failed to remove member")
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to delete member"
      if (process.env.NODE_ENV === "development") {
        console.error("Error deleting member:", error)
      }
      toast.error(errorMessage)
    } finally {
      setDeleteConfirm({
        isOpen: false,
        userId: null,
        userName: null,
        isDeleting: false,
      })
    }
  }, [organizationId, deleteConfirm.userId, deleteConfirm.userName, fetchMembersData])

  const handleResendInvite = useCallback(
    async (member: IndividualMember) => {
      if (!organizationId) {
        toast.error("No organization selected")
        return
      }

      // Extract invitation ID from user_id (format: "pending-{invitation_id}")
      const invitationId = member.user_id.replace("pending-", "")
      if (!invitationId || member.user_id === invitationId) {
        toast.error("Cannot resend invitation: Invalid invitation ID")
        return
      }

      try {
        setActionLoading(member.user_email)
        const result = await organizationService.resendInvitation(organizationId, invitationId)
        
        if (result.success) {
          toast.success(`Invitation resent to ${member.user_name}`)
          // Refresh the members list to update the status
          fetchMembersData()
        } else {
          toast.error(result.message || "Failed to resend invitation")
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Failed to resend invitation"
        if (process.env.NODE_ENV === "development") {
          console.error("Error resending invitation:", error)
        }
        toast.error(errorMessage)
      } finally {
        setActionLoading(null)
      }
    },
    [organizationId, fetchMembersData],
  )

  const handleAllocateCreditsClick = useCallback((member: IndividualMember) => {
    setCreditAllocation({
      isOpen: true,
      member,
      amount: "",
      isAllocating: false,
    })
  }, [])

  const handleAllocateCredits = useCallback(async () => {
    if (!organizationId || !creditAllocation.member) {
      toast.error("No organization or member selected")
      return
    }

    // Validate individual_tenant_id exists
    if (!creditAllocation.member.individual_tenant_id) {
      toast.error("Member does not have an individual workspace. Cannot allocate credits.")
      return
    }

    const amount = parseInt(creditAllocation.amount, 10)
    if (isNaN(amount) || amount < 1) {
      toast.error("Please enter a valid credit amount (minimum 1)")
      return
    }

    try {
      setCreditAllocation((prev) => ({ ...prev, isAllocating: true }))
      
      // Use individual_tenant_id for credit allocation (not user_id)
      // The backend expects the tenant_id from org_individuals table
      const result = await organizationService.allocateCreditsToMember(
        organizationId,
        creditAllocation.member.individual_tenant_id,
        "individual",
        amount
      )

      // Show success message with email notification status
      let successMessage = `Successfully allocated ${amount} credits to ${creditAllocation.member.user_name}`
      if (result.email_sent) {
        successMessage += ` - Notification sent to ${result.email_recipient}`
      }
      toast.success(successMessage)

      // Close modal and refresh data
      setCreditAllocation({
        isOpen: false,
        member: null,
        amount: "",
        isAllocating: false,
      })
      fetchMembersData()
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to allocate credits"
      if (process.env.NODE_ENV === "development") {
        console.error("Error allocating credits:", error)
      }
      toast.error(errorMessage)
    } finally {
      setCreditAllocation((prev) => ({ ...prev, isAllocating: false }))
    }
  }, [organizationId, creditAllocation.member, creditAllocation.amount, fetchMembersData])

  const getRoleColor = useCallback((role: string) => {
    switch (role?.toLowerCase()) {
      case "owner":
        return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200 border-purple-200 dark:border-purple-800"
      case "admin":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 border-blue-200 dark:border-blue-800"
      case "member":
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 border-green-200 dark:border-green-800"
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200 border-gray-200 dark:border-gray-800"
    }
  }, [])

  const getStatusColor = useCallback((status: string) => {
    switch (status?.toLowerCase()) {
      case "active":
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 border-green-200 dark:border-green-800"
      case "pending":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 border-yellow-200 dark:border-yellow-800"
      case "expired":
        return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200 border-red-200 dark:border-red-800"
      case "inactive":
        return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200 border-gray-200 dark:border-gray-800"
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200 border-gray-200 dark:border-gray-800"
    }
  }, [])

  const getCreditUsageColor = useCallback((used: number, allocated: number) => {
    if (allocated === 0) return "text-gray-600 dark:text-gray-400"
    const percentage = (used / allocated) * 100
    if (percentage >= 90) return "text-red-600 dark:text-red-400"
    if (percentage >= 75) return "text-yellow-600 dark:text-yellow-400"
    return "text-green-600 dark:text-green-400"
  }, [])

  const getCreditUsagePercentage = useCallback((used: number, allocated: number) => {
    if (allocated === 0) return 0
    return Math.round((used / allocated) * 100)
  }, [])

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Skeleton className="h-10 w-10 rounded-md" />
            <div className="space-y-2">
              <Skeleton className="h-8 w-64" />
              <Skeleton className="h-4 w-96" />
            </div>
          </div>
          <div className="flex space-x-3">
            <Skeleton className="h-10 w-24" />
            <Skeleton className="h-10 w-32" />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-lg" />
          ))}
        </div>

        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="space-y-2">
                <Skeleton className="h-6 w-48" />
                <Skeleton className="h-4 w-96" />
              </div>
              <div className="flex flex-col sm:flex-row gap-3">
                <Skeleton className="h-10 w-64" />
                <Skeleton className="h-10 w-32" />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center space-x-4 p-4 border rounded-lg">
                  <Skeleton className="h-12 w-12 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-3 w-24" />
                  </div>
                  <Skeleton className="h-6 w-16 rounded-full" />
                  <Skeleton className="h-6 w-20 rounded-full" />
                  <Skeleton className="h-6 w-24" />
                  <Skeleton className="h-6 w-6 rounded" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-2 space-y-2">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" size="icon" onClick={handleBack} aria-label="Go back">
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-brand-500 dark:text-white">Organization Members</h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">Manage team members across all teams</p>
          </div>
        </div>

        <Card className="border-red-200 dark:border-red-800">
          <CardContent className="pt-6">
            <div className="flex items-start space-x-4">
              <AlertCircle className="w-6 h-6 text-red-500 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <h3 className="font-semibold text-red-800 dark:text-red-200">Unable to Load Members</h3>
                <p className="text-red-700 dark:text-red-300 mt-1">{error}</p>
                <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-3 mt-4">
                  <Button onClick={handleRetry} className="flex items-center space-x-2">
                    <RefreshCw className="w-4 h-4" />
                    <span>Try Again</span>
                  </Button>
                  <Button variant="outline" onClick={handleBackToWorkspaces}>
                    Back to Workspaces
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-2 space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleBack}
            aria-label="Go back to organization"
            className="hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
          <h1 className="text-2xl font-bold text-brand-500 dark:text-white">Organization Members</h1>
          <p className="text-gray-600 dark:text-gray-400">
              Manage individual members and their credit allocations
            </p>
          </div>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <Button
            variant="outline"
            onClick={handleRefresh}
            className="flex items-center space-x-2 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800 bg-transparent"
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </Button>
          <Button
            onClick={() => router.push("/organization/invite-members")}
            className="flex items-center space-x-2"
          >
            <Mail className="w-4 h-4" />
            <span>Invite Members</span>
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
                <Users className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stats.totalMembers.toLocaleString()}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Total Members</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center">
                <UserCheck className="w-6 h-6 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stats.activeMembers.toLocaleString()}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Active Members</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-amber-100 dark:bg-amber-900 rounded-lg flex items-center justify-center">
                <Clock className="w-6 h-6 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stats.pendingMembers.toLocaleString()}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Pending</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center">
                <Shield className="w-6 h-6 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stats.totalCreditsAllocated.toLocaleString()}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Total Credits</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Individual Members List */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle className="flex items-center space-x-2 text-xl">
                <Shield className="w-5 h-5" />
                <span>Individual Members</span>
              </CardTitle>
              <CardDescription>Manage organization members who are not part of any team</CardDescription>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  placeholder="Search members..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 w-full sm:w-64 transition-all focus:ring-2"
                  aria-label="Search members"
                />
              </div>
              <div className="flex items-center space-x-2">
                <Label htmlFor="status-filter" className="text-sm whitespace-nowrap">
                  Status:
                </Label>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger id="status-filter" className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="expired">Expired</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredMembers.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                {searchTerm || statusFilter !== "all" ? "No matching members found" : "No individual members found"}
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
                {searchTerm || statusFilter !== "all"
                  ? "Try adjusting your search or filter criteria."
                  : "All organization members are currently part of teams. Individual members who join directly will appear here."}
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button
                  onClick={() => router.push("/organization/invite-members")}
                  className="flex items-center space-x-2"
                >
                  <Mail className="w-4 h-4" />
                  <span>Invite Members</span>
                </Button>
                {(searchTerm || statusFilter !== "all") && (
                  <Button
                    variant="outline"
                    onClick={() => {
                      setSearchTerm("")
                      setStatusFilter("all")
                    }}
                  >
                    Clear Filters
                  </Button>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Mobile View */}
              <div className="sm:hidden space-y-4">
                {filteredMembers.map((member) => (
                  <Card key={member.user_id} className="p-4 hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-gray-900 dark:text-white truncate">{member.user_name}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400 truncate">{member.user_email}</p>
                      </div>
                      {actionLoading === member.user_id ? (
                        <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                      ) : (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="hover:bg-gray-100 dark:hover:bg-gray-700">
                              <MoreVertical className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            {member.status?.toLowerCase() !== "pending" && member.status?.toLowerCase() !== "expired" && (
                              <DropdownMenuItem
                                onClick={() => handleAllocateCreditsClick(member)}
                                className="text-brand-600 focus:text-brand-600"
                              >
                                <Coins className="w-3 h-3 mr-2" />
                                Allocate Credits
                              </DropdownMenuItem>
                            )}
                            {(member.status?.toLowerCase() === "pending" || member.status?.toLowerCase() === "expired") && (
                              <DropdownMenuItem
                                onClick={() => handleResendInvite(member)}
                                disabled={actionLoading === member.user_email}
                              >
                                {actionLoading === member.user_email ? (
                                  <Loader2 className="w-3 h-3 animate-spin mr-2" />
                                ) : null}
                                Resend Invite
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => handleDeleteMemberClick(member.user_id, member.user_name)}
                              className="text-red-600 focus:text-red-600 focus:bg-red-50 dark:focus:bg-red-900/20"
                            >
                              <Trash2 className="w-3 h-3 mr-2" />
                              Remove Member
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Role</span>
                        <Badge variant="secondary" className={`mt-1 ${getRoleColor(member.role)}`}>
                          {member.role}
                        </Badge>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Status</span>
                        <Badge variant="secondary" className={`mt-1 ${getStatusColor(member.status)}`}>
                          {member.status}
                        </Badge>
                      </div>
                      <div className="col-span-2">
                        <span className="text-gray-500 dark:text-gray-400">Credits</span>
                        <div className="flex items-center space-x-2 mt-1">
                          <p
                            className={`font-medium ${getCreditUsageColor(member.credits_used, member.credits_allocated)}`}
                          >
                            {member.credits_used} / {member.credits_allocated}
                          </p>
                          <span className="text-xs text-gray-500">
                            ({getCreditUsagePercentage(member.credits_used, member.credits_allocated)}%)
                          </span>
                        </div>
                        {member.credits_allocated > 0 && (
                          <div className="w-full bg-gray-200 rounded-full h-1.5 mt-1 dark:bg-gray-700">
                            <div
                              className={`h-1.5 rounded-full transition-all duration-300 ${
                                getCreditUsagePercentage(member.credits_used, member.credits_allocated) >= 90
                                  ? "bg-red-500"
                                  : getCreditUsagePercentage(member.credits_used, member.credits_allocated) >= 75
                                    ? "bg-yellow-500"
                                    : "bg-green-500"
                              }`}
                              style={{
                                width: `${Math.min(getCreditUsagePercentage(member.credits_used, member.credits_allocated), 100)}%`,
                              }}
                            />
                          </div>
                        )}
                      </div>
                      <div className="col-span-2">
                        <span className="text-gray-500 dark:text-gray-400">Joined</span>
                        <p className="text-gray-900 dark:text-white mt-1">
                          {member.joined_at ? new Date(member.joined_at).toLocaleDateString() : "N/A"}
                        </p>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>

              {/* Desktop View */}
              <div className="hidden sm:block overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-700">
                      <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Member</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Role</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Credits</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Credit Request</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Status</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Joined</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredMembers.map((member) => (
                      <tr
                        key={member.user_id}
                        className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                      >
                        <td className="py-4 px-4">
                          <div>
                            <p className="font-medium text-gray-900 dark:text-white">{member.user_name}</p>
                            <p className="text-sm text-gray-500 dark:text-gray-400">{member.user_email}</p>
                          </div>
                        </td>
                        <td className="py-4 px-4">
                          <Badge variant="secondary" className={getRoleColor(member.role)}>
                            {member.role}
                          </Badge>
                        </td>
                        <td className="py-4 px-4">
                          <div className="space-y-1">
                            <div className="flex items-center space-x-2 text-sm">
                              <p
                                className={`font-medium ${getCreditUsageColor(member.credits_used, member.credits_allocated)}`}
                              >
                                {member.credits_used} / {member.credits_allocated}
                              </p>
                              <span className="text-xs text-gray-500">
                                ({getCreditUsagePercentage(member.credits_used, member.credits_allocated)}%)
                              </span>
                            </div>
                            {member.credits_allocated > 0 && (
                              <div className="w-24 bg-gray-200 rounded-full h-1.5 mt-1 dark:bg-gray-700">
                                <div
                                  className={`h-1.5 rounded-full transition-all duration-300 ${
                                    getCreditUsagePercentage(member.credits_used, member.credits_allocated) >= 90
                                      ? "bg-red-500"
                                      : getCreditUsagePercentage(member.credits_used, member.credits_allocated) >= 75
                                        ? "bg-yellow-500"
                                        : "bg-green-500"
                                  }`}
                                  style={{
                                    width: `${Math.min(getCreditUsagePercentage(member.credits_used, member.credits_allocated), 100)}%`,
                                  }}
                                />
                              </div>
                            )}
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              {member.credits_allocated - member.credits_used} remaining
                            </p>
                          </div>
                        </td>
                        <td className="py-4 px-4">
                          {(() => {
                            const reqStatus = getMemberCreditRequestStatus(member.user_id)
                            if (reqStatus.hasPendingRequest) {
                              return (
                                <div className="flex items-center space-x-2">
                                  <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400 border border-yellow-200 dark:border-yellow-800">
                                    <Clock className="w-3 h-3 mr-1" />
                                    Pending
                                  </Badge>
                                  <span className="text-xs text-gray-500">
                                    {reqStatus.pendingAmount?.toLocaleString()} credits
                                  </span>
                                </div>
                              )
                            } else if (reqStatus.totalRequests > 0) {
                              return (
                                <Badge variant="outline" className="text-gray-500 dark:text-gray-400">
                                  {reqStatus.latestStatus === 'approved' ? '✓ Last approved' : 
                                   reqStatus.latestStatus === 'rejected' ? '✗ Last rejected' : 
                                   'No pending'}
                                </Badge>
                              )
                            }
                            return (
                              <span className="text-xs text-gray-400 dark:text-gray-500">
                                No requests
                              </span>
                            )
                          })()}
                        </td>
                        <td className="py-4 px-4">
                          <Badge variant="secondary" className={getStatusColor(member.status)}>
                            {member.status}
                          </Badge>
                        </td>
                        <td className="py-4 px-4">
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            {member.joined_at ? new Date(member.joined_at).toLocaleDateString() : "N/A"}
                          </p>
                        </td>
                        <td className="py-4 px-4">
                          {actionLoading === member.user_id ? (
                            <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                          ) : (
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                >
                                  <MoreVertical className="w-4 h-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                {member.status?.toLowerCase() !== "pending" && member.status?.toLowerCase() !== "expired" && (
                                  <DropdownMenuItem
                                    onClick={() => handleAllocateCreditsClick(member)}
                                    className="text-brand-600 focus:text-brand-600"
                                  >
                                    <Coins className="w-3 h-3 mr-2" />
                                    Allocate Credits
                                  </DropdownMenuItem>
                                )}
                                {(member.status?.toLowerCase() === "pending" || member.status?.toLowerCase() === "expired") && (
                                  <>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem
                                      onClick={() => handleResendInvite(member)}
                                      disabled={actionLoading === member.user_email}
                                    >
                                      {actionLoading === member.user_email ? (
                                        <Loader2 className="w-3 h-3 animate-spin mr-2" />
                                      ) : null}
                                      Resend Invite
                                    </DropdownMenuItem>
                                  </>
                                )}
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                  onClick={() => handleDeleteMemberClick(member.user_id, member.user_name)}
                                  className="text-red-600 focus:text-red-600 focus:bg-red-50 dark:focus:bg-red-900/20"
                                >
                                  <Trash2 className="w-3 h-3 mr-2" />
                                  Remove Member
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Summary */}
              <div className="flex flex-col sm:flex-row justify-between items-center pt-4 border-t border-gray-200 dark:border-gray-700 gap-4">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Showing {filteredMembers.length} of {members.length} members
                </p>
                <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
                  <span>Total Credits: {stats.totalCreditsAllocated.toLocaleString()}</span>
                  <span>•</span>
                  <span>Used: {stats.totalCreditsUsed.toLocaleString()}</span>
                  <span>•</span>
                  <span>Available: {creditsRemaining.toLocaleString()}</span>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialogs */}
      <Dialog
        open={deleteConfirm.isOpen}
        onOpenChange={(open) => {
          if (!open) {
            setDeleteConfirm({
              isOpen: false,
              userId: null,
              userName: null,
              isDeleting: false,
            })
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
              </div>
              <DialogTitle className="text-lg">Remove Member</DialogTitle>
            </div>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <DialogDescription className="text-base">
              Are you sure you want to remove{" "}
              <span className="font-semibold text-gray-900 dark:text-white">{deleteConfirm.userName}</span> from this
              organization?
            </DialogDescription>
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-900/50 rounded-lg p-3">
              <p className="text-sm text-amber-800 dark:text-amber-200">
                ⚠️ This action will return any allocated credits and allow them to be re-invited.
              </p>
            </div>
          </div>

          <DialogFooter className="flex gap-3 pt-4">
            <Button
              variant="outline"
              onClick={() => {
                setDeleteConfirm({
                  isOpen: false,
                  userId: null,
                  userName: null,
                  isDeleting: false,
                })
              }}
              disabled={deleteConfirm.isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDeleteMember}
              disabled={deleteConfirm.isDeleting}
              className="flex items-center space-x-2"
            >
              {deleteConfirm.isDeleting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Removing...</span>
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4" />
                  <span>Remove Member</span>
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Credit Allocation Dialog */}
      <Dialog
        open={creditAllocation.isOpen}
        onOpenChange={(open) => {
          if (!open) {
            setCreditAllocation({
              isOpen: false,
              member: null,
              amount: "",
              isAllocating: false,
            })
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-brand-100 dark:bg-brand-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                <Coins className="w-5 h-5 text-brand-600 dark:text-brand-400" />
              </div>
              <DialogTitle className="text-lg">Allocate Credits</DialogTitle>
            </div>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <DialogDescription className="text-base">
              Allocate credits from your organization pool to{" "}
              <span className="font-semibold text-gray-900 dark:text-white">
                {creditAllocation.member?.user_name}
              </span>
            </DialogDescription>

            {creditAllocation.member && (
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Current Credits:</span>
                  <span className="font-medium">
                    {creditAllocation.member.credits_allocated - creditAllocation.member.credits_used} available
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Total Allocated:</span>
                  <span className="font-medium">{creditAllocation.member.credits_allocated}</span>
                </div>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="credit-amount">Credits to Allocate</Label>
              <Input
                id="credit-amount"
                type="number"
                min="1"
                placeholder="Enter amount"
                value={creditAllocation.amount}
                onChange={(e) =>
                  setCreditAllocation((prev) => ({ ...prev, amount: e.target.value }))
                }
                disabled={creditAllocation.isAllocating}
              />
              <p className="text-xs text-gray-500">
                Credits will be deducted from your organization's pool
              </p>
            </div>
          </div>

          <DialogFooter className="flex gap-3 pt-4">
            <Button
              variant="outline"
              onClick={() => {
                setCreditAllocation({
                  isOpen: false,
                  member: null,
                  amount: "",
                  isAllocating: false,
                })
              }}
              disabled={creditAllocation.isAllocating}
            >
              Cancel
            </Button>
            <Button
              onClick={handleAllocateCredits}
              disabled={creditAllocation.isAllocating || !creditAllocation.amount}
              className="flex items-center space-x-2 bg-brand-600 hover:bg-brand-700"
            >
              {creditAllocation.isAllocating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Allocating...</span>
                </>
              ) : (
                <>
                  <Coins className="w-4 h-4" />
                  <span>Allocate Credits</span>
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
