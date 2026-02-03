import React from "react";
import OnboardingForm from "@/components/OnboardingForm";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";


export default function ProblemExplorer() {
  return (
    <div className="relative flex flex-col overflow-x-hidden ">

      <PageBreadcrumb pageTitle="Problem Explorer" />
            
   
      <div      
      className="rounded-2xl border border-gray-200 bg-white px-4 py-2 dark:border-gray-800 dark:bg-white/[0.03] ">
       
        <OnboardingForm path="team-workspace" />
      </div>
    </div>
  );
}
