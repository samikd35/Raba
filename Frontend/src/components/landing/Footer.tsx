"use client"

import type React from "react"

import Image from "next/image"
import { useState, useEffect } from "react"
import instagram from "lucide-react"

interface OpenSections {
  product: boolean
  company: boolean
  resources: boolean
}

interface FooterLink {
  name: string
  href: string
}

interface SocialLink {
  name: string
  href: string
  icon: React.ReactNode
}

interface FooterLinks {
  product: FooterLink[]
  company: FooterLink[]
  resources: FooterLink[]
  legal: FooterLink[]
}

interface SubscriptionResult {
  success: boolean
  isDuplicate: boolean
  message: string
}

const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear()
  const [openSections, setOpenSections] = useState<OpenSections>({
    product: false,
    company: false,
    resources: false,
  })

  // Email subscription state with proper typing
  const [email, setEmail] = useState<string>("")
  const [isValidEmail, setIsValidEmail] = useState<boolean>(false)
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)
  const [submitStatus, setSubmitStatus] = useState<"success" | "duplicate" | "error" | "">("")
  const [statusMessage, setStatusMessage] = useState<string>("")
  const [buttonText, setButtonText] = useState<string>("Subscribe")

  // Email validation regex
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

  const toggleSection = (section: keyof OpenSections): void => {
    setOpenSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }))
  }

  const handleKeyDown = (event: React.KeyboardEvent, section: keyof OpenSections): void => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault()
      toggleSection(section)
    }
  }

  // Email validation effect
  useEffect(() => {
    const trimmedEmail = email.trim()
    setIsValidEmail(trimmedEmail.length > 0 && emailRegex.test(trimmedEmail))
  }, [email])

  const subscribeEmail = async (emailToSubscribe: string): Promise<SubscriptionResult> => {
    try {
      const response = await fetch("/api/newsletter/subscribe", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email: emailToSubscribe }),
      })

      const data = await response.json()

      if (response.status === 409) {
        return { success: false, isDuplicate: true, message: data.error }
      }

      if (!response.ok) {
        throw new Error(data.error || "Subscription failed")
      }

      return { success: true, isDuplicate: false, message: data.message }
    } catch (error) {
      console.error("API subscription error:", error)

      // Fallback to localStorage if API is unavailable
      return fallbackLocalStorage(emailToSubscribe)
    }
  }

  const fallbackLocalStorage = (emailToStore: string): SubscriptionResult => {
    try {
      const existingEmails = JSON.parse(localStorage.getItem("subscribedEmails") || "[]")

      // Check for duplicates
      if (existingEmails.some((subscriber: { email: string }) => subscriber.email === emailToStore)) {
        return { success: false, isDuplicate: true, message: "Already subscribed" }
      }

      const newEmail = {
        email: emailToStore,
        subscribedAt: new Date().toISOString(),
      }
      existingEmails.push(newEmail)
      localStorage.setItem("subscribedEmails", JSON.stringify(existingEmails))
      return { success: true, isDuplicate: false, message: "Successfully subscribed!" }
    } catch (error) {
      console.error("Fallback storage error:", error)
      return { success: false, isDuplicate: false, message: "Something went wrong. Please try again." }
    }
  }





  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()

    if (!isValidEmail || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setSubmitStatus("")
    setStatusMessage("")

    // Trim and lowercase email
    const processedEmail = email.trim().toLowerCase()

    try {
      // Call API to subscribe email
      const result = await subscribeEmail(processedEmail)

      if (result.isDuplicate) {
        setSubmitStatus("duplicate")
        setStatusMessage(result.message)
        setIsSubmitting(false)
        return
      }

      if (result.success) {
        setSubmitStatus("success")
        setStatusMessage(result.message)
        setButtonText("Saved 👍")
        setEmail("")

        // Reset button after 10 seconds
        setTimeout(() => {
          setButtonText("Subscribe")
          setSubmitStatus("")
          setStatusMessage("")
        }, 10000)
      } else {
        throw new Error(result.message)
      }
    } catch (error) {
      console.error("Subscription error:", error)
      setSubmitStatus("error")
      setStatusMessage("Something went wrong. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    setEmail(e.target.value)
    // Clear status when user starts typing again
    if (submitStatus) {
      setSubmitStatus("")
      setStatusMessage("")
    }
  }

  // Determine button state
  const isButtonDisabled = !isValidEmail || isSubmitting

  const getButtonClasses = (): string => {
    const baseClasses = `
      px-4 py-2 font-medium rounded-lg text-sm sm:text-base
      focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 focus:ring-offset-slate-900
      transition-all duration-200 w-full sm:w-auto
    `

    if (submitStatus === "success") {
      return `${baseClasses} bg-green-600 hover:bg-green-700 text-white transform hover:scale-105 active:scale-95 shadow-lg`
    }

    if (isButtonDisabled) {
      return `${baseClasses} bg-slate-600 text-slate-400 cursor-not-allowed opacity-60`
    }

    return `${baseClasses} bg-gradient-vertical hover:from-brand-600 hover:to-brand-700 active:from-brand-700 active:to-brand-600 text-white transform hover:scale-105 active:scale-95 shadow-gradient-btn`
  }

  const footerLinks: FooterLinks = {
    product: [
      { name: "Features", href: "#features" },
      { name: "Pricing", href: "#pricing" },
      { name: "FAQs", href: "#faqs" },
      { name: "Roadmap", href: "#roadmap" },
    ],
    company: [
      { name: "About", href: "#about" },
      { name: "Blog", href: "#blog" },
      { name: "Careers", href: "#careers" },
      { name: "Contact", href: "#contact" },
    ],
    resources: [
      { name: "Documentation", href: "#docs" },
      { name: "Help Center", href: "#help" },
      { name: "Community", href: "#community" },
      { name: "API Reference", href: "#api" },
    ],
    legal: [
      { name: "Privacy Policy", href: "/privacy" },
      { name: "Terms of Service", href: "#terms" },
      { name: "Cookie Policy", href: "#cookies" },
      { name: "GDPR", href: "#gdpr" },
    ],
  }

  const socialLinks: SocialLink[] = [
    {
      name: "LinkedIn",
      href: "https://www.linkedin.com/company/yubanow/",
      icon: (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
        </svg>
      ),
    },
        {
      name: "Instagram",
      href: "https://www.instagram.com/yuba_now/",
      icon: ( 
        <svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" className="bi w-5 h-5" viewBox="0 0 16 16">
          <path d="M8 0C5.829 0 5.556.01 4.703.048 3.85.088 3.269.222 2.76.42a3.9 3.9 0 0 0-1.417.923A3.9 3.9 0 0 0 .42 2.76C.222 3.268.087 3.85.048 4.7.01 5.555 0 5.827 0 8.001c0 2.172.01 2.444.048 3.297.04.852.174 1.433.372 1.942.205.526.478.972.923 1.417.444.445.89.719 1.416.923.51.198 1.09.333 1.942.372C5.555 15.99 5.827 16 8 16s2.444-.01 3.298-.048c.851-.04 1.434-.174 1.943-.372a3.9 3.9 0 0 0 1.416-.923c.445-.445.718-.891.923-1.417.197-.509.332-1.09.372-1.942C15.99 10.445 16 10.173 16 8s-.01-2.445-.048-3.299c-.04-.851-.175-1.433-.372-1.941a3.9 3.9 0 0 0-.923-1.417A3.9 3.9 0 0 0 13.24.42c-.51-.198-1.092-.333-1.943-.372C10.443.01 10.172 0 7.998 0zm-.717 1.442h.718c2.136 0 2.389.007 3.232.046.78.035 1.204.166 1.486.275.373.145.64.319.92.599s.453.546.598.92c.11.281.24.705.275 1.485.039.843.047 1.096.047 3.231s-.008 2.389-.047 3.232c-.035.78-.166 1.203-.275 1.485a2.5 2.5 0 0 1-.599.919c-.28.28-.546.453-.92.598-.28.11-.704.24-1.485.276-.843.038-1.096.047-3.232.047s-2.39-.009-3.233-.047c-.78-.036-1.203-.166-1.485-.276a2.5 2.5 0 0 1-.92-.598 2.5 2.5 0 0 1-.6-.92c-.109-.281-.24-.705-.275-1.485-.038-.843-.046-1.096-.046-3.233s.008-2.388.046-3.231c.036-.78.166-1.204.276-1.486.145-.373.319-.64.599-.92s.546-.453.92-.598c.282-.11.705-.24 1.485-.276.738-.034 1.024-.044 2.515-.045zm4.988 1.328a.96.96 0 1 0 0 1.92.96.96 0 0 0 0-1.92m-4.27 1.122a4.109 4.109 0 1 0 0 8.217 4.109 4.109 0 0 0 0-8.217m0 1.441a2.667 2.667 0 1 1 0 5.334 2.667 2.667 0 0 1 0-5.334"/>
        </svg>
      ),
    },
    {
      name: "Twitter",
      href: "",
      icon: (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M8.29 20.251c7.547 0 11.675-6.253 11.675-11.675 0-.178 0-.355-.012-.53A8.348 8.348 0 0022 5.92a8.19 8.19 0 01-2.357.646 4.118 4.118 0 001.804-2.27 8.224 8.224 0 01-2.605.996 4.107 4.107 0 00-6.993 3.743 11.65 11.65 0 01-8.457-4.287 4.106 4.106 0 001.27 5.477A4.072 4.072 0 012.8 9.713v.052a4.105 4.105 0 003.292 4.022 4.095 4.095 0 01-1.853.07 4.108 4.108 0 003.834 2.85A8.233 8.233 0 012 18.407a11.616 11.616 0 006.29 1.84" />
        </svg>
      ),
    },
    {
      name: "GitHub",
      href: "",
      icon: (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path
            fillRule="evenodd"
            d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
            clipRule="evenodd"
          />
        </svg>
      ),
    },
  ]

  return (
    <footer



      style={{
        backgroundColor: '#0a0a0a',
        backgroundImage: `
        radial-gradient(circle at 25% 25%, #222222 0.5px, transparent 1px),
        radial-gradient(circle at 75% 75%, #111111 0.5px, transparent 1px)
      `,
        backgroundSize: '10px 10px',
        imageRendering: 'pixelated',
      }}


      className="bg-slate-900 text-slate-300 " aria-labelledby="footer-heading">

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-4 py-4 md:py-4 lg:py-16">
        {/* Main Footer Content */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6 sm:gap-8 lg:gap-12">
          {/* Brand Section with Newsletter */}
          <div className="sm:col-span-2 lg:col-span-2">
            <div className="flex items-center mb-6">
              {/* Logo */}
              <div className="flex items-center">
                <Image src="/assets/Logo/yuba-logo-white.svg" alt="Yuba Logo" width={150} height={64} className="h-16 w-auto" />
              </div>
            </div>

            {/* Newsletter Signup */}
            <div className="mb-6">
              <h3 className="text-brand-25 font-semibold mb-3 text-xl">Stay updated</h3>
              <p className="text-slate-400 text-sm mb-4 max-w-sm">
                Get the latest updates on new features and startup insights.
              </p>
              <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 max-w-sm" noValidate>
                <div className="flex-1">
                  <label htmlFor="email-address" className="sr-only">
                    Email address
                  </label>
                  <input
                    id="email-address"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={handleEmailChange}
                    placeholder="Enter your email"
                    aria-describedby="email-status"
                    className="
                      w-full px-3 sm:px-4 py-2
                      bg-slate-800 border border-slate-700 rounded-lg
                      text-white placeholder-slate-400 text-sm sm:text-base
                      focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500
                      transition-colors duration-200
                    "
                  />
                </div>

                <button
                  type="submit"
                  disabled={isButtonDisabled}
                  aria-describedby="email-status"
                  className={getButtonClasses()}
                >
                  {isSubmitting ? (
                    <span className="flex items-center justify-center">
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-current" fill="none" viewBox="0 0 24 24">
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        ></circle>
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>
                      Subscribing...
                    </span>
                  ) : (
                    buttonText
                  )}
                </button>
              </form>

              {/* Status message with aria-live */}
              <div id="email-status" aria-live="polite" aria-atomic="true" className="mt-2 min-h-[1rem]">
                {statusMessage && (
                  <p
                    className={`text-xs ${submitStatus === "success"
                        ? "text-green-400"
                        : submitStatus === "duplicate"
                          ? "text-yellow-400"
                          : submitStatus === "error"
                            ? "text-red-400"
                            : "text-slate-400"
                      }`}
                  >
                    {statusMessage}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Product Links */}
          <div>
            <button
              onClick={() => toggleSection("product")}
              onKeyDown={(e) => handleKeyDown(e, "product")}
              className="
                w-full flex items-center justify-between
                text-white font-semibold mb-3 sm:mb-4 text-sm sm:text-base
                md:cursor-default md:pointer-events-none
                focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 focus:ring-offset-slate-900
                rounded-md p-1 md:p-0
              "
              aria-expanded={openSections.product}
              aria-controls="product-links"
              id="product-heading"
            >
              Product
              <svg
                className={`
                  w-4 h-4 transition-transform duration-200 md:hidden
                  ${openSections.product ? "rotate-180" : "rotate-0"}
                `}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <nav aria-label="Product links">
              <ul
                id="product-links"
                role="region"
                aria-labelledby="product-heading"
                className={`
                  space-y-3 overflow-hidden transition-all duration-300 ease-out
                  md:block md:opacity-100 md:max-h-none
                  ${openSections.product
                    ? "block opacity-100 max-h-96"
                    : "hidden opacity-0 max-h-0 md:block md:opacity-100"
                  }
                `}
              >
                {footerLinks.product.map((link) => (
                  <li key={link.name}>
                    <a
                      href={link.href}
                      className="
                        text-slate-400 hover:text-brand-400 text-sm sm:text-base
                        transition-colors duration-200
                        focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900
                        rounded-md px-1 py-1
                      "
                    >
                      {link.name}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          </div>

          {/* Company Links */}
          <div>
            <button
              onClick={() => toggleSection("company")}
              onKeyDown={(e) => handleKeyDown(e, "company")}
              className="
                w-full flex items-center justify-between
                text-white font-semibold mb-3 sm:mb-4 text-sm sm:text-base
                md:cursor-default md:pointer-events-none
                focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 focus:ring-offset-slate-900
                rounded-md p-1 md:p-0
              "
              aria-expanded={openSections.company}
              aria-controls="company-links"
              id="company-heading"
            >
              Company
              <svg
                className={`
                  w-4 h-4 transition-transform duration-200 md:hidden
                  ${openSections.company ? "rotate-180" : "rotate-0"}
                `}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <nav aria-label="Company links">
              <ul
                id="company-links"
                role="region"
                aria-labelledby="company-heading"
                className={`
                  space-y-3 overflow-hidden transition-all duration-300 ease-out
                  md:block md:opacity-100 md:max-h-none
                  ${openSections.company
                    ? "block opacity-100 max-h-96"
                    : "hidden opacity-0 max-h-0 md:block md:opacity-100"
                  }
                `}
              >
                {footerLinks.company.map((link) => (
                  <li key={link.name}>
                    <a
                      href={link.href}
                      className="
                        text-slate-400 hover:text-brand-400 text-sm sm:text-base
                        transition-colors duration-200
                        focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900
                        rounded-md px-1 py-1
                      "
                    >
                      {link.name}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          </div>

          {/* Contact Us */}
          <div>
            <h3 className="text-white font-semibold mb-3 sm:mb-4 text-sm sm:text-base">Contact Us</h3>
            <div className="space-y-3">
              <a
                href="mailto:info@yubanow.com"
                className="
                  text-slate-400 hover:text-brand-400 text-sm sm:text-base
                  transition-colors duration-200
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900
                  rounded-md px-1 py-1
                  flex items-center
                "
                aria-label="Send us an email"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
                info@yubanow.com
              </a>

              {/* Social Links */}
              <div className="flex space-x-4 pt-2">
                {socialLinks.map((social) => (
                  <a
                    key={social.name}
                    href={social.href}
                    className="
                      text-slate-400 hover:text-brand-400
                      transition-colors duration-200
                      focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900
                      rounded-md p-1
                    "
                    aria-label={`Follow us on ${social.name}`}
                  >
                    {social.icon}
                  </a>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-6 sm:pt-8  border-t border-slate-700">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
            <p className="text-slate-400 text-xs sm:text-sm">© {currentYear} Yuba. All rights reserved.</p>
            <div className="mt-3 sm:mt-0 flex items-center space-x-4 sm:space-x-6">
              <a
                href="/privacy"
                className="
                  text-slate-400 hover:text-brand-400 text-sm
                  transition-colors duration-200
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900
                  rounded-md px-1 py-1
                "
              >
                Privacy
              </a>
              <a
                href="/privacy"
                className="
                  text-slate-400 hover:text-brand-400 text-sm
                  transition-colors duration-200
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900
                  rounded-md px-1 py-1
                "
              >
                Terms
              </a>
              <a
                href="/privacy"
                className="
                  text-slate-400 hover:text-brand-400 text-sm
                  transition-colors duration-200
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900
                  rounded-md px-1 py-1
                "
              >
                Cookies
              </a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}

export default Footer
