import React from "react";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ProjectsMvp from "@/components/ProjectsMvp";

export default function ProjectsMvpPage() {
  return (
    <div>
      <PageBreadcrumb pageTitle="Projects" />
      <ProjectsMvp path="team-workspace" />
    </div>
  );
}
