"use client";

import React from "react";
import { useParams } from "next/navigation";
import { ProductRequirementDetailView } from "@/components/prd";

export default function ProductRequirementDetail() {
  const params = useParams();
  const projectId = params?.id as string;

  if (!projectId) {
    return null; // Or some loading state if params aren't ready? Usually they are.
  }

  return (
    <ProductRequirementDetailView
      projectId={projectId}
      backPath="/team-workspace/product-requirement/projects"
      continuePath={`/team-workspace/bmc-v2/${projectId}`}
    />
  );
}
