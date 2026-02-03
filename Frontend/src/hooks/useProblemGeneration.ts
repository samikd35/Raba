"use client"

import { useState, useCallback } from "react"
import { toast } from "react-hot-toast"
import { generateProblemsComplete, mapFormDataToApiParameters } from "@/lib/api/problemGeneration"
import type { GenerationState, FormData } from "@/types/onboarding"
import type { Problem } from "@/lib/api/problemGeneration"

export const useProblemGeneration = () => {
  const [generationState, setGenerationState] = useState<GenerationState>({
    status: "idle",
    progress: 0,
    message: "",
  })
  const [results, setResults] = useState<Problem[] | null>(null)
  const [showResults, setShowResults] = useState(false)

  const generateProblems = useCallback(
    async (formData: FormData) => {
      try {
        setGenerationState({
          status: "validating",
          progress: 0,
          message: "Validating form data...",
          startTime: Date.now(),
        })

        const parameters = mapFormDataToApiParameters(formData)

        setGenerationState((prev) => ({
          ...prev,
          status: "submitting",
          progress: 10,
          message: "Submitting your request...",
        }))

        const response = await generateProblemsComplete(parameters, (progressValue, status, message) => {
          let mappedStatus = status as "processing" | "completed" | "error"
          if (status === "pending" || status === "processing") {
            mappedStatus = "processing"
          }

          setGenerationState((prev) => ({
            ...prev,
            status: mappedStatus,
            progress: Math.min(progressValue, 90),
            message: message || prev.message,
          }))
        })

        if (response.status === "completed" && response.problems) {
          const endTime = Date.now()
          const processingTime = endTime - (generationState.startTime || endTime)

          setResults(response.problems)
          setShowResults(true)

          const seconds = Math.round(processingTime / 1000)
          toast.success(`Successfully generated ${response.problems.length} problems in ${seconds} seconds`)

          setGenerationState({
            status: "completed",
            progress: 100,
            message: `Generated ${response.problems.length} problems`,
            jobId: response.job_id,
            startTime: generationState.startTime,
          })

          setTimeout(() => {
            const resultsElement = document.getElementById("generation-results")
            if (resultsElement) {
              resultsElement.scrollIntoView({ behavior: "smooth" })
            }
          }, 500)
        } else {
          throw new Error(response.message || "Problem generation failed. Please try again.")
        }
      } catch (error:unknown) {
        console.error("Error in problem generation:", error)

        let errorMessage = "An unexpected error occurred"

        if (error.message) {
          errorMessage = error.message
        } else if (typeof error === "string") {
          errorMessage = error
        }

        setGenerationState({
          status: "error",
          progress: 0,
          message: "Failed to generate problems",
          error: errorMessage,
        })

        if (errorMessage.toLowerCase().includes("authentication")) {
          toast.error("Session expired. Please sign in again.")
        } else if (errorMessage.toLowerCase().includes("validation")) {
          toast.error(`Validation error: ${errorMessage}`)
        } else {
          toast.error(errorMessage || "Failed to generate problems. Please try again.")
        }
      }
    },
    [generationState.startTime],
  )

  const resetGeneration = useCallback(() => {
    setShowResults(false)
    setResults(null)
    setGenerationState({
      status: "idle",
      progress: 0,
      message: "",
    })
  }, [])

  return {
    generationState,
    results,
    showResults,
    generateProblems,
    resetGeneration,
  }
}
