"use client";
import React from "react";
import RefinementHistoryDrawer from "./RefinementHistoryDrawer";

/**
 * Legacy wrapper component for backward compatibility
 * Now uses the new ProblemValidationHistoryDrawer component
 */
export default function ProblemValidationHistoryDropdown() {
  return <RefinementHistoryDrawer workspacePath="/team-workspace" />;
}