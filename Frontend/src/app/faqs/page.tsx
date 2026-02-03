"use client"

import FAQSection from "@/components/landing/FAQSection"
import Footer from "@/components/landing/Footer"
import { HeroHeader } from "@/components/header"

export default function FAQsPage() {
  return (
    <div className="min-h-screen w-full bg-[#f8fafc]">
      <HeroHeader />
      <main>
        <FAQSection />
      </main>
      <Footer />
    </div>
  )
}
