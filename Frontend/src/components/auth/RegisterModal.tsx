import { useId, useState, useRef, useEffect } from "react"
import { toast } from "react-hot-toast"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import Image from "next/image"
import { Eye, EyeOff } from 'lucide-react'
import { useAuthStore } from "@/stores/authStore"
import { authService } from "@/services/authService"

interface RegisterModalProps {
  isOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  onSuccess?: () => void;
  onClose?: () => void;
  vbInvitationToken?: string | null;
}

interface SignUpResponse {
  message: string;
  access_token: string;
  user: {
    id: string;
    email: string;
    tenant_id: string;
    tenant_type: string;
    full_name: string;
    roles: string[];
  };
}

export default function RegisterModal({ isOpen, onOpenChange, onSuccess, onClose, vbInvitationToken }: RegisterModalProps) {
  const id = useId()
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  // Get auth store action - ONLY setToken, nothing else
  const setToken = useAuthStore((state) => state.setToken)

  // Refs for cleanup
  const abortControllerRef = useRef<AbortController | null>(null)
  const isMountedRef = useRef(true)

  // Track mount status
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
        abortControllerRef.current = null
      }
    }
  }, [])

  // Form state
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
    confirmPassword: ''
  })

  // Input sanitization
  const sanitizeInput = (value: string, maxLength: number): string => {
    return value
      .replace(/<[^>]*>/g, '') // Remove HTML tags
      .slice(0, maxLength)
  }

  // Handle input changes
  const handleInputChange = (field: keyof typeof formData, value: string) => {
    let sanitized = value

    switch (field) {
      case 'firstName':
      case 'lastName':
        sanitized = sanitizeInput(value, 50)
        break
      case 'email':
        sanitized = sanitizeInput(value, 254)
        break
      case 'password':
      case 'confirmPassword':
        sanitized = sanitizeInput(value, 128)
        break
    }

    setFormData(prev => ({ ...prev, [field]: sanitized }))
  }

  // Validate form
  const validateForm = (): string | null => {
    if (!formData.firstName || !formData.lastName) {
      return 'Please enter your first and last name'
    }

    if (!formData.email) {
      return 'Please enter your email address'
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(formData.email)) {
      return 'Please enter a valid email address'
    }

    if (!formData.password) {
      return 'Please enter a password'
    }

    if (formData.password.length < 8) {
      return 'Password must be at least 8 characters long'
    }

    const hasUpperCase = /[A-Z]/.test(formData.password)
    const hasLowerCase = /[a-z]/.test(formData.password)
    const hasNumber = /[0-9]/.test(formData.password)
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(formData.password)

    const missing = []
    if (!hasUpperCase) missing.push('uppercase letter')
    if (!hasLowerCase) missing.push('lowercase letter')
    if (!hasNumber) missing.push('number')
    if (!hasSpecialChar) missing.push('special character')

    if (missing.length > 0) {
      return `Password must contain: ${missing.join(', ')}`
    }

    if (formData.password !== formData.confirmPassword) {
      return 'Passwords do not match'
    }

    return null
  }

  // Handle form submission - SIMPLIFIED
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validate form
    const validationError = validateForm()
    if (validationError) {
      toast.error(validationError)
      return
    }

    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    // Create new AbortController
    abortControllerRef.current = new AbortController()

    setIsLoading(true)

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL
      const full_name = `${formData.firstName} ${formData.lastName}`.trim()

      if (process.env.NODE_ENV === 'development') {
        console.log('📝 Registering user:', { email: formData.email, full_name })
      }

      const response = await fetch(`${API_URL}/api/v2/auth/signup/direct`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          full_name: full_name,
        }),
        signal: abortControllerRef.current.signal,
      })

      const data: SignUpResponse = await response.json()

      if (!response.ok) {
        throw new Error(data.message || 'Sign up failed')
      }

      // Check if component is still mounted
      if (!isMountedRef.current) {
        if (process.env.NODE_ENV === 'development') {
          console.log('⚠️ Component unmounted, skipping state updates')
        }
        return
      }

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Registration successful, updating token only')
      }

      console.log("dataaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", data)

      // ONLY update the access token - parent will handle the rest
      setToken(data.access_token)

      toast.success('Account created successfully!')

      // Login via authService - this updates the global auth store
      // IMPORTANT: Wait for login to complete before closing modal
      await authService.login({
        email: formData.email,
        password: formData.password,
      });

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Auto-login completed successfully')
      }

      // Reset form
      setFormData({
        firstName: '',
        lastName: '',
        email: '',
        password: '',
        confirmPassword: ''
      })

      // Close modal
      if (onOpenChange) {
        onOpenChange(false)
      }

      // Call success callback - parent handles everything else
      if (onSuccess) {
        onSuccess()
      }

      // Call close callback
      if (onClose) {
        onClose()
      }

    } catch (error: any) {
      // Don't show errors if request was aborted or component unmounted
      if (error.name === 'AbortError' || !isMountedRef.current) {
        return
      }

      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Sign up error:', error.message)
      }

      const errorMessage = error instanceof Error ? error.message : 'Failed to create account. Please try again.'
      toast.error(errorMessage)
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false)
      }
      abortControllerRef.current = null
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">Don't have an account?</span>
        <DialogTrigger asChild>
          <div className="text-sm underline hover:no-underline cursor-pointer text-brand-500 font-bold">Sign up</div>
        </DialogTrigger>
      </div>
      <DialogContent 
        onInteractOutside={(e) => {
          // Prevent closing when clicking outside during loading or when form has data
          if (isLoading || formData.email || formData.firstName || formData.lastName) {
            e.preventDefault()
          }
        }}
        onEscapeKeyDown={(e) => {
          // Prevent closing on Escape key during loading
          if (isLoading) {
            e.preventDefault()
          }
        }}
      >
        <div className="flex flex-col items-center gap-2">
          <div
            className="flex size-11 shrink-0 items-center justify-center rounded-full border"
            aria-hidden="true"
          >
            <Image src="/images/logo/yuba-logo-icon-colored.png" alt="Yuba" width={80} height={80} priority />
          </div>
          <DialogHeader>
            <DialogTitle className="sm:text-center text-brand-500">
              Sign up to Yuba
            </DialogTitle>
            <DialogDescription className="sm:text-center">
              We just need a few details to get you started.
            </DialogDescription>
          </DialogHeader>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className=":not-first:mt-2">
                <Label htmlFor={`${id}-first-name`} className="mb-1">First name</Label>
                <Input
                  id={`${id}-first-name`}
                  placeholder="Jane"
                  type="text"
                  required
                  value={formData.firstName}
                  onChange={(e) => handleInputChange('firstName', e.target.value)}
                  disabled={isLoading}
                />
              </div>
              <div className=":not-first:mt-2">
                <Label htmlFor={`${id}-last-name`} className="mb-1">Last name</Label>
                <Input
                  id={`${id}-last-name`}
                  placeholder="Doe"
                  type="text"
                  required
                  value={formData.lastName}
                  onChange={(e) => handleInputChange('lastName', e.target.value)}
                  disabled={isLoading}
                />
              </div>
            </div>
            <div className=":not-first:mt-2">
              <Label htmlFor={`${id}-email`} className="mb-1">Email</Label>
              <Input
                id={`${id}-email`}
                placeholder="hi@yourcompany.com"
                type="email"
                required
                value={formData.email}
                onChange={(e) => handleInputChange('email', e.target.value)}
                disabled={isLoading}
              />
            </div>
            <div className=":not-first:mt-2">
              <Label htmlFor={`${id}-password`} className="mb-1">Password</Label>
              <div className="relative">
                <Input
                  id={`${id}-password`}
                  placeholder="Enter your password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  className="pr-10"
                  value={formData.password}
                  onChange={(e) => handleInputChange('password', e.target.value)}
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute inset-y-0 right-2 flex items-center text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  disabled={isLoading}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Must be 8+ characters with uppercase, lowercase, number, and special character
              </p>
            </div>
            <div className=":not-first:mt-2">
              <Label htmlFor={`${id}-confirm-password`} className="mb-1">Confirm password</Label>
              <div className="relative">
                <Input
                  id={`${id}-confirm-password`}
                  placeholder="Re-enter your password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  required
                  className="pr-10"
                  value={formData.confirmPassword}
                  onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword((prev) => !prev)}
                  className="absolute inset-y-0 right-2 flex items-center text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                  aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                  disabled={isLoading}
                >
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </div>
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? 'Creating account...' : 'Sign up'}
          </Button>
        </form>

        <p className="text-center text-xs text-muted-foreground">
          By signing up you agree to our{" "}
          <a className="underline hover:no-underline" href="#">
            Terms
          </a>
          .
        </p>
      </DialogContent>
    </Dialog>
  )
}
