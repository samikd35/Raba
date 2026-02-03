"use client";

import React, { use } from "react";
import dynamic from "next/dynamic";
import PageBreadcrumb from "@/components/common/module 3/sub-module-1/PageBreadCrumb";
import CreditCostBadge from "@/components/common/CreditCostBadge";


const SolutionCritic = dynamic(() => import("@/features/solution-critic"), {
  loading: () => <div className="py-20 flex justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div></div>,
});

export default function SolutionCriticPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;

  return (
    <div className="relative flex flex-col overflow-x-hidden py-2">
      <PageBreadcrumb pageTitle="Evaluate Your Solution Critique" titleSuffix={<CreditCostBadge cost={40} />} />
      <SolutionCritic projectId={projectId} />
    </div>
  );
}
