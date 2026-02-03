"use client";

import PageBreadcrumb from "@/components/common/PageBreadCrumb2";
import React, { useState } from "react";
import CreditCostBadge from "@/components/common/CreditCostBadge";
  
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import IdeaRefinerInput from "@/components/IdeaRefinerInput";

const exampleIdeas = [
  "A service connecting migrant workers in Johannesburg with cheaper remittance channels.",
  "An AI-powered app that helps small farmers in rural Kenya optimize crop yields using weather data.",
  "A platform matching elderly people with young professionals for skill exchange and companionship.",
  "A subscription service delivering fresh, locally-sourced ingredients with recipe cards to busy families."
];

export default function ProblemPredictor() {
  const [selectedIdea, setSelectedIdea] = useState("");
  const router = useRouter();
  const handleIdeaClick = (idea: string) => {
    setSelectedIdea(idea);
  };

  return (
    <div className="relative flex flex-col overflow-x-hidden ">
      <PageBreadcrumb pageTitle="Problem Predictor" titleSuffix={<CreditCostBadge cost={5} />} />
      <div className="relative min-h-screen rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-800 dark:bg-[#101828] xl:px-10 xl:py-12 flex flex-col gap-4 items-center justify-start">
        {/* Back Button - Top Left */}
        <button
          onClick={() => router.push('/workspace/problem-validator')}
          className="absolute top-6 left-6 inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-brand-600 dark:text-brand-400 border border-brand-300 dark:border-brand-600 rounded-lg hover:bg-brand-50 dark:hover:bg-brand-900/30 transition-all duration-200 shadow-sm hover:shadow-md z-10"
        >
          <ArrowLeft className="w-3 h-3" />
          Back to Validator
        </button>

        <div className="mx-auto w-full max-w-[630px] text-center">
          <h3 className="font-semibold text-brand-500 dark:text-white/90 sm:text-2xl break-words">
            What problem are you looking to validate today?
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 sm:text-base">
            Describe your idea in one or two sentences to the best of your ability.
          </p>
        </div>
        <div className="flex flex-col gap-4 mx-auto items-center justify-center mt-4 max-w-[630px] w-full">
          <div className="flex items-center justify-center w-full">
            <h3 className="text-sm text-brand-500 dark:text-white/90">Example ideas:</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
            {exampleIdeas.map((idea, index) => (
              <div
                key={index}
                className="rounded-md border border-brand-500/50 px-4 py-3 text-brand-500 cursor-pointer bg-brand-25 hover:bg-brand-50 dark:bg-brand-800 dark:text-white transition-colors duration-200 break-words"
                onClick={() => handleIdeaClick(idea)}
              >
                <p className="text-sm leading-relaxed">
                  {idea}
                </p>
              </div>
            ))}
          </div>
        </div>
        <IdeaRefinerInput initialValue={selectedIdea} path={"/workspace"} />
      </div>
    </div>
  );
}
