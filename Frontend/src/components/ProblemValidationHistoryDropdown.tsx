"use client";
import React from "react";
import ProblemValidationHistoryDrawer from "./ProblemValidationHistoryDrawer";

/**
 * Legacy wrapper component for backward compatibility
 * Now uses the new ProblemValidationHistoryDrawer component
 */
export default function ProblemValidationHistoryDropdown() {
  return <ProblemValidationHistoryDrawer workspacePath="/team-workspace" />;
}