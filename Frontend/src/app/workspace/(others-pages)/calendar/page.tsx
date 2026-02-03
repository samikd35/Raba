import Calendar from "@/components/calendar/Calendar";
import PageBreadcrumb from "@/components/common/workspace/PageBreadCrumb";

import React from "react";


export default function page() {
  return (
    <div>
      <PageBreadcrumb pageTitle="Calendar" />
      <Calendar />
    </div>
  );
}
