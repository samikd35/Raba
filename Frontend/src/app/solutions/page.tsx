"use client";

import React from 'react';
import { HeroHeader } from '@/components/header';
import Footer from '@/components/landing/Footer';
import SolutionsHero from '@/components/solutions/SolutionsHero';
import Module1Section from '@/components/solutions/Module1Section';
import Module2Section from '@/components/solutions/Module2Section';
import Module3Section from '@/components/solutions/Module3Section';
import Module4Section from '@/components/solutions/Module4Section';

export default function SolutionsPage() {
  return (
    <>
      <HeroHeader />
      <main className="min-h-screen bg-[#f8fafc]">
        <SolutionsHero />
        <Module1Section />
        <Module2Section />
        <Module3Section />
        <Module4Section />
      </main>
      <Footer />
    </>
  );
}
