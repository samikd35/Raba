"use client"

import { useId, useRef, useState } from "react"
import { UserRoundPlusIcon, PlusIcon, AlertCircleIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { CreditAllocator } from "@/lib/validation"


export default function InviteTeamMember() {
  const [emails, setEmails] = useState([
    "mark@yourcompany.com",
    "jane@yourcompany.com",
    "",
  ])
  const [creditsPerMember, setCreditsPerMember] = useState<number>(100)
  const [organizationLimit, setOrganizationLimit] = useState<number>(1000)
  const [currentUsage, setCurrentUsage] = useState<number>(200)
  const [validationMessage, setValidationMessage] = useState<string>("")
  const [isValid, setIsValid] = useState<boolean>(true)
  const [ setCopied] = useState<boolean>(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const lastInputRef = useRef<HTMLInputElement>(null)

  const addEmail = () => {
    setEmails([...emails, ""])
  }

  const handleEmailChange = (index: number, value: string) => {
    const newEmails = [...emails]
    newEmails[index] = value
    setEmails(newEmails)
    validateCredits(newEmails.filter(email => email.trim() !== "").length, creditsPerMember);
  }

  const handleCreditsChange = (value: number) => {
    setCreditsPerMember(value);
    validateCredits(emails.filter(email => email.trim() !== "").length, value);
  }

  const validateCredits = (inviteeCount: number, credits: number) => {
    const result = CreditAllocator.isAllocationValid(
      inviteeCount,
      credits,
      organizationLimit,
      currentUsage
    );
    
    setIsValid(result.isValid);
    setValidationMessage(result.message);
  }



  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button className="bg-brand-500 text-white">  <PlusIcon
                      size={16}
                      aria-hidden="true"
                    />
                    Invite members</Button>
      </DialogTrigger>
      <DialogContent
      className="dark:bg-[#0c131f] z-50"
        onOpenAutoFocus={(e) => {
          e.preventDefault()
          lastInputRef.current?.focus()
        }}
      >
        <div className="flex flex-col gap-2">
          <div
            className="flex size-11 shrink-0 items-center justify-center rounded-full border"
            aria-hidden="true"
          >
            <UserRoundPlusIcon className="opacity-80" size={16} />
          </div>
          <DialogHeader>
            <DialogTitle className="text-left">Invite team members</DialogTitle>
            <DialogDescription className="text-left">
              Invite teammates to your workspace.
            </DialogDescription>
          </DialogHeader>
        </div>

        <form className="space-y-5">
          <div className="space-y-4">
            <div className="*:not-first:mt-2">
              <Label>Invite via email</Label>
              <div className="space-y-3">
                {emails.map((email, index) => (
                  <Input
                    key={index}
                    id={`team-email-${index + 1}`}
                    placeholder="hi@yourcompany.com"
                    type="email"
                    value={email}
                    onChange={(e) => handleEmailChange(index, e.target.value)}
                    ref={index === emails.length - 1 ? lastInputRef : undefined}
                  />
                ))}
              </div>
            </div>
            <button
              type="button"
              onClick={addEmail}
              className="text-sm underline hover:no-underline"
            >
              + Add another
            </button>
          </div>
          
          {/* Credit Allocation */}
          <div className="space-y-4">
            <div>
              <Label htmlFor="credits-per-member">Credits per Member</Label>
              <Input
                id="credits-per-member"
                type="number"
                min="1"
                value={creditsPerMember}
                onChange={(e) => handleCreditsChange(Number(e.target.value))}
                className="mt-1"
              />
            </div>
            
            {/* Credit Information */}
            <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 text-sm">
              <div className="flex justify-between mb-1">
                <span>Organization Limit:</span>
                <span className="font-medium">{organizationLimit.toLocaleString()}</span>
              </div>
              <div className="flex justify-between mb-1">
                <span>Current Usage:</span>
                <span className="font-medium">{currentUsage.toLocaleString()}</span>
              </div>
              <div className="flex justify-between mb-1">
                <span>Available Credits:</span>
                <span className="font-medium">{(organizationLimit - currentUsage).toLocaleString()}</span>
              </div>
              <div className="flex justify-between font-medium mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                <span>Required for {emails.filter(email => email.trim() !== "").length} members:</span>
                <span>{(emails.filter(email => email.trim() !== "").length * creditsPerMember).toLocaleString()}</span>
              </div>
            </div>
            
            {/* Validation Message */}
            {validationMessage && (
              <div className={`flex items-center p-3 rounded-lg ${isValid ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200' : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'}`}>
                <AlertCircleIcon className="h-5 w-5 mr-2 flex-shrink-0" />
                <span>{validationMessage}</span>
              </div>
            )}
          </div>
          
          <Button 
            type="button" 
            className="w-full"
            disabled={!isValid}
          >
            Send invites
          </Button>
        </form>

       
      </DialogContent>
    </Dialog>
  )
}
