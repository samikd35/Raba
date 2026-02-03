"use client"

import { useState, useCallback, useEffect } from "react"
import { toast } from "react-hot-toast"
import { STORAGE_KEY, VALIDATION_RULES } from "@/constants/onboarding"
import type { FormData } from "@/types/onboarding"

const initialFormData: FormData = {
  industries: [],
  country: "",
  professions: [],
  productTypes: [],
  targetCustomers: [],
  impactFocus: "",
}

export const useOnboardingForm = () => {
  const [currentStep, setCurrentStep] = useState(1)
  const [formData, setFormData] = useState<FormData>(initialFormData)
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false)

  useEffect(() => {
    if (typeof window === "undefined") return

    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const { formData: savedFormData, currentStep: savedStep } = JSON.parse(saved)
        setFormData(savedFormData)
        setCurrentStep(savedStep)
        toast.success("Previous progress restored!", { duration: 2000 })
      }
    } catch (error) {
      console.error("Failed to restore saved data:", error)
      localStorage.removeItem(STORAGE_KEY) // Clean up corrupted data
    }
  }, [])

  const isStepValid = useCallback(
    (step: number): boolean => {
      const rules = VALIDATION_RULES[step]
      if (!rules) return false

      return rules.every((rule) => rule.validate(formData))
    },
    [formData],
  )

  const getStepValidationError = useCallback(
    (step: number): string => {
      const rules = VALIDATION_RULES[step]
      if (!rules) return "Invalid step"

      const failedRule = rules.find((rule) => !rule.validate(formData))
      if (!failedRule) return "Please complete this step"

      return typeof failedRule.message === "function" ? failedRule.message(formData) : failedRule.message
    },
    [formData],
  )

  const isFormValid = useCallback((): boolean => {
    return Object.keys(VALIDATION_RULES).every((step) => isStepValid(Number.parseInt(step)))
  }, [isStepValid])

  const resetForm = useCallback(() => {
    setCurrentStep(1)
    setFormData(initialFormData)
    setHasAttemptedSubmit(false)
  }, [])

  return {
    currentStep,
    formData,
    hasAttemptedSubmit,
    setCurrentStep,
    setFormData,
    setHasAttemptedSubmit,
    isStepValid,
    getStepValidationError,
    isFormValid,
    resetForm,
  }
}
