import React from "react";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import { AllProjects } from "@/components/AllProjects";

export default function ProjectsPage() {
  return (
    <div>
      <PageBreadcrumb pageTitle="Value Proposition" />
      <AllProjects basePath="/team-workspace" />
    </div>
  );
}
