import {
  Accordion,
  AccordionItem,
  AccordionContent,
  AccordionTrigger,
} from "@/components/ui/accordion";

interface MoreContextProps {
  title?: string;
  content: string;
  className?: string;
}

export default function MoreContext({ title = "More Context", content, className = "" }: MoreContextProps) {

  return (
    <Accordion className={`w-inherit mt-8 ${className} transition-all duration-300 ease-in-out`} type="single" collapsible>
      <AccordionItem value="more-context" className="border border-brand-200 dark:border-brand-700/50 rounded-lg bg-white dark:bg-gray-900/95 backdrop-blur-sm shadow-sm hover:shadow-md transition-all duration-300 ease-in-out w-auto">
        <AccordionTrigger className="px-4 py-3 hover:no-underline w-auto hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors">
          <span className="text-brand-600 dark:text-brand-300 font-semibold text-lg">
            {title}
          </span>
        </AccordionTrigger>
        <AccordionContent className="p-4 pt-1 bg-white dark:bg-gray-900/50 rounded-b-lg border-t border-brand-100 dark:border-brand-800/30">
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap text-md">
              {content}
            </p>
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
