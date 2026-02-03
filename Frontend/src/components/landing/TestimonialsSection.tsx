"use client"

import type React from "react"
import { useState, useEffect, useRef, useCallback, useMemo } from "react"
import { useRouter } from "next/navigation"
import Image from "next/image"
import QuickActionsLanding from "../QuickActionsLanding"

interface Testimonial {
  id: number
  photoPng: string
  name: string
  title: string
  country: string
  quote: string
}

interface ButtonDescriptions {
  button1: string
  button2: string
  button3: string
}

// Testimonials data array - moved outside component to prevent recreation
const testimonials: Testimonial[] = [
  {
    id: 1,
    photoPng: "/assets/testimonials/Chidi.jpg",
    name: "Chidi Afulezi",
    title: "Product Sensei",
    country: "Nigeria - United States",
    quote:
      "I work with a lot of founders, product leaders, and teams, and the challenge of accessing and using accurate, relevant, and context-sensitive information in Africa is real and present. Yuba may have cracked the code on this, and if you're serious about helping founders build products that customers will love, this tool should be a part of your daily product stack.",
  },
  {
    id: 2,
    photoPng: "/assets/testimonials/Dennis.png",
    name: "Dennis Mhangami",
    title: "Venture Builder & MD, TheStartUpCoach",
    country: "South Africa",
    quote:
      "The systematic de-risking, integrated workflow, and actionable outputs at every stage, and the ability to simultaneously guide founders from ambiguous ideas to validated ventures, while empowering ESOs to scale world-class venture support, are a real and unique Yuba advantage.",
  },
  {
    id: 3,
    photoPng: "/assets/testimonials/Ermias.jpg",
    name: "Ermias Mekonnen",
    title: "Co-Founder & CEO, MYCO & Jasiri Fellow",
    country: "Rwanda",
    quote:
      "I've been testing this tool and I'm really impressed by how powerful it is—not just in surfacing highly relevant sources, but also in providing eye-opeing insights. Even by just running the problem we're solcing for, it provided fresh perspectives tailored to my company's, MYCO, problem space. Yuba is timely, and a much needed intervention, not just to get started, but also to check oneself along the process.",
  },
  {
    id: 4,
    photoPng: "/assets/testimonials/Mia.jpg",
    name: "Mia Bunn",
    title: "Director Talent Acceleration, Vitatalent Consulting",
    country: "South Africa",
    quote:
      "Finally, a platform designed for Africa's entrepreneurs. Unlike tools built around American and European markets, this platform is different. It is built with Africa's unique market dynamics, legislation, and competitive environments in mind. In minutes, it produces high-quality reports that provides the clarity and actionable insights entrepreneurs need to move forward with confidence. This true game-changer will transform how African founders test and pursue opportunities.",
  },
  {
    id: 5,
    photoPng: "/assets/testimonials/kirubel.jpeg",
    name: "Kirubel Engidawork",
    title: "Co-Founder & COO, Lije Care",
    country: "Ethiopia",
    quote:
      "Yuba makes the toughest part of starting up, problem discovery and validation, feel clearer and actionable. Just at the first try, it helped me stress test my assumptions, uncover insights I'd have missed, and cut through the early-stage fog with focus and confidence. I share this both as a founder and an ecosystem builder who sees entrepreneurs struggle at this exact stage, and with Yuba, this is definitely about to change, for good.",
  },
  {
    id: 6,
    photoPng: "/assets/testimonials/Rinah.jpg",
    name: "Rinah Lidonde",
    title: "Co-Founder & CMO, ProPath Sports",
    country: "Kenya",
    quote:
      "As a founder already in the deep skin of the game, I ran the same problem we're solving into this platform, and to my surprise, it spit out information that took me and my two co-founders almost a year to get down to - and this time in a very structured and digestibe format. It truly felt like having an experienced cofounder by my side. If you are building, no matter your stage, you will certainly need Yuba.",
  },
  {
    id: 7,
    photoPng: "/assets/testimonials/Becky.WEBP",
    name: "Becky Tsadik",
    title: "Founder & CEO, 25x50",
    country: "Ethiopia & Kenya",
    quote: "I did my first customer research interview an was able to ask thoughtful questions to get meaningful responses. Yuba's discovery process goes well beyond generating generic queries. I had a collaborative thought partner and was ready to conduct the interview with confidence in 20 minutes. So many insights, thanks to those strong questions."
  }
]

// Constants
const AUTO_ROTATION_INTERVAL = 10000
const ANIMATION_DELAY = 100
const INITIAL_CARDS_PER_VIEW = 3

const TestimonialsSection: React.FC = () => {
  const router = useRouter()
  const [currentIndex, setCurrentIndex] = useState<number>(0)
  const [isHovered, setIsHovered] = useState<boolean>(false)
  const [isVisible, setIsVisible] = useState<boolean>(false)
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false)
  const [hoveredButton, setHoveredButton] = useState<keyof ButtonDescriptions | null>(null)
  const [prefersReducedMotion, setPrefersReducedMotion] = useState<boolean>(false)
  const [cardsPerView, setCardsPerView] = useState<number>(INITIAL_CARDS_PER_VIEW)
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const sectionRef = useRef<HTMLElement | null>(null)

  // Default modal description text
  const defaultModalDescription: string = "Help us guide you to the right tool for your entrepreneurial journey."

  // Custom descriptions for each button on hover
  const buttonDescriptions: ButtonDescriptions = useMemo(() => ({
    button1: "You are exactly in the right place. Let's begin the exploration.",
    button2: "Excellent! We'll now help you understand the problem you could be solving.",
    button3: "Congratulations! You're ready to proceed to the Problem Exploration Engine.",
  }), [])

  // Check for reduced motion preference
  useEffect(() => {
    if (typeof window === "undefined") return

    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)")
    setPrefersReducedMotion(mediaQuery.matches)

    const handleMediaChange = () => {
      setPrefersReducedMotion(mediaQuery.matches)
    }

    mediaQuery.addEventListener("change", handleMediaChange)
    return () => mediaQuery.removeEventListener("change", handleMediaChange)
  }, [])

  // Get cards per view based on screen size
  const getCardsPerView = useCallback((): number => {
    if (typeof window === "undefined") return INITIAL_CARDS_PER_VIEW
    if (window.innerWidth < 768) return 1 // mobile
    if (window.innerWidth < 1024) return 2 // tablet
    return 3 // desktop
  }, [])

  // Update cards per view on resize with throttling
  useEffect(() => {
    let resizeTimeout: NodeJS.Timeout

    const handleResize = () => {
      clearTimeout(resizeTimeout)
      resizeTimeout = setTimeout(() => {
        setCardsPerView(getCardsPerView())
      }, 150) // Throttle resize events
    }

    if (typeof window !== "undefined") {
      // Set initial value
      setCardsPerView(getCardsPerView())
      window.addEventListener("resize", handleResize)
      return () => {
        window.removeEventListener("resize", handleResize)
        clearTimeout(resizeTimeout)
      }
    }
  }, [getCardsPerView])

  // Calculate total pages
  const totalPages: number = useMemo(() => 
    Math.ceil(testimonials.length / cardsPerView), 
    [cardsPerView]
  )

  // Get current page (0-indexed)
  const currentPage: number = useMemo(() => 
    Math.floor(currentIndex / cardsPerView), 
    [currentIndex, cardsPerView]
  )

  // Auto-rotation logic
  useEffect(() => {
    if (!isHovered && !prefersReducedMotion) {
      intervalRef.current = setInterval(() => {
        setCurrentIndex((prevIndex) => {
          const nextIndex = prevIndex + cardsPerView
          return nextIndex >= testimonials.length ? 0 : nextIndex
        })
      }, AUTO_ROTATION_INTERVAL)
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [isHovered, cardsPerView, prefersReducedMotion])

  // Intersection Observer for animations
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting)
      },
      { threshold: 0.1 },
    )

    const currentSectionRef = sectionRef.current
    if (currentSectionRef) {
      observer.observe(currentSectionRef)
    }

    return () => {
      if (currentSectionRef) {
        observer.unobserve(currentSectionRef)
      }
    }
  }, [])

  // Navigation functions
  const goToPrevious = useCallback((): void => {
    setCurrentIndex((prevIndex) => {
      const newIndex = prevIndex - cardsPerView
      return newIndex < 0 ? testimonials.length - cardsPerView : newIndex
    })
  }, [cardsPerView])

  const goToNext = useCallback((): void => {
    setCurrentIndex((prevIndex) => {
      const nextIndex = prevIndex + cardsPerView
      return nextIndex >= testimonials.length ? 0 : nextIndex
    })
  }, [cardsPerView])

  const goToPage = useCallback((pageIndex: number): void => {
    setCurrentIndex(pageIndex * cardsPerView)
  }, [cardsPerView])

  // Keyboard navigation
  const handleKeyDown = useCallback((event: React.KeyboardEvent, action: () => void): void => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault()
      action()
    } else if (event.key === "ArrowLeft") {
      event.preventDefault()
      goToPrevious()
    } else if (event.key === "ArrowRight") {
      event.preventDefault()
      goToNext()
    }
  }, [goToPrevious, goToNext])

  // Get visible testimonials
  const visibleTestimonials: Testimonial[] = useMemo(() => {
    const visible: Testimonial[] = []
    for (let i = 0; i < cardsPerView; i++) {
      const index = (currentIndex + i) % testimonials.length
      visible.push(testimonials[index])
    }
    return visible
  }, [currentIndex, cardsPerView])

  // Modal handler functions
  const openModal = useCallback((): void => {
    setIsModalOpen(true)
    if (typeof document !== "undefined") {
      document.body.style.overflow = "hidden"
    }
  }, [])

  const closeModal = useCallback((): void => {
    setIsModalOpen(false)
    if (typeof document !== "undefined") {
      document.body.style.overflow = "unset"
    }
  }, [])

  const handleYes = useCallback((): void => {
    router.push("/market-validation")
    closeModal()
  }, [router, closeModal])

  const handleIdea = useCallback((): void => {
    router.push("/prefine")
    closeModal()
  }, [router, closeModal])

  const handleNo = useCallback((): void => {
    console.log("handleNo clicked - navigating to /problem-generator")
    setIsModalOpen(false)
    router.push("/problem-generator")
  }, [router])

  // Handle escape key to close modal
  useEffect(() => {
    const handleEscapeKey = (event: KeyboardEvent): void => {
      if (event.key === "Escape" && isModalOpen) {
        closeModal()
      }
    }

    if (isModalOpen && typeof document !== "undefined") {
      document.addEventListener("keydown", handleEscapeKey)
      return () => {
        document.removeEventListener("keydown", handleEscapeKey)
      }
    }
  }, [isModalOpen, closeModal])

  // Mouse event handlers
  const handleMouseEnter = useCallback(() => setIsHovered(true), [])
  const handleMouseLeave = useCallback(() => setIsHovered(false), [])

  // Testimonial card component for better reusability
  const TestimonialCard = useCallback(({ testimonial, index }: { testimonial: Testimonial; index: number }) => (
    <div
      key={`${testimonial.id}-${currentIndex}`}
      className={`
        bg-gradient-to-br from-white via-white to-sky-50/30 rounded-2xl p-8
        shadow-lg shadow-slate-200/50 
        border border-slate-100 relative
        transition-all duration-500 ease-out
        hover:shadow-xl hover:shadow-sky-100/30 hover:border-sky-200/50
        flex flex-col h-full
        ${isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"}
      `}
      style={{
        transitionDelay: prefersReducedMotion ? "0ms" : `${index * ANIMATION_DELAY}ms`,
        boxShadow:
          "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06), 0 0 0 1px rgba(27, 106, 156, 0.2)",
      }}
    >
      {/* Quote Icon with Color Gradient */}
      <div className="absolute top-6 left-6">
        <div className="p-2 rounded-full bg-gradient-to-br from-[#128AA3]/20 to-[#244694]/20">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            className="text-gradient-to-r from-[#128AA3] to-[#244694]"
            style={{ filter: "drop-shadow(0 1px 1px rgba(0, 0, 0, 0.05))" }}
          >
            <defs>
              <linearGradient id="quoteGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#128AA3" />
                <stop offset="100%" stopColor="#244694" />
              </linearGradient>
            </defs>
            <path
              d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10h-9.983zm-14.017 0v-7.391c0-5.704 3.748-9.57 9-10.609l.996 2.151c-2.433.917-3.996 3.638-3.996 5.849h4v10h-10z"
              fill="url(#quoteGradient)"
            />
          </svg>
        </div>
      </div>

      {/* Testimonial Text with Enhanced Styling */}
      <blockquote className="text-slate-900 text-base leading-relaxed mb-6 mt-8 border-l-4 border-[#128AA3]/20 pl-4 italic flex-grow">
        "{testimonial.quote}"
      </blockquote>

      {/* Author Info with Enhanced Styling */}
      <div className="flex items-center mt-auto pt-4 border-t border-slate-100">
        <Image
          src={testimonial.photoPng || "/placeholder.svg"}
          alt={`${testimonial.name}, ${testimonial.title}`}
          width={48}
          height={48}
          className="w-12 h-12 rounded-full object-cover mr-4 ring-2 ring-[#128AA3]/30 shadow-lg"
          style={{
            boxShadow: "0 0 0 2px white, 0 0 0 4px rgba(18, 138, 163, 0.1)",
          }}
          loading="lazy"
          sizes="48px"
        />
        <div>
          <div className="font-semibold bg-gradient-to-r from-[#128AA3] to-[#244694] text-transparent bg-clip-text">
            {testimonial.name}
          </div>
          <div className="text-slate-500 text-sm font-medium">{testimonial.title}</div>
          <div className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gradient-to-r from-[#128AA3]/10 to-[#244694]/10 border border-[#128AA3]/20">
            <svg className="w-4 h-4 text-[#128AA3]" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
            </svg>
            <span className="text-[#128AA3] text-sm font-semibold bg-gradient-to-r from-[#128AA3] to-[#244694] text-transparent bg-clip-text">
              {testimonial.country}
            </span>
          </div>
        </div>
      </div>
    </div>
  ), [currentIndex, isVisible, prefersReducedMotion])

  return (
    <section
      id='testimonials'
      ref={sectionRef}
      className="pt-16 md:pt-24 bg-[#FAFCFD] lg:pb-16"
      aria-label="Customer Testimonials"
      style={{
        background: "#ffffff",
        backgroundImage: "radial-gradient(circle at 1px 1px, rgba(0, 0, 0, 0.20) 1px, transparent 0)",
        backgroundSize: "20px 20px",
      }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl lg:text-5xl mx-auto max-w-[800px] font-bold text-slate-900 mb-4">
            Trusted by <br /> <span className="text-brand-500 ">Founders</span> & <span className="text-brand-500">Ecosystem</span> Builders
          </h2>
        </div>

        {/* Testimonials Carousel */}
        <div
          className="relative"
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          aria-live="polite"
          aria-label={`Testimonial ${currentPage + 1} of ${totalPages}`}
        >
          {/* Testimonial Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-12 auto-rows-fr">
            {visibleTestimonials.map((testimonial, index) => (
              <TestimonialCard 
                key={`${testimonial.id}-${currentIndex}-${index}`}
                testimonial={testimonial}
                index={index}
              />
            ))}
          </div>

          {/* Navigation Controls */}
          <div className="flex items-center justify-center gap-8 ">
            {/* Previous Button */}
            <button
              onClick={goToPrevious}
              onKeyDown={(e) => handleKeyDown(e, goToPrevious)}
              className="
                p-3 rounded-full bg-gradient-to-br from-white to-sky-50 shadow-md border border-slate-200
                hover:shadow-lg hover:border-[#128AA3]/30 hover:bg-gradient-to-br hover:from-white hover:to-[#128AA3]/10
                focus:outline-none focus:ring-2 focus:ring-[#128AA3] focus:ring-offset-2
                transition-all duration-300 ease-in-out
                disabled:opacity-50 disabled:cursor-not-allowed
              "
              aria-label="Previous Testimonials"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>

            {/* Pagination Dots */}
            <div className="flex gap-2" role="tablist" aria-label="Testimonial pages">
              {Array.from({ length: totalPages }).map((_, pageIndex) => (
                <button
                  key={pageIndex}
                  onClick={() => goToPage(pageIndex)}
                  onKeyDown={(e) => handleKeyDown(e, () => goToPage(pageIndex))}
                  className={`
                    w-3 h-3 rounded-full transition-all duration-300 ease-in-out
                    focus:outline-none focus:ring-2 focus:ring-[#128AA3] focus:ring-offset-2
                    ${
                      currentPage === pageIndex
                        ? "bg-gradient-to-r from-[#128AA3] to-[#244694] w-8 shadow-md shadow-[#128AA3]/20"
                        : "bg-slate-300 hover:bg-[#128AA3]/50"
                    }
                  `}
                  role="tab"
                  aria-selected={currentPage === pageIndex}
                  aria-label={`Go to Testimonial page ${pageIndex + 1}`}
                />
              ))}
            </div>

            {/* Next Button */}
            <button
              onClick={goToNext}
              onKeyDown={(e) => handleKeyDown(e, goToNext)}
              className="
                p-3 rounded-full bg-gradient-to-br from-white to-sky-50 shadow-md border border-slate-200
                hover:shadow-lg hover:border-[#128AA3]/30 hover:bg-gradient-to-br hover:from-white hover:to-[#128AA3]/10
                focus:outline-none focus:ring-2 focus:ring-[#128AA3] focus:ring-offset-2
                transition-all duration-300 ease-in-out
                disabled:opacity-50 disabled:cursor-not-allowed
              "
              aria-label="Next Testimonials"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 18l6-6-6-6" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* CTA Block */}
      <div 
        style={{
          backgroundColor: '#0a0a0a',
          backgroundImage: `
            radial-gradient(circle at 25% 25%, #222222 0.5px, transparent 1px),
            radial-gradient(circle at 75% 75%, #111111 0.5px, transparent 1px)
          `,
          backgroundSize: '10px 10px',
          imageRendering: 'pixelated',
        }}
      >
        {/* <div className="relative z-10 max-w-3xl mx-auto py-16 flex flex-col items-center mt-20 px-8 md:px-1">
          <h2 
            id="cta-heading"
            className="text-3xl sm:text-5xl md:text-6xl font-bold tracking-tight leading-tight text-brand-200 text-center"
          >
            Join <span className="text-white">Yuba</span> Today
          </h2>
          <p className="text-md text-brand-50 mb-8 text-center">
           Move from idea to execution with clarity. Yuba guides you through problem discovery, market validation, and practical next steps to build with confidence.
          </p>
          <QuickActionsLanding/>
        </div> */}
      </div>
    </section>
  )
}

export default TestimonialsSection