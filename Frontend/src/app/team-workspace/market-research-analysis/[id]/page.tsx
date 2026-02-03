"use client";

import { useParams } from "next/navigation";
import CreditCostBadge from "@/components/common/CreditCostBadge";
import PageBreadcrumb from "@/components/common/module 2/sub-module-2/PageBreadCrumb";
import MarketResearchAnalysis from "@/features/market-research-analysis";
import FeatureVideoOverlay from "@/components/feature-videos/FeatureVideoOverlay";
import { FEATURE_IDS, getFeatureVideoConfig } from "@/lib/featureVideos";

export default function MarketResearchAnalysisPage() {
  const params = useParams();
  const projectId = params?.id as string;
  // const featureConfig = getFeatureVideoConfig(FEATURE_IDS.MARKET_RESEARCH_ANALYSIS);

  return (
    <div>
      {/* <FeatureVideoOverlay
        featureId={FEATURE_IDS.MARKET_RESEARCH_ANALYSIS}
        youtubeId={featureConfig.youtubeId}
        resourcesHref={featureConfig.resourcesHref}
        title={featureConfig.title}
        buttonClassName="bottom-32 right-6" 
      /> */}
      <PageBreadcrumb pageTitle="Market Research Findings Analysis" titleSuffix={<CreditCostBadge cost={30} />}  />
      <div>
       <MarketResearchAnalysis projectId={projectId}  />
      </div>
    </div>
  );
}