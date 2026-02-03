"use client";

import React from "react";
import { useParams } from "next/navigation";
import { ProductRequirementDetailView } from "@/components/prd";

export default function ProductRequirementDetail() {
  const params = useParams();
  const projectId = params?.id as string;

  if (!projectId) {
    return null;
  }

  return (
    <ProductRequirementDetailView
      projectId={projectId}
      backPath="/workspace/product-requirement/projects"
      continuePath={`/workspace/bmc-v2/${projectId}`}
    />
  );
}
