import React from "react";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import MemberProjectsCohortsComponent from "@/components/organization/member-projects/MemberProjectsCohortsComponent";

export default function MemberProjectsCohortsPage() {
  return (
    <div>
      <PageBreadcrumb pageTitle="Member Projects - Select Cohort" />
      <MemberProjectsCohortsComponent />
    </div>
  );
}
