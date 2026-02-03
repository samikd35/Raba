import type { FormData } from "@/types/onboarding"

export const STORAGE_KEY = "onboarding_form_data"

export const FORM_STEPS = [
  { id: 1, label: "Industry", icon: "Building" },
  { id: 2, label: "Location", icon: "Globe" },
  { id: 3, label: "Role", icon: "Briefcase" },
  { id: 4, label: "Type", icon: "Target" },
  { id: 5, label: "Customer", icon: "UserCheck" },
  { id: 6, label: "Impact", icon: "Settings" },
] as const

export const INDUSTRY_OPTIONS = [
  "Agriculture / Food",
  "Healthcare / Life Sciences",
  "Education & EdTech",
  "Financial Services & FinTech",
  "Energy & Utilities",
  "Transportation & Mobility",
  "Logistics & Supply Chain",
  "Retail & e-Commerce",
  "Manufacturing",
  "Construction & Real Estate",
  "Media & Entertainment",
  "Tourism & Hospitality",
  "Water & Sanitation",
  "Climate / Environmental Services",
  "Public Services / GovTech",
  "ICT / Telecom",
  "Mining & Natural Resources",
  "Sports & Recreation",
] as const

export const COUNTRY_OPTIONS = [
  "Algeria",
  "Angola",
  "Benin",
  "Botswana",
  "Burkina Faso",
  "Burundi",
  "Cabo Verde",
  "Cameroon",
  "Central African Republic",
  "Chad",
  "Comoros",
  "Congo (Congo-Brazzaville)",
  "Côte d'Ivoire",
  "Democratic Republic of the Congo",
  "Djibouti",
  "Egypt",
  "Equatorial Guinea",
  "Eritrea",
  "Eswatini",
  "Ethiopia",
  "Gabon",
  "Gambia",
  "Ghana",
  "Guinea",
  "Guinea-Bissau",
  "Kenya",
  "Lesotho",
  "Liberia",
  "Libya",
  "Madagascar",
  "Malawi",
  "Mali",
  "Mauritania",
  "Mauritius",
  "Morocco",
  "Mozambique",
  "Namibia",
  "Niger",
  "Nigeria",
  "Rwanda",
  "Sao Tome and Principe",
  "Senegal",
  "Seychelles",
  "Sierra Leone",
  "Somalia",
  "South Africa",
  "South Sudan",
  "Sudan",
  "Tanzania",
  "Togo",
  "Tunisia",
  "Uganda",
  "Zambia",
  "Zimbabwe",
] as const

export const PROFESSION_OPTIONS = [
  "Software / Web Developer",
  "Data / AI Professional",
  "Mechanical Engineer",
  "Electrical / Electronics Engineer",
  "Civil / Construction Engineer",
  "Business / Management",
  "Finance / Accounting",
  "Marketing / Sales",
  "Healthcare Professional",
  "Agriculture / Agronomy",
  "Education / Teaching",
  "Design / UX",
  "Logistics / Supply Chain",
  "Manufacturing / Operations",
  "Legal / Policy",
  "Research / Academia",
  "Other",
] as const

export const PROFESSIONAL_BACKGROUND_OPTIONS = [
  "Academic Researcher",
  "Accountant",
  "Agricultural Specialist",
  "Agronomist",
  "Business Manager",
  "Civil Engineer",
  "Cloud Infrastructure Engineer",
  "Community Manager",
  "Construction Engineer",
  "Customer Success Manager",
  "Cybersecurity Specialist",
  "Data Scientist",
  "Development Practitioner",
  "Educator",
  "Electrical Engineer",
  "Electronics Engineer",
  "Entrepreneur",
  "Finance Manager",
  "Healthcare Professional",
  "Human Resources Manager",
  "Information Security Analyst",
  "Legal Advisor",
  "Logistics Manager",
  "Manufacturing Manager",
  "Management Consultant",
  "Manager",
  "Marketing Manager",
  "Mechanical Engineer",
  "Operations Manager",
  "People & Culture Lead",
  "Policy Analyst",
  "Product Manager",
  "Research Analyst",
  "Sales Executive",
  "Social Scientist",
  "Software Developer",
  "Supply Chain Manager",
  "Teacher",
  "UX Designer",
  "Web Developer",
] as const

export const PRODUCT_TYPE_OPTIONS = [
  "Digital / tech products or services",
  "Physical products",
  "Hardware products",
  "Creative Products / Services",
  "Hybrid (digital + physical)",
] as const

export const TARGET_CUSTOMER_OPTIONS = [
  "Businesses (B2B)",
  "Consumers (B2C)",
  "Both (B2B2C)",
  "Non-profits",
  "Government",
] as const

export const IMPACT_FOCUS_OPTIONS = [
  "Social Impact",
  "Environmental",
  "Economic",
  "Education",
  "Healthcare",
  "Gender Equality",
  "Rural Development",
  "Technology",
  "Other",
] as const

export const VALIDATION_RULES: Record<
  number,
  Array<{
    validate: (formData: FormData) => boolean
    message: string | ((formData: FormData) => string)
  }>
> = {
  1: [
    {
      validate: (formData) => formData.industries.length > 0 && formData.industries.length <= 2,
      message: (formData) =>
        formData.industries.length === 0
          ? "Please select at least one industry"
          : "Please select no more than two industries",
    },
  ],
  2: [
    {
      validate: (formData) => formData.country !== "",
      message: "Please select your country",
    },
  ],
  3: [
    {
      validate: (formData) => formData.professions.length > 0,
      message: "Please select at least one profession",
    },
  ],
  4: [
    {
      validate: (formData) => formData.productTypes.length > 0,
      message: "Please select at least one product type",
    },
  ],
  5: [
    {
      validate: (formData) => formData.targetCustomers.length > 0 && formData.targetCustomers.length <= 3,
      message: (formData) =>
        formData.targetCustomers.length === 0
          ? "Please select at least one target customer"
          : "Please select no more than three target customers",
    },
  ],
  6: [
    {
      validate: (formData) => formData.impactFocus !== "",
      message: "Please select an impact focus",
    },
  ],
}
