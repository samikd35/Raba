import React from "react";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ProjectsPRComponent from "@/components/ProjectsMvp/ProjectsPRComponent";

export default function ProjectsMvpPage() {
  return (
    <div>
      <PageBreadcrumb pageTitle="Projects product requirement" />
      <ProjectsPRComponent path="team-workspace" />
    </div>
  );
}
