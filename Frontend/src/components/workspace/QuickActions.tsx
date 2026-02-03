import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Search, Lightbulb, Target, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { useAuthStore } from '@/stores/authStore';
const QuickActions = () => {
  const { user } = useAuthStore();

  const basePath = user?.tenant_type === 'team' ? '/team-workspace' : '/workspace';

  return (
    <>
      <Card className="@container/card bg-white dark:bg-gray-900">
        <CardHeader>
          <CardTitle>Select a pathway that best aligns with your current progress</CardTitle>
          <CardDescription>
            <span className="hidden @[540px]/card:block">
              Help us guide you to the right tool for your entrepreneurial journey.
            </span>
          </CardDescription>
        </CardHeader>
        <CardContent className="px-2 sm:px-6 -mt-2">
          <div className={`flex flex-wrap ${user?.can_skip_module ? 'justify-center' : 'justify-center'} gap-6`}>
            {/* First Card - brand Theme */}
            <Link
              href={`${basePath}/problem-validator`}
              className="group relative flex flex-col rounded-md border border-brand-500/50 p-4 text-brand-700 cursor-pointer bg-brand-50 hover:bg-brand-100 dark:bg-brand-900/30 dark:text-brand-200 dark:border-brand-500/30 transition-all duration-300 hover:shadow-lg w-full md:max-w-md"
            >
              <div className="absolute top-4 right-4">
                <div className="flex items-center gap-2 px-3 py-1.5 transition-all duration-300 rounded-lg border border-brand-500 bg-transparent group-hover:bg-brand-500 dark:border-brand-400 dark:group-hover:bg-brand-800">
                  <span className="text-sm font-semibold text-brand-600 whitespace-nowrap transition-all duration-300 group-hover:text-white dark:text-brand-300 dark:group-hover:text-brand-200">
                    Start validation
                  </span>
                  <ArrowRight className="w-4 h-4 text-brand-500 transition-all duration-300 group-hover:text-white dark:text-brand-400 dark:group-hover:text-brand-200" />
                </div>
              </div>
              <div className="mb-2 p-2 bg-brand-100 dark:bg-brand-800/30 rounded-full w-10 h-10 flex items-center justify-center">
                <Search className="w-5 h-5 text-brand-600 dark:text-brand-300" />
              </div>
              <h3 className="font-semibold text-lg mb-1">Problem Explorer</h3>
              <p className="text-sm">
                Get contextual and actionable market insights on any problem you'll validate
              </p>
            </Link>

            {/* Second Card - Green Theme - Only shown if can_skip_module is true */}
            {(user?.can_skip_module) && (
              <Link
                href={`${basePath}/projects-mvp`}
                className="group relative flex flex-col rounded-md border border-emerald-500/50 p-4 text-emerald-700 cursor-pointer bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-200 dark:border-emerald-500/30 transition-all duration-300 hover:shadow-lg w-full md:max-w-md"
              >
                <div className="absolute top-4 right-4">
                  <div className="flex items-center gap-2 px-3 py-1.5 transition-all duration-300 rounded-lg border border-emerald-500 bg-transparent group-hover:bg-emerald-500 dark:border-emerald-400 dark:group-hover:bg-emerald-800">
                    <span className="text-sm font-semibold text-emerald-600 whitespace-nowrap transition-all duration-300 group-hover:text-white dark:text-emerald-300 dark:group-hover:text-emerald-200">
                      Go to module 3
                    </span>
                    <ArrowRight className="w-4 h-4 text-emerald-500 transition-all duration-300 group-hover:text-white dark:text-emerald-400 dark:group-hover:text-emerald-200" />
                  </div>
                </div>
                <div className="mb-2 p-2 bg-emerald-100 dark:bg-emerald-800/30 rounded-full w-10 h-10 flex items-center justify-center">
                  <Lightbulb className="w-5 h-5 text-emerald-600 dark:text-emerald-300" />
                </div>
                <h3 className="font-semibold text-lg mb-1">Projects MVP</h3>
                <p className="text-sm">
                  proceed to module 3 directly
                </p>
              </Link>
            )}
          </div>


        </CardContent>
      </Card>
    </>
  )
}

export default QuickActions;