import React from "react";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import CohortsComponent from "@/components/organization/cohorts/CohortsComponent";

export default function CohortsPage() {
  return (
    <div>
      <PageBreadcrumb pageTitle="Cohorts" />
      <CohortsComponent path="organization" />
    </div>
  );
}
