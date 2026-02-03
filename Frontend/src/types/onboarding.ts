export interface FormData {
  industries: string[]
  country: string
  professions: string[]
  productTypes: string[]
  targetCustomers: string[]
  impactFocus: string
}

export interface GenerationState {
  status: "idle" | "validating" | "submitting" | "processing" | "completed" | "error"
  progress: number
  message: string
  error?: string
  jobId?: string
  startTime?: number
}

export interface StepConfig {
  id: number
  label: string
  icon: string
}
