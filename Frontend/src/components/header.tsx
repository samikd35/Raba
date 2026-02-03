"use client"
import Link from "next/link"
import Image from 'next/image'
import { Menu, X, User, ArrowRight, Check, ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useState, useEffect, useRef, useCallback } from "react"
import { 
  useUser, 
  useIsAuthenticated, 
  useIsLoading, 
  useIsInitialized,
  useUserDisplayName,
  useLogout,
  useComputedRole
} from "@/stores/authStore"
import { authService } from "@/services/authService"
import { useRouter, usePathname } from "next/navigation"

const menuItems = [
  { 
    name: "Solutions", 
    href: "#how-it-works",
    hasDropdown: true,
    dropdownItems: [
      { name: "Founders", href: "#how-it-works" },
      { name: "ESOs", href: "#eso" },
    ]
  },
  { name: "Pricing", href: "/pricing" },
  { name: "Testimonials", href: "#testimonials" },
  { name: "FAQs", href: "#faqs" },
]

interface HeroHeaderProps {
  darkMode?: boolean;
}

export const HeroHeader = ({ darkMode = false }: HeroHeaderProps) => {
  const [menuState, setMenuState] = useState(false)
  const [isScrolled, setIsScrolled] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [activeNavLink, setActiveNavLink] = useState<string | null>(null)
  const [hoveredNavLink, setHoveredNavLink] = useState<string | null>(null)
  const [solutionsDropdownOpen, setSolutionsDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const dropdownCloseTimerRef = useRef<NodeJS.Timeout | null>(null)
  const [signupLoading, setSignupLoading] = useState(false)
  const [signinLoading, setSigninLoading] = useState(false)
  const [dashboardLoading, setDashboardLoading] = useState(false)
  
  const user = useUser()
  const isAuthenticated = useIsAuthenticated()
  const authLoading = useIsLoading()
  const isInitialized = useIsInitialized()
  const userDisplayName = useUserDisplayName()
  const logout = useLogout()
  const computedRole = useComputedRole()
  const router = useRouter()
  const pathname = usePathname()

  const initializedRef = useRef(false)

  useEffect(() => {
    if (initializedRef.current || isInitialized) {
      return
    }

    const initializeAuth = async () => {
      try {
        if (process.env.NODE_ENV === 'development') {
          console.log('Header: Initializing auth via authService...')
        }
        
        initializedRef.current = true
        await authService.initialize()
        
        if (process.env.NODE_ENV === 'development') {
          console.log('Header: Auth initialized successfully')
        }
      } catch (error) {
        if (process.env.NODE_ENV === 'development') {
          console.error('Header: Auth initialization failed:', error)
        }
        initializedRef.current = false
      }
    }
    
    initializeAuth()
  }, [isInitialized])

  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('Header Auth State:', {
        isInitialized,
        authLoading,
        isAuthenticated,
        hasUser: !!user,
        userDisplayName,
        userRole: computedRole,
        userRoles: user?.roles
      })
    }
  }, [isInitialized, authLoading, isAuthenticated, user, userDisplayName, computedRole])

  useEffect(() => {
    let ticking = false
    
    const handleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const scrollTop = window.scrollY
          setIsScrolled(scrollTop > 0)
          ticking = false
        })
        ticking = true
      }
    }

    if (typeof window !== 'undefined') {
      window.addEventListener("scroll", handleScroll, { passive: true })
      return () => {
        window.removeEventListener("scroll", handleScroll)
      }
    }
  }, [])

  useEffect(() => {
    if (pathname === '/' && typeof window !== 'undefined') {
      const hash = window.location.hash
      if (hash) {
        // Small delay to ensure DOM is ready after navigation
        setTimeout(() => {
          const element = document.getElementById(hash.substring(1))
          if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'start' })
          }
        }, 100)
      }
    }
  }, [pathname])

  const handleSignOut = useCallback(async () => {
    try {
      setIsLoggingOut(true)
      await authService.logout()
      setMenuState(false)
      router.push('/')
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Logout error:', error)
      }
    } finally {
      setIsLoggingOut(false)
    }
  }, [router])

  const handleMenuItemClick = useCallback((e: React.MouseEvent, href?: string) => {
    if (!href) {
      setMenuState(false)
      return
    }

    setActiveNavLink(href)
    setTimeout(() => setActiveNavLink(null), 600)
    setMenuState(false)

    // Check if it's a section link (starts with #)
    if (href.startsWith('#')) {
      e.preventDefault()
      const sectionId = href.substring(1)
      
      // If on landing page, smooth scroll to section
      if (pathname === '/') {
        const element = document.getElementById(sectionId)
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      } else {
        // If on another page, navigate to landing page with hash
        router.push(`/${href}`)
      }
    }
  }, [pathname, router])

  const handleNavLinkHover = useCallback((href: string | null) => {
    setHoveredNavLink(href)
  }, [])

  const handleSignUpClick = useCallback(async (e: React.MouseEvent) => {
    e.preventDefault()
    
    setSigninLoading(false)
    setSignupLoading(true)
    
    await new Promise(resolve => setTimeout(resolve, 800))
    
    router.push('/signup')
    
    setMenuState(false)
    
    setTimeout(() => setSignupLoading(false), 1000)
  }, [router])

  const handleSignInClick = useCallback(async (e: React.MouseEvent) => {
    e.preventDefault()
    
    setSignupLoading(false)
    setSigninLoading(true)
    
    await new Promise(resolve => setTimeout(resolve, 600))
    
    router.push('/signin')
    
    setMenuState(false)
    
    setTimeout(() => setSigninLoading(false), 1000)
  }, [router])

  const handleDashboardClick = useCallback(async (e: React.MouseEvent, href: string) => {
    e.preventDefault()
    setSigninLoading(false)
    setSignupLoading(false)
    setDashboardLoading(true)

    setMenuState(false)

    await new Promise((resolve) => setTimeout(resolve, 500))

    router.push(href)

    setTimeout(() => setDashboardLoading(false), 1000)
  }, [router])

  const getDashboardRoute = useCallback(() => {
    if (!user || !isAuthenticated) return '/signin'
    
    const roles = user.roles || []
    
    if (roles.includes('super_admin') || roles.includes('admin')) {
      return '/admin'
    } else {
      return '/choose-workspace'
    }
  }, [user, isAuthenticated])

  const AnimatedNavLink = ({ 
    item, 
    isMobile = false 
  }: { 
    item: typeof menuItems[0]; 
    isMobile?: boolean 
  }) => {
    const isActive = activeNavLink === item.href
    const isHovered = hoveredNavLink === item.href

    // Handle dropdown for Solutions
    if (item.hasDropdown && item.dropdownItems) {
      const handleDropdownMouseEnter = () => {
        if (isMobile) return
        
        // Cancel any pending close timer
        if (dropdownCloseTimerRef.current) {
          clearTimeout(dropdownCloseTimerRef.current)
          dropdownCloseTimerRef.current = null
        }
        
        setSolutionsDropdownOpen(true)
      }

      const handleDropdownMouseLeave = () => {
        if (isMobile) return
        
        // Set a 2-second delay before closing
        dropdownCloseTimerRef.current = setTimeout(() => {
          setSolutionsDropdownOpen(false)
          dropdownCloseTimerRef.current = null
        }, 500)
      }

      return (
        <li className="relative">
          <div
            ref={!isMobile ? dropdownRef : undefined}
            onMouseEnter={handleDropdownMouseEnter}
            onMouseLeave={handleDropdownMouseLeave}
            className="relative"
          >
            <button
              onClick={() => isMobile && setSolutionsDropdownOpen(!solutionsDropdownOpen)}
              className={`
                relative flex items-center duration-200 transition-all cursor-pointer
                ${isMobile 
                  ? darkMode
                    ? "text-gray-300 hover:text-brand-400 py-2 px-4 rounded-lg hover:bg-slate-700 w-full justify-between"
                    : "text-gray-700 hover:text-brand-600 py-2 px-4 rounded-lg hover:bg-gray-100 w-full justify-between" 
                  : darkMode
                    ? "text-gray-300 hover:text-brand-400"
                    : "text-gray-700 hover:text-brand-600"
                }
                ${isActive ? 'scale-95 opacity-70' : 'scale-100 opacity-100'}
              `}
            >
              <span className="relative flex items-center">
                {item.name}
                <ChevronDown 
                  className={`
                    ml-1 h-3 w-3 transition-all duration-200 transform
                    ${solutionsDropdownOpen ? 'rotate-180' : 'rotate-0'}
                  `} 
                />
              </span>
            </button>

            {/* Dropdown Menu */}
            <div 
              className={`
                ${isMobile 
                  ? 'pl-4 mt-1 space-y-1' 
                  : darkMode
                    ? 'absolute top-full left-0 mt-1 min-w-[140px] bg-slate-800 rounded-lg shadow-[0_4px_12px_rgba(0,0,0,0.3)] border border-slate-600 py-1.5 z-50'
                    : 'absolute top-full left-0 mt-1 min-w-[140px] bg-white rounded-lg shadow-[0_4px_12px_rgba(0,0,0,0.08)] border border-gray-100/80 py-1.5 z-50'
                }
                transition-all duration-150 origin-top
                ${solutionsDropdownOpen 
                  ? 'opacity-100 scale-100 visible' 
                  : 'opacity-0 scale-95 invisible pointer-events-none'
                }
              `}
            >
              {item.dropdownItems.map((dropdownItem, idx) => (
                <Link
                  key={idx}
                  href={dropdownItem.href}
                  onClick={(e) => {
                    handleMenuItemClick(e, dropdownItem.href)
                    setSolutionsDropdownOpen(false)
                  }}
                  className={`
                    group block transition-all duration-150
                    ${isMobile 
                      ? darkMode
                        ? 'text-gray-400 hover:text-brand-400 py-2 px-4 rounded-lg hover:bg-slate-700 text-sm'
                        : 'text-gray-600 hover:text-brand-600 py-2 px-4 rounded-lg hover:bg-gray-50 text-sm' 
                      : darkMode
                        ? 'px-3.5 py-2 text-sm text-gray-300 hover:text-brand-400 hover:bg-slate-700/50 mx-1 rounded-md'
                        : 'px-3.5 py-2 text-sm text-gray-700 hover:text-brand-600 hover:bg-brand-50/50 mx-1 rounded-md'
                    }
                  `}
                >
                  <span className="flex items-center justify-between">
                    <span>{dropdownItem.name}</span>
                    <ArrowRight className="h-3.5 w-3.5 opacity-0 -translate-x-1 transition-all duration-150 group-hover:opacity-100 group-hover:translate-x-0" />
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </li>
      )
    }

    return (
      <li>
        <Link
          href={item.href}
          onClick={(e) => handleMenuItemClick(e, item.href)}
          onMouseEnter={() => handleNavLinkHover(item.href)}
          onMouseLeave={() => handleNavLinkHover(null)}
          className={`
            relative block duration-300 transition-all group
            ${isMobile 
              ? darkMode
                ? "text-gray-300 hover:text-brand-400 py-2 px-4 rounded-lg hover:bg-slate-700"
                : "text-gray-700 hover:text-brand-600 py-2 px-4 rounded-lg hover:bg-gray-100" 
              : darkMode
                ? "text-gray-300 hover:text-brand-400"
                : "text-gray-700 hover:text-brand-600"
            }
            ${isActive ? 'scale-95 opacity-70' : 'scale-100 opacity-100'}
          `}
        >
          <span className="relative flex items-center">
            {item.name}
            <ArrowRight 
              className={`
                ml-1 h-3 w-3 transition-all duration-300 transform
                ${isHovered ? 'translate-x-1 opacity-100 scale-100' : 'translate-x-0 opacity-0 scale-50'}
              `} 
            />
          </span>
          
          <div 
            className={`
              absolute bottom-0 left-1/2 transform -translate-x-1/2
              w-1.5 h-1.5 bg-brand-500 rounded-full transition-all duration-300
              ${isActive ? 'scale-100 opacity-100' : 'scale-0 opacity-0'}
              ${isMobile ? 'top-1/2 -translate-y-1/2 left-2' : 'bottom-[-8px]'}
            `} 
          />
          
          {!isMobile && (
            <div 
              className={`
                absolute bottom-0 left-0 w-0 h-0.5 bg-brand-500 
                transition-all duration-300 group-hover:w-full
                ${isActive ? 'w-full' : ''}
              `} 
            />
          )}
        </Link>
      </li>
    )
  }

  const SignUpButton = () => (
    <button 
      type="button" 
      className="px-6 w-full sm:w-auto relative overflow-hidden group transition-all duration-300 hover:scale-105 active:scale-95 border-brand-500 text-brand-600 hover:bg-brand-50 hover:text-brand-700 hover:border-brand-600 border rounded-md font-medium py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
      onClick={handleSignUpClick}
      disabled={signupLoading || signinLoading}
    >
      <div className="relative flex items-center justify-center">
        <div className={`
          flex items-center transition-all duration-300
          ${signupLoading ? 'opacity-0 -translate-y-2' : 'opacity-100 translate-y-0'}
        `}>
          <span className="flex items-center transition-transform duration-200 group-hover:translate-x-0.5">
            Sign Up
            <ArrowRight className="ml-1 h-3 w-3 transition-all duration-300 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0" />
          </span>
        </div>

        <div className={`
          absolute flex items-center justify-center transition-all duration-300
          ${signupLoading ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}
        `}>
          <div className="flex items-center space-x-2">
            <span className="text-xs whitespace-nowrap">Creating Account...</span>
          </div>
        </div>
      </div>
      
      <div className={`
        absolute inset-0 -translate-x-full transition-transform duration-1000 bg-gradient-to-r from-transparent via-brand-50/50 to-transparent
        ${!signupLoading ? 'group-hover:translate-x-full' : ''}
      `} />
      
      {signupLoading && (
        <div className="absolute bottom-0 left-0 w-0 h-0.5 bg-brand-500 animate-progress rounded-full" />
      )}
      
      <div className={`
        absolute inset-0 rounded-md border-2 border-transparent transition-all duration-300
        ${signupLoading ? 'border-brand-300 animate-pulse' : ''}
      `} />
    </button>
  )

  const SignInButton = () => (
    <button 
      type="button" 
      className="px-4 w-full sm:w-auto relative overflow-hidden group transition-all duration-300 hover:scale-105 active:scale-95 bg-gradient-to-r from-brand-600 to-brand-700 hover:from-brand-700 hover:to-brand-800 text-white shadow-md hover:shadow-lg rounded-md font-medium py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
      onClick={handleSignInClick}
      disabled={signinLoading || signupLoading}
    >
      <div className="relative flex items-center justify-center">
        <div className={`
          flex items-center transition-all duration-300
          ${signinLoading ? 'opacity-0 -translate-y-2' : 'opacity-100 translate-y-0'}
        `}>
          <span className="flex items-center transition-transform duration-200 group-hover:translate-x-0.5">
            Sign In
            <ArrowRight className="ml-1 h-3 w-3 transition-all duration-300 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0" />
          </span>
        </div>

        <div className={`
          absolute flex items-center justify-center transition-all duration-300
          ${signinLoading ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}
        `}>
          <span className="text-xs whitespace-nowrap">Signing In...</span>
        </div>

        <div className={`
          absolute flex items-center justify-center transition-all duration-300
          opacity-0 scale-50
        `}>
          <Check 
            className="animate-in zoom-in duration-300" 
            size={16} 
            strokeWidth={3}
          />
        </div>
      </div>
      
      <div className={`
        absolute inset-0 -translate-x-full transition-transform duration-1000 bg-gradient-to-r from-transparent via-white/30 to-transparent
        ${!signinLoading ? 'group-hover:translate-x-full' : ''}
      `} />
      
      {signinLoading && (
        <div className="absolute bottom-0 left-0 w-0 h-0.5 bg-brand-300 animate-progress rounded-full" />
      )}
      
      <div className={`
        absolute inset-0 rounded-md transition-all duration-300
        ${signinLoading 
          ? 'bg-brand-400/30 animate-pulse' 
          : 'bg-brand-400/20 group-hover:bg-brand-400/30'
        }
      `} />
      
      <div className="absolute inset-0 overflow-hidden rounded-md">
        <div className={`
          absolute inset-0 bg-white/20 scale-0 rounded-full transition-transform duration-500
          ${signinLoading ? 'scale-150 opacity-0' : ''}
        `} />
      </div>
    </button>
  )

  const renderAuthButtons = () => {
    if (!isInitialized && authLoading) {
      return (
        <div className="flex w-full flex-col space-y-3 sm:flex-row sm:gap-3 sm:space-y-0 md:w-fit">
          <div className="flex items-center justify-center px-8 py-2 rounded-lg bg-gray-100 animate-pulse">
            <span className="text-sm text-gray-600">Loading...</span>
          </div>
        </div>
      )
    }

    if (isAuthenticated && user) {
      const dashboardHref = getDashboardRoute()
      const roles = user.roles || []
      const isAdmin = roles.includes('super_admin') || roles.includes('admin')

      return (
        <div className="flex w-full flex-col space-y-3 sm:flex-row sm:gap-3 sm:space-y-0 md:w-fit">
          <div className="hidden sm:flex items-center px-3 py-2 text-sm text-gray-700 rounded-lg bg-gray-100 transition-colors duration-200 border border-gray-200">
            <User className="h-4 w-4 mr-2 transition-transform duration-200 hover:scale-110" />
            Welcome, {userDisplayName}
          </div>
          
          <Link href={dashboardHref} onClick={(e) => handleDashboardClick(e, dashboardHref)}>
            <Button 
              type="button" 
              variant="outline" 
              className="px-8 w-full sm:w-auto relative overflow-hidden group transition-all duration-300 hover:scale-105 active:scale-95 border-brand-500 text-brand-600 hover:bg-brand-50 hover:text-brand-700 hover:border-brand-600"
              disabled={dashboardLoading}
            >
              <div className="relative flex items-center justify-center">
                <div className={`
                  flex items-center transition-all duration-300
                  ${dashboardLoading ? 'opacity-0 -translate-y-2' : 'opacity-100 translate-y-0'}
                `}>
                  <span className="flex items-center transition-transform duration-200 group-hover:translate-x-0.5">
                    {isAdmin ? 'Admin Panel' : 'Dashboard'}
                    <ArrowRight className="ml-1 h-3 w-3 transition-all duration-300 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0" />
                  </span>
                </div>

                <div className={`
                  absolute flex items-center justify-center transition-all duration-300
                  ${dashboardLoading ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}
                `}>
                  <div className="flex items-center space-x-2">
                    <span className="text-sm">Opening...</span>
                  </div>
                </div>
              </div>
              
              <div className={`
                absolute inset-0 -translate-x-full transition-transform duration-1000 bg-gradient-to-r from-transparent via-brand-50/50 to-transparent
                ${!dashboardLoading ? 'group-hover:translate-x-full' : ''}
              `} />

              {dashboardLoading && (
                <div className="absolute bottom-0 left-0 w-0 h-0.5 bg-brand-500 animate-progress rounded-full" />
              )}

              <div className={`
                absolute inset-0 rounded-md border-2 border-transparent transition-all duration-300
                ${dashboardLoading ? 'border-brand-300 animate-pulse' : ''}
              `} />
            </Button>
          </Link>
          
          <Button 
            type="button" 
            variant="ghost" 
            className="px-8 w-full sm:w-auto relative overflow-hidden group transition-all duration-300 hover:scale-105 active:scale-95 hover:bg-red-50 hover:text-red-700 text-gray-700 border border-transparent hover:border-red-100"
            onClick={handleSignOut}
            disabled={isLoggingOut}
          >
            <span className="flex items-center">
              {isLoggingOut ? (
                <>
                  <span className="ml-2">Signing out...</span>
                </>
              ) : (
                <>
                  Sign Out
                  <svg 
                    className="ml-1 h-3 w-3 transition-all duration-300 transform group-hover:translate-x-0.5" 
                    fill="none" 
                    viewBox="0 0 24 24" 
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7" />
                  </svg>
                </>
              )}
            </span>
            
            {isLoggingOut && (
              <div className="absolute inset-0 bg-red-100 animate-pulse rounded-md" />
            )}
          </Button>
        </div>
      )
    }

    return (
      <div className="flex w-full flex-col space-y-3 sm:flex-row sm:gap-3 sm:space-y-0 md:w-fit">
        <SignUpButton />
        <SignInButton />
      </div>
    )
  }

  return (
    <header>
      <nav
        data-state={menuState ? "active" : "inactive"}
        className={`fixed z-100 w-full transition-all duration-300 ${
          isScrolled 
            ? darkMode 
              ? "bg-slate-900/95 border-b border-slate-700 backdrop-blur-lg shadow-sm"
              : "bg-white/95 border-b border-gray-200 backdrop-blur-lg shadow-sm"
            : "bg-transparent border-transparent"
        }`}
      >
        <div className="mx-auto max-w-7xl px-6 transition-all duration-300">
          <div className="relative flex flex-wrap items-center justify-between gap-6 py-3 lg:gap-0 lg:py-3">
            <div className="flex w-full items-center justify-between gap-12 lg:w-auto">
              <Link 
                href="/" 
                aria-label="home" 
                className="flex items-center space-x-2 transition-transform duration-200 hover:scale-105 active:scale-95"
                onClick={(e) => handleMenuItemClick(e, '/')}
              >
                <Image
                  src="/images/logo/logo.svg"
                  alt="Logo"
                  width={110}
                  height={20}
                  priority
                  className="transition-all duration-300 hover:brightness-110"
                />  
              </Link>

              <button
                onClick={() => setMenuState(!menuState)}
                aria-label={menuState ? "Close Menu" : "Open Menu"}
                aria-expanded={menuState}
                className={`relative z-20 -m-2.5 -mr-4 block cursor-pointer p-2.5 lg:hidden transition-all duration-300 hover:scale-110 active:scale-95 rounded-lg ${darkMode ? 'hover:bg-slate-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'}`}
              >
                <Menu className={`m-auto size-6 duration-200 transition-all ${menuState ? 'rotate-180 scale-0 opacity-0' : 'rotate-0 scale-100 opacity-100'}`} />
                <X className={`absolute inset-0 m-auto size-6 duration-200 transition-all ${menuState ? 'rotate-0 scale-100 opacity-100' : '-rotate-180 scale-0 opacity-0'}`} />
                
                {menuState && (
                  <div className="absolute -top-1 -right-1 w-2 h-2 bg-brand-500 rounded-full animate-ping" />
                )}
              </button>

              <div className="hidden lg:block">
                <ul className="flex gap-8 text-sm">
                  {menuItems.map((item, index) => (
                    <AnimatedNavLink key={index} item={item} />
                  ))}
                </ul>
              </div>
            </div>

            <div className={`${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'} mb-6 w-full flex-wrap items-center justify-center space-y-8 rounded-3xl border p-6 shadow-xl md:flex-nowrap lg:m-0 lg:flex lg:w-fit lg:gap-6 lg:space-y-0 lg:border-transparent lg:bg-transparent lg:p-0 lg:shadow-none transition-all duration-300 ${
              menuState 
                ? 'flex animate-in slide-in-from-top-5 duration-300' 
                : 'hidden lg:flex'
            }`}>
              <div className="lg:hidden">
                <ul className="space-y-2">
                  {menuItems.map((item, index) => (
                    <AnimatedNavLink key={index} item={item} isMobile={true} />
                  ))}
                </ul>
              </div>
              {renderAuthButtons()}
            </div>
          </div>
        </div>
      </nav>

      <style jsx global>{`
        @keyframes progress {
          0% { width: 0%; opacity: 1; }
          50% { width: 70%; opacity: 1; }
          100% { width: 100%; opacity: 0; }
        }
        .animate-progress {
          animation: progress 1.5s ease-in-out infinite;
        }
      `}</style>
    </header>
  )
}