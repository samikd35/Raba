"use client";

import { useParams, useRouter } from "next/navigation";
import CreditCostBadge from "@/components/common/CreditCostBadge";
import PageBreadcrumb from "@/components/common/module 2/sub-module-2/PageBreadCrumb";
import MarketResearchAnalysisUpload from "@/features/market-research-analysis-upload";
import GetUploadedDocuments from "@/features/get-uploaded-documents";
import { useState, useEffect } from "react";

export default function MarketResearchAnalysisUploadPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const [viewAnalysis, setViewAnalysis] = useState(true);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Function to trigger refresh of uploaded documents list
  const handleDocumentChange = () => {
    if (process.env.NODE_ENV === 'development') {
      console.log('🎯 Parent: handleDocumentChange called, incrementing refreshTrigger from', refreshTrigger);
    }
    setRefreshTrigger(prev => {
      const newValue = prev + 1;
      if (process.env.NODE_ENV === 'development') {
        console.log('🎯 Parent: refreshTrigger updated to', newValue);
      }
      return newValue;
    });
  };

  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('🎯 Parent: refreshTrigger changed to', refreshTrigger);
    }
  }, [refreshTrigger]);

  return (
    <div>
      <PageBreadcrumb pageTitle="Market Findings Analyser" titleSuffix={<CreditCostBadge cost={30} />} />
      <MarketResearchAnalysisUpload 
       path={`team-workspace`}
        projectId={projectId} 
        viewAnalysis={viewAnalysis} 
        onDocumentChange={handleDocumentChange}
      />
      <GetUploadedDocuments 
        projectId={projectId} 
        setViewAnalysis={setViewAnalysis} 
        refreshTrigger={refreshTrigger}
      />
    </div>
  );
}