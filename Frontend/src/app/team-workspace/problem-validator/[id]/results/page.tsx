"use client";

import { ValidationResultsView } from "@/components/problem-validator/validation-results";
import ActionableInsights from '../insights/page';

export default function ValidationResults({ params }: { params: Promise<{ id: string }> }) {
  return (
    <ValidationResultsView
      params={params}
      workspaceType="team-workspace"
      basePath="/team-workspace"
      ActionableInsightsComponent={ActionableInsights}
    />
  );
}