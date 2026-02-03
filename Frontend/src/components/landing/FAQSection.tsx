"use client"

import type React from "react"
import { useState, useEffect, useRef } from "react"
import { usePathname } from "next/navigation"
import Link from "next/link"
import { ArrowRight } from "lucide-react"

interface FAQ {
  question: string
  answer: string
}

interface FAQSectionProps {
  faqData?: FAQ[]
  showFooter?: boolean
}

const defaultFaqData: FAQ[] = [
  {
    question: "What is Yuba?",
    answer: "Yuba is a sounding board and a reliable, ever-present virtual co-founder for early-stage African founders. At its core, Yuba is an ecosystem of cohorts of specialized AI Venture Builders that combine the unique strengths of purpose-built AI Agents to supercharge your entrepreneurial journey."
  },
  {
    question: "What is Yuba NOT?",
    answer: "Yuba is NOT another AI model. Our AI Agents have been engineered and trained to both interpret proven entrepreneurship frameworks and simulate the thinking process of trusted industry experts and world-class venture builders, thus delivering tailored, relevant, and context-biased actionable insights at every step of the process."
  },
  {
    question: "Do I Need Advanced Prompting Skills to use Yuba?",
    answer: "No. You do not need to worry about your prompting skills. By design, the system helps you narrow down to the core issue. You just need to have a formulated problem statement to start with."
  },
  {
    question: "What if I don't have a problem statement?",
    answer: "No problem. You can leverage the Problem Predictor feature to get started and eventually formulate one before you move forward."
  },
  {
    question: "How Does Yuba Work?",
    answer: "At the heart of the Yuba ecosystem is a meticulously designed and integrated workflow of four modules, Problem Discovery, Value Proposition Design, MVP & Business Model Development, and Market Validation, that progressively guide founders through the critical stages of building a venture. Each stage unlocks sequentially, ensuring a rigorous, evidence-based approach and actionable output. It's a self-directed process, and at any given stage, Yuba provides on-demand expert guidance from our vetted Venture Builders."
  },
  {
    question: "Who is Yuba For?",
    answer: "If you are an early-stage African Founder within the Pre-idea and Market Validation spectrum, Yuba is built for you. If you have validated your market, but still wish to run additional validation, Yuba is for you. If you're a professional who's exploring entrepreneurship but is not yet ready to test the waters with both legs, Yuba is for you. If you are outside of the continent and exploring building something in Africa, this is the right platform for you. And if you are an ESO, a university, or any other form of institution running entrepreneurship programs, we built Yuba for you."
  },
  {
    question: "Can Organizations Customize their Accounts?",
    answer: "Yes. Yuba offers the basic structure for all, and organizations can request customization to match desired operational needs."
  },
  {
    question: "How Many Programs is an Organization Allowed to Run on Yuba?",
    answer: "As many as they wish. There is no limit to the number of programs organizations can run on Yuba. The structure is flexible, down to the level of cohorts."
  },
  {
    question: "Can Organizations onboard their own Venture Builders?",
    answer: "As many as they wish. There is no limit to the number of programs organizations can run on Yuba. The structure is flexible, down to the level of cohorts."
  },
  {
    question: "How do I Unlock the Pro Features?",
    answer: "You can unlock the pro features by upgrading from either purchasing credits yourself or by invitation from an organization whose program you're a part of, in which case, they would grant you credits to access the pro features."
  },
  {
    question: "Can Someone Else Buy Credits for Me?",
    answer: "Yes. Someone else can buy credits and allocate them directly to you."
  },
  {
    question: "What does the Free Plan Include?",
    answer: "The Free plan includes only 30 credits and will allow you help you explore features in the Problem Discovery Module. Credits in this plan expire within two weeks if not used."
  },
  {
    question: "What are Yuba Venture Builders?",
    answer: "Yuba Venture Builders are carefully vetted individuals with either general knowledge that transfers across industries or deep expertise in a particular field or industry. In addition to the requirement to have been a founder or be one in the moment, it is this industry expertise and knowledge that qualify them to advise ventures, grounding their guidance and insights in the African context."
  },
  {
    question: "Is Yuba Venture Builders Access Part of the Pro Feature?",
    answer: "No. Venture Builders are available for booking at an extra cost beyond the paid features. Founders accessing Yuba as part of a program can book and access Venture Builders as instructed by their program management."
  },
  {
    question: "Can Organizations Onboard Their Own Venture Builders?",
    answer: "Absolutely. Organizations can onboard as many people, including coaches and venture Builders, onto their admin account as they wish, and manage access based on roles."
  },
  {
    question: "Who Owns the Data?",
    answer: "You own the data and any work you do, unless you decide to share it with anyone else, or give visibility to other people, such as venture builders, coaches, and their likes. If you are a part of a program on Yuba, however, your program manager and others that the program deems necessary will have direct access to your work by default. Coaches, Venture Builders, and Program managers can access your projects only in View Mode."
  },
  {
    question: "Can I retrieve my work and pick up where I left off?",
    answer: "Yes, you can. Whether you are exploring and validating problems or working through advanced projects, Yuba automatically saves your work, which you can access at any time, going forward."
  },
  {
    question: "Can I Form a Team on Yuba?",
    answer: "Yes, you can join Yuba as either a solo founder or as a Team."
  }
]

const FAQSection: React.FC<FAQSectionProps> = ({ faqData = defaultFaqData, showFooter = false }) => {
  const [openIndex, setOpenIndex] = useState<number | null>(null)
  const [isVisible, setIsVisible] = useState<boolean>(false)
  const sectionRef = useRef<HTMLElement>(null)
  const pathname = usePathname()

  const isStandalonePage = pathname === "/faqs"

  // Determine how many FAQs to show - 5 on landing page, all on standalone page
  const faqsToShow = isStandalonePage ? faqData : faqData.slice(0, 5)


  // Intersection Observer for animations
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting)
      },
      { threshold: 0.1 },
    )

    if (sectionRef.current) {
      observer.observe(sectionRef.current)
    }

    return () => observer.disconnect()
  }, [])

  const toggleAccordion = (index: number): void => {
    setOpenIndex(openIndex === index ? null : index)
  }

  const handleKeyDown = (event: React.KeyboardEvent, index: number): void => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault()
      toggleAccordion(index)
    }
  }

  return (
    <section
      ref={sectionRef}
      className="pb-24 bg-[#f8fafc]"
      aria-label="Frequently Asked Questions"
      id='faqs'
    >
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-8 md:mb-12 lg:mb-12 pt-24">
        <h2 className="text-3xl md:text-4xl lg:text-5xl mx-auto max-w-[800px] font-bold text-slate-900 mb-4">
            Frequently Asked <span className="text-brand-500">Questions</span>
          </h2>
        </div>

        {/* FAQ Accordion */}
        <div className="max-w-3xl mx-auto flex flex-col gap-4 items-center justify-center">
            <div className="space-y-6">
              {faqsToShow.map((faq, index) => (
                <div key={index} className="border  rounded-xl bg-[#FAFCFD]" >
                  {/* Question Button */}
                  <button
                    onClick={() => toggleAccordion(index)}
                    onKeyDown={(e) => handleKeyDown(e, index)}
                    className="
                      w-full px-4 sm:px-6 md:px-8 py-4 text-left
                      focus:outline-none
                      transition-colors duration-200
                    "
                    aria-expanded={openIndex === index}
                    aria-controls={`faq-answer-${index}`}
                    id={`faq-question-${index}`}
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="text-md font-semibold text-brand-500">
                        {faq.question}
                      </h3>

                      {/* Toggle Icon */}
                      <div
                        className={`
                        flex-shrink-0 w-5 h-5 sm:w-6 sm:h-6 flex items-center justify-center
                        text-brand-500 transition-transform duration-200
                        ${openIndex === index ? "rotate-45" : "rotate-0"}
                      `}
                      >
                        <svg
                          width="24"
                          height="24"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path d="M12 5v14m-7-7h14" />
                        </svg>
                      </div>
                    </div>
                  </button>

                  {/* Answer Panel */}
                  <div
                    id={`faq-answer-${index}`}
                    role="region"
                    aria-labelledby={`faq-question-${index}`}
                    className={`
                      overflow-hidden transition-all duration-300 ease-out
                      ${openIndex === index ? "max-h-96 opacity-100" : "max-h-0 opacity-0"}
                    `}
                  >
                    <div className="px-4 sm:px-6 md:px-8 pb-4 ">
                      <p className="text-sm text-slate-600">{faq.answer}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

          {/* More FAQs Button - only show on landing page */}
          {!isStandalonePage && (
            <Link
              href="/faqs"
              className="
                inline-flex items-center gap-2
                px-7 py-3 mt-8
                rounded-full
                bg-gradient-to-r from-brand-500 to-[#128AA3]
                text-sm text-white font-semibold
                transition-all duration-300
                hover:shadow-[0_0_24px_0_rgba(36,70,148,0.4)]
                hover:scale-105
              "
            >
              More FAQs
              <ArrowRight className="w-4 h-4" />
            </Link>
          )}
        </div>
      </div>
      
    </section>
  )
}

export default FAQSection
