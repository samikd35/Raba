import { Lightbulb,  Search, Target } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { CardContent } from "./ui/card"

export default function QuickActionsLanding() {
  return (
    <Dialog >
      <DialogTrigger asChild>
        <Button 
          size="lg"
          className="w-full sm:w-auto px-8 py-6 text-base font-medium transition-all hover:scale-105"
        >
          Get Started
        </Button>
      </DialogTrigger>
      <DialogContent>
        <div className="mb-2 flex flex-col items-center gap-2 ">
         
          {/* <DialogHeader>
            <DialogTitle className="sm:text-center pt-4 text-brand-500 font-semibold text-[1.5rem] mb-2">
              Select a pathway that best aligns with your current progress
            </DialogTitle>
            <DialogDescription className="sm:text-center">
              Help us guide you to the right tool for your entrepreneurial journey.
            </DialogDescription>
          </DialogHeader> */}
        </div>

        <CardContent className="px-2  -mt-2">
          <div className='grid grid-cols-1 gap-4'>
           

            {/* Second Card - Green Theme */}
            <div className="flex items-center justify-center gap-4 rounded-md border border-emerald-500/50 p-4 text-emerald-700 cursor-pointer bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-200 dark:border-emerald-500/30">
              <div className="mb-2 p-2 bg-emerald-100 dark:bg-emerald-800/30 rounded-full w-10 h-10 flex items-center justify-center">
                <Lightbulb className="w-5 h-5 text-emerald-600 dark:text-emerald-300" />
              </div>
              <p className="text-md">
                Get contextual and actionable market insights on any problem you’ll validate
              </p>
            </div>
          </div>
        </CardContent>

       
      </DialogContent>
    </Dialog>
  )
}
