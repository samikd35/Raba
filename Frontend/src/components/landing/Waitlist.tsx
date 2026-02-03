"use client"

import type React from "react"
import { useState, useCallback, useRef, useEffect } from "react"
import Image from "next/image"
import GridShape from "@/components/common/GridShape";

type FeedbackStatus = "idle" | "loading" | "success" | "already_added" | "error"

interface FeedbackMessage {
  title: string
  body: string
}

const feedbackMessages: Record<Exclude<FeedbackStatus, "idle" | "loading">, FeedbackMessage> = {
  success: {
    title: "You're on the waitlist.",
    body: "Thanks for joining Yuba's Waitlist. We'll email you as soon as access opens.",
  },
  already_added: {
    title: "You're already on the waitlist.",
    body: "This email is already registered. We'll notify you when access is available.",
  },
  error: {
    title: "Something went wrong.",
    body: "Please try again later or contact support if the issue persists.",
  },
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const Waitlist: React.FC = () => {
  const [email, setEmail] = useState<string>("")
  const [status, setStatus] = useState<FeedbackStatus>("idle")
  const [isVisible, setIsVisible] = useState<boolean>(false)
  const [showSuccessAnimation, setShowSuccessAnimation] = useState<boolean>(false)
  const sectionRef = useRef<HTMLElement>(null)

  const isValidEmail = EMAIL_REGEX.test(email.trim())
  const isButtonDisabled = !isValidEmail || status === "loading"

  // Intersection Observer for fade-in animation
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting)
      },
      { threshold: 0.1 }
    )

    if (sectionRef.current) {
      observer.observe(sectionRef.current)
    }

    return () => observer.disconnect()
  }, [])

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()

    if (!isValidEmail || status === "loading") return

    setStatus("loading")
    setShowSuccessAnimation(false)

    try {
      const response = await fetch(
        "https://yuba-backend-prod.azurewebsites.net/api/v2/auth/waitlist/join",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email: email.trim(),
            source: "",
            referral_code: "",
            metadata: {},
          }),
        }
      )

      const data = await response.json()

      if (response.ok) {
        if (data.already_exists || data.message?.toLowerCase().includes("already")) {
          setStatus("already_added")
        } else {
          setStatus("success")
          setShowSuccessAnimation(true)
          setEmail("")
        }
      } else {
        if (response.status === 409 || data.message?.toLowerCase().includes("already")) {
          setStatus("already_added")
        } else {
          setStatus("error")
        }
      }
    } catch (error) {
      console.error("Waitlist submission error:", error)
      setStatus("error")
    }
  }, [email, isValidEmail, status])

  const handleEmailChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setEmail(e.target.value)
    // Reset status when user starts typing again
    if (status !== "idle" && status !== "loading") {
      setStatus("idle")
      setShowSuccessAnimation(false)
    }
  }, [status])

  return (
    <section
      ref={sectionRef}
      className="relative pt-24 pb-10 md:pt-32 md:pb-2 overflow-hidden"
      aria-label="Join the Waitlist"
      id="waitlist"
    >
      {/* Background gradient */}
      <div
        className="absolute inset-0 bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950"
        style={{
          background: "linear-gradient(135deg, #0a0a0a 0%, #0d1f1a 25%, #0a1612 50%, #081510 75%, #050505 100%)",
        }}
      />

      {/* Subtle radial glow effects */}
      <div
        className="absolute inset-0 opacity-40"
        style={{
          background: "radial-gradient(ellipse at 30% 20%, rgba(16, 185, 129, 0.15) 0%, transparent 50%), radial-gradient(ellipse at 70% 80%, rgba(6, 95, 70, 0.1) 0%, transparent 50%)",
        }}
      />

      {/* Grid shape decoration - top right */}
      <div className="absolute right-0 top-0 z-0 w-full max-w-[200px] xl:max-w-[350px] opacity-75">
        <GridShape />
      </div>
      <div className="absolute left-0 bottom-0 z-0 w-full max-w-[200px] xl:max-w-[350px] opacity-75">
        <GridShape />
      </div>

      {/* Content */}
      <div
        className={`relative z-10 max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 text-center transition-all duration-700 ${isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}
      >
        {/* Logo Icon */}
        <div className="flex justify-center mb-8">
          <div className="relative w-42 h-42 md:w-28 md:h-28 flex items-center justify-center">
            <Image
              src="/images/logo/logo-dark-mobile.png"
              alt="Yuba Logo"
              width={143}
              height={172}
              className="w-full h-full object-contain lg:scale-175 md:scale-100 sm:scale-75"
              priority
            />
          </div>
        </div>

        {/* Heading */}
        <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-4 tracking-tight">
          Join the  <span className="text-brand-200">waitlist</span>
        </h2>

        {/* Subtitle */}
        <p className="text-gray-400 text-base md:text-lg mb-10 max-w-md mx-auto leading-relaxed">
          Receive all the latest news and updates,
          <br />
          as well as early access to the beta.
        </p>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row items-center justify-center gap-3 max-w-lg mx-auto">
          <div className="relative flex-1 w-full sm:w-auto">
            <input
              type="email"
              value={email}
              onChange={handleEmailChange}
              placeholder="your@email.com"
              className={`
                w-full px-5 py-3.5 rounded-xl
                bg-gray-800/60 backdrop-blur-sm
                border transition-all duration-200
                text-white placeholder-gray-500
                focus:outline-none focus:ring-2 focus:ring-emerald-500/50
                ${email && !isValidEmail
                  ? "border-red-500/50 focus:border-red-500"
                  : "border-gray-700/50 focus:border-emerald-500/50"
                }
              `}
              aria-label="Email address"
              aria-invalid={email ? !isValidEmail : undefined}
              disabled={status === "loading"}
            />
          </div>

          <button
            type="submit"
            disabled={isButtonDisabled}
            className={`
              w-full sm:w-auto px-6 py-3.5 rounded-xl
              font-medium text-sm
              transition-all duration-200
              focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900
              ${isButtonDisabled
                ? "bg-gray-700 text-gray-400 cursor-not-allowed"
                : "bg-white text-gray-900 hover:bg-gray-100 focus:ring-white shadow-lg hover:shadow-xl"
              }
            `}
          >
            {status === "loading" ? (
              <span className="flex items-center justify-center gap-2">
                <svg
                  className="animate-spin h-4 w-4"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Joining...
              </span>
            ) : (
              "Join waitlist"
            )}
          </button>
        </form>

        {/* Inline Feedback Area */}
        <div
          className={`
            mt-6 min-h-[60px] transition-all duration-500 ease-out
            ${status !== "idle" && status !== "loading" ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-2"}
          `}
          role="status"
          aria-live="polite"
        >
          {status !== "idle" && status !== "loading" && (
            <div
              className={`
                inline-flex flex-col items-center gap-1 px-6 py-4 rounded-xl backdrop-blur-sm
                ${status === "success"
                  ? "bg-emerald-500/10 bg-[#a5bbe3] border border-emerald-500/20"
                  : status === "already_added"
                    ? "bg-amber-500/10 border border-amber-500/20"
                    : "bg-red-500/10 border border-red-500/20"
                }
              `}
            >
              {/* Success checkmark animation */}
              {status === "success" && (
                <div className="mb-2">
                  <svg
                    className="w-8 h-8 text-emerald-400"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="2"
                      className="animate-[draw-circle_0.5s_ease-out_forwards]"
                      style={{
                        strokeDasharray: 63,
                        strokeDashoffset: 63,
                        animation: "draw-circle 0.5s ease-out forwards",
                      }}
                    />
                    <path
                      d="M8 12l2.5 2.5L16 9"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      style={{
                        strokeDasharray: 20,
                        strokeDashoffset: 20,
                        animation: "draw-check 0.3s ease-out 0.4s forwards",
                      }}
                    />
                  </svg>
                </div>
              )}

              <p
                className={`
                  font-semibold text-sm
                  ${status === "success"
                    ? "text-emerald-400"
                    : status === "already_added"
                      ? "text-amber-400"
                      : "text-red-400"
                  }
                `}
              >
                {feedbackMessages[status].title}
              </p>
              <p className="text-gray-400 text-sm">
                {feedbackMessages[status].body}
              </p>
            </div>
          )}
        </div>

        {/* Decorative bottom line */}
        <div className="mt-16 flex justify-center">
          <div className="w-48 h-px bg-gradient-to-r from-transparent via-gray-700 to-transparent" />
        </div>
      </div>

      {/* CSS for checkmark animation */}
      <style jsx>{`
        @keyframes draw-circle {
          to {
            stroke-dashoffset: 0;
          }
        }
        @keyframes draw-check {
          to {
            stroke-dashoffset: 0;
          }
        }
      `}</style>
    </section>
  )
}

export default Waitlist
