"use client";
import React from "react";
import ProblemGenerationHistoryDrawer from "./ProblemGenerationHistoryDrawer";

/**
 * Legacy wrapper component for backward compatibility
 * Now uses the new ProblemValidationHistoryDrawer component
 */
export default function ProblemGenerationHistoryDropdown() {
  return <ProblemGenerationHistoryDrawer workspacePath="/team-workspace" />;
}