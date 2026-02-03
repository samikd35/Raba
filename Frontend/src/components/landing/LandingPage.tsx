"use client"
import React from 'react'
import { Suspense } from 'react'
import HeroSection from '../HeroSection'
import FounderWorks from './FounderWorks'
import WhyYuba from './WhyYuba'
import TestimonialsSection from './TestimonialsSection'
import FAQSection from './FAQSection'
import Footer from './Footer'
import EsoSection from './ESOSection'
import AdvantagesSection from './AdvantagesSection'
import { HeroHeader } from "../header"


const LandingPage = () => {
  return (

    <Suspense fallback={null}> 
    <div 
    
  
    className="min-h-screen w-full bg-[#f8fafc] relative ">
      <HeroHeader />
      <HeroSection />
      <WhyYuba />
      <FounderWorks />
      <EsoSection />
      <AdvantagesSection />
      <TestimonialsSection />
      <FAQSection showFooter={true} />
      <Footer />
      </div>  
      </Suspense>)
}

export default LandingPage