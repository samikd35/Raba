import React from "react";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import CohortDetailComponent from "@/components/organization/cohorts/CohortDetailComponent";

export default async function CohortsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="space-y-4">
      <PageBreadcrumb pageTitle="Cohort Details" />
      <CohortDetailComponent cohortId={id} />
    </div>
  );
}
