"use client";

import React, { use } from "react";
import dynamic from "next/dynamic";
import PageBreadcrumb from "@/components/common/module 3/sub-module-1/PageBreadCrumb";
import CreditCostBadge from "@/components/common/CreditCostBadge";
import FeatureVideoOverlay from "@/components/feature-videos/FeatureVideoOverlay";
import { FEATURE_IDS, getFeatureVideoConfig } from "@/lib/featureVideos";


const SolutionCritic = dynamic(() => import("@/features/solution-critic"), {
  loading: () => <div className="py-20 flex justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div></div>,
});

export default function SolutionCriticPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;
  const featureConfig = getFeatureVideoConfig(FEATURE_IDS.SOLUTION_CRITIC);

  return (
    <div className="relative flex flex-col overflow-x-hidden py-2">
      <FeatureVideoOverlay
        featureId={FEATURE_IDS.SOLUTION_CRITIC}
        youtubeId={featureConfig.youtubeId}
        resourcesHref={featureConfig.resourcesHref}
        title={featureConfig.title}
      />
      <PageBreadcrumb pageTitle="Evaluate Your Solution Critique" titleSuffix={<CreditCostBadge cost={40} />} />
      <SolutionCritic projectId={projectId} />
    </div>
  );
}
