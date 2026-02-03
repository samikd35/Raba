import React from 'react';
import { motion } from 'framer-motion';
import { FileText, Target, PlayCircle, TrendingUp, Plus } from 'lucide-react';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from '@/components/ui/button';
import { CreateProjectModal } from './CreateProjectModal';
import { useAuthStore } from '@/stores/authStore';


interface ProjectsEmptyProps {
  onGoToCustomerUnderstanding: () => void;
  onStartValidationProject: () => void;
  isCreateModalOpen: boolean;
  onCloseCreateModal: () => void;
  onProjectCreated: () => void;
  onOpenCreateModal: () => void;
}

/**
 * Empty state component when no projects exist
 */
export const ProjectsEmpty = React.memo(({
  onGoToCustomerUnderstanding,
  onStartValidationProject,
  isCreateModalOpen,
  onCloseCreateModal,
  onProjectCreated,
  onOpenCreateModal
}: ProjectsEmptyProps) => {
  const { user } = useAuthStore();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center py-8 px-4"
    >
      <Card className="bg-linear-to-br from-brand-50 to-brand-50 dark:from-gray-900 dark:to-gray-800 border-brand-200 dark:border-brand-800/50 max-w-2xl w-full shadow-xl">
        <CardContent className="text-center">
          <h3 className="text-xl font-bold text-brand-500 dark:text-white ">
            No Completed Value Maps Yet
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-md mx-auto text-sm">
            Start your journey by understanding your customers and creating your first value proposition.
          </p>

          <div className="grid md:grid-cols-2 gap-4 mb-6">
            <motion.div
              whileHover={{ scale: 1.02 }}
              className="bg-white dark:bg-gray-800/50 p-6 rounded-lg border border-brand-200 dark:border-brand-700/50 text-left"
            >
              <div className="bg-brand-100 dark:bg-brand-900/30 rounded-lg p-3 w-12 h-12 flex items-center justify-center mb-4">
                <Target className="h-6 w-6 text-brand-600 dark:text-brand-400" />
              </div>
              <h4 className="font-semibold text-brand-500 dark:text-white mb-2">
                Customer Understanding
              </h4>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Deep dive into customer insights and build comprehensive personas
              </p>
              <Button
                onClick={onGoToCustomerUnderstanding}
                variant="outline"
                className="w-full border-brand-500 text-brand-600 hover:bg-brand-50 dark:border-brand-600 dark:text-brand-400 dark:hover:bg-brand-900/20"
              >
                Explore Customers
              </Button>
            </motion.div>


            {user?.can_skip_module && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.1 }}
                className="group"
              >
                <Card
                  className="h-auto p-4 bg-brand-25 dark:from-brand-900/20 dark:to-brand-800/20 dark:bg-gray-900/20 hover:bg-gray-900/20 border-2 border-dashed border-brand-300 dark:border-brand-600 rounded-xl hover:border-brand-500 dark:hover:border-brand-400 hover:shadow-lg transition-all duration-200 cursor-pointer overflow-hidden relative h-full flex items-center justify-center"
                  onClick={onOpenCreateModal}
                >
                  <div className="text-center space-y-4">
                    {/* Icon */}
                    <div className="flex justify-center">
                      <div className="w-16 h-16 rounded-full border-2 border-brand-500 dark:border-brand-400 bg-brand-50 dark:bg-brand-900/10 flex items-center justify-center group-hover:scale-110 transition-transform duration-200">
                        <Plus className="h-8 w-8 text-brand-500 dark:text-brand-400" />
                      </div>
                    </div>

                    {/* Text */}
                    <div className="space-y-2">
                      <h3 className="text-lg font-semibold text-brand-500 dark:text-brand-300">
                        Create New Project
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400 max-w-xs mx-auto">
                        Start a new value proposition project from scratch
                      </p>
                    </div>

                    {/* Button - appears on hover */}
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                      <Button
                        className="bg-brand-500 hover:bg-brand-600 text-white"
                        size="sm"
                      >
                        Create Project
                      </Button>
                    </div>
                  </div>
                </Card>
              </motion.div>
            )}

            <CreateProjectModal
              isOpen={isCreateModalOpen}
              onClose={onCloseCreateModal}
              onProjectCreated={onProjectCreated}
            />
          </div>

          <div className="flex items-center justify-center gap-2 text-sm text-gray-500 dark:text-gray-400">
            <TrendingUp className="h-4 w-4" />
            <span>Build validated value propositions that resonate with your customers</span>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
});

ProjectsEmpty.displayName = 'ProjectsEmpty';
