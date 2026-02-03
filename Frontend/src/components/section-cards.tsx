import { IconTrendingDown, IconTrendingUp } from "@tabler/icons-react"

import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardAction,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export function SectionCards() {
  return (
    <div className="grid grid-cols-1 gap-4 @xl/main:grid-cols-2 @5xl/main:grid-cols-4">
      <Card className="@container/card bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-900 border-gray-100 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow duration-200">
        <CardHeader>
          <CardDescription>Total Reports</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl text-brand-500 dark:text-white">
            1,250
          </CardTitle>
          <CardAction>
            <Badge className="bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800">
              <IconTrendingUp className="h-3.5 w-3.5 mr-1" />
              +12.5%
            </Badge>
          </CardAction>
        </CardHeader>
       
      </Card>
      <Card className="@container/card bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-900 border-gray-100 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow duration-200">
        <CardHeader>
          <CardDescription>Active Projects</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl text-brand-500 dark:text-white">
            2
          </CardTitle>
          <CardAction>
            <Badge className="bg-rose-50 text-rose-700 hover:bg-rose-100 border-rose-200 dark:bg-rose-900/30 dark:text-rose-300 dark:border-rose-800">
              <IconTrendingDown className="h-3.5 w-3.5 mr-1" />
              -20%
            </Badge>
          </CardAction>
        </CardHeader>
       
      </Card>
      <Card className="@container/card bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-900 border-gray-100 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow duration-200">
        <CardHeader>
          <CardDescription>Finished Projects</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl text-brand-500 dark:text-white">
            4
          </CardTitle>
          <CardAction>
            <Badge className="bg-blue-50 text-blue-700 hover:bg-blue-100 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800">
              <IconTrendingUp className="h-3.5 w-3.5 mr-1" />
              +12.5%
            </Badge>
          </CardAction>
        </CardHeader>
        {/* <CardFooter className="flex-col items-start gap-1.5 text-sm -mt-4">
        
          <div className="text-muted-foreground">Engagement exceed targets</div>
        </CardFooter> */}
      </Card>
      <Card className="@container/card bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-900 border-gray-100 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow duration-200">
        <CardHeader>
          <CardDescription>Active Members</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl text-brand-500 dark:text-white">
            5
          </CardTitle>
          <CardAction>
            <Badge className="bg-amber-50 text-amber-700 hover:bg-amber-100 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-800">
              <IconTrendingUp className="h-3.5 w-3.5 mr-1" />
              +4.5%
            </Badge>
          </CardAction>
        </CardHeader>
       
      </Card>
    </div>
  )
}
