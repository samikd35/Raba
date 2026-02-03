import PageBreadcrumb from "@/components/common/workspace/PageBreadCrumb";
import VideosExample from "@/components/ui/video/VideosExample";

import React from "react";


export default function VideoPage() {
  return (
    <div>
      <PageBreadcrumb pageTitle="Videos" />

      <VideosExample />
    </div>
  );
}
