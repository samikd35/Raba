"use client";

import React, { use, useRef, useState, useCallback } from "react";
import PageBreadcrumb from "@/components/common/module 3/sub-module-1/PageBreadCrumb";
import { BMCLoadingState } from "@/components/bmc/BMCLoadingState";
import { BMCErrorState } from "@/components/bmc/BMCErrorState";
import { BMCHeader } from "@/components/bmc/BMCHeader";
import { BMCFullscreenHeader } from "@/components/bmc/BMCFullscreenHeader";
import { BMCCanvas } from "@/components/bmc/BMCCanvas";
import { BMCEditModal } from "@/components/bmc/BMCEditModal";
import { BMCAddItemModal } from "@/components/bmc/BMCAddItemModal";
import { BMCDeleteConfirmModal } from "@/components/bmc/BMCDeleteConfirmModal";
import { useBMC, BMCBlockName, BMCEditItem } from "@/hooks/useBMC";
import { motion } from "framer-motion";
import domtoimage from 'dom-to-image';
import html2canvas from "html2canvas";
import toast from "react-hot-toast";

// All interfaces moved to /src/types/bmc.ts

export default function BMCPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;

  const {
    bmcData,
    projectName,
    loading,
    error,
    isGenerating,
    isContinuing,
    generateBMC,
    handleBackToProject,
    handleRetry,
    handleContinue,
    isFullscreen,
    toggleFullscreen,
    isAccessError,
    // Edit mode state and actions
    isEditMode,
    isEditing,
    isAdding,
    isDeleting,
    editingBlock,
    editingItem,
    addingToBlock,
    deletingItem,
    toggleEditMode,
    startEditItem,
    cancelEdit,
    saveEditItem,
    startAddItem,
    cancelAdd,
    addNewItem,
    startDeleteItem,
    cancelDelete,
    confirmDeleteItem
  } = useBMC(projectId);

  // Ref for the BMC canvas container
  const bmcCanvasRef = useRef<HTMLDivElement>(null);
  
  // Screenshot state
  const [isDownloading, setIsDownloading] = useState(false);

  // Enhanced screenshot function with improved UX and reliability
  const captureScreenshot = useCallback(async () => {
    if (!bmcCanvasRef.current || isDownloading) return;

    setIsDownloading(true);
    let loadingToast: string | undefined;

    try {
      loadingToast = toast.loading('Preparing to capture screenshot...', {
        duration: 15000
      });

      // Wait for any animations and transitions to complete
      await new Promise(resolve => setTimeout(resolve, 500));

      const element = bmcCanvasRef.current;
      
      // Get current element dimensions without modifying styles
      const rect = element.getBoundingClientRect();
      const computedStyle = window.getComputedStyle(element);
      
      // Calculate natural dimensions based on current layout
      const naturalWidth = Math.max(element.scrollWidth, element.offsetWidth);
      const naturalHeight = Math.max(element.scrollHeight, element.offsetHeight);
      
      // Use device pixel ratio for high-quality capture
      const pixelRatio = window.devicePixelRatio || 1;
      const captureWidth = naturalWidth;
      const captureHeight = naturalHeight;

      console.log(`📸 Capturing BMC canvas - Natural dimensions: ${naturalWidth}x${naturalHeight}, Pixel ratio: ${pixelRatio}`);

      // Try dom-to-image first with optimized configuration
      try {
        const dataUrl = await domtoimage.toPng(element, {
          quality: 1.0,
          bgcolor: '#ffffff',
          width: captureWidth,
          height: captureHeight,
          style: {
            // Preserve existing layout without aggressive modifications
            margin: '0',
            padding: computedStyle.padding,
            boxSizing: 'border-box',
            // Don't override transform - let it maintain current state
            overflow: 'visible'
          },
          filter: (node: any) => {
            // Enhanced filtering for better capture
            if (node.nodeType === Node.ELEMENT_NODE) {
              const element = node as Element;
              const classList = element.classList;
              
              // Skip problematic elements that might cause distortion
              if (classList?.contains('no-screenshot') || 
                  classList?.contains('animate-spin') ||
                  classList?.contains('animate-pulse') ||
                  classList?.contains('animate-bounce') ||
                  element.tagName === 'SCRIPT' ||
                  element.tagName === 'STYLE') {
                return false;
              }
            }
            return true;
          },
          cacheBust: true,
          // Use higher pixel ratio for better quality
          pixelRatio: Math.min(pixelRatio, 4) // Cap at 4x to avoid memory issues
        });
        
        // Create and trigger download
        const link = document.createElement('a');
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
        link.download = `BMC-${timestamp}.png`;
        link.href = dataUrl;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    
        toast.dismiss(loadingToast);
        toast.success('🎉 BMC screenshot captured successfully!', {
          duration: 4000
        });
        
        console.log('✅ Screenshot captured successfully using dom-to-image');
        
      } catch (domToImageError) {
        console.warn('⚠️ dom-to-image failed, trying html2canvas:', domToImageError);
        
        // Update progress for fallback method
        toast.dismiss(loadingToast);
        loadingToast = toast.loading('Trying alternative capture method...', {
          duration: 15000
        });
        
        // Fallback to html2canvas with conservative configuration
        const canvas = await html2canvas(element, {
          allowTaint: true,
          useCORS: true,
          scale: Math.min(pixelRatio, 2), // Use device pixel ratio but cap at 2x
          backgroundColor: '#ffffff',
          width: captureWidth,
          height: captureHeight,
          scrollX: 0,
          scrollY: 0,
          // Don't override window dimensions - use natural size
          logging: false,
          removeContainer: true,
          // Preserve original element positioning
          x: 0,
          y: 0,
          ignoreElements: (element) => {
            // Enhanced element filtering to prevent distortion
            return element.classList?.contains('no-screenshot') || 
                   element.classList?.contains('animate-spin') ||
                   element.classList?.contains('animate-pulse') ||
                   element.classList?.contains('animate-bounce') ||
                   element.tagName === 'SCRIPT' ||
                   element.tagName === 'STYLE' || false;
          },
          onclone: (clonedDoc, element) => {
            // Ensure cloned element maintains proper styling
            const clonedElement = clonedDoc.querySelector('[data-screenshot-target]') || element;
            if (clonedElement && clonedElement instanceof HTMLElement) {
              // Reset any transforms that might cause distortion
              clonedElement.style.transform = 'none';
              clonedElement.style.transformOrigin = 'top left';
            }
          }
        });
        
        // Convert canvas to blob and download
        return new Promise<void>((resolve, reject) => {
          canvas.toBlob((blob) => {
            if (blob) {
              const url = URL.createObjectURL(blob);
              const link = document.createElement('a');
              const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
              link.download = `BMC-${timestamp}.png`;
              link.href = url;
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
              URL.revokeObjectURL(url);
              
              toast.dismiss(loadingToast);
              toast.success('🎉 BMC screenshot captured successfully!', {
                duration: 4000
              });
              
              console.log('✅ Screenshot captured successfully using html2canvas');
              resolve();
            } else {
              reject(new Error('Failed to create blob from canvas'));
            }
          }, 'image/png', 1); // Slightly compress for better file size
        });
      }

    } catch (error) {
      console.error('❌ Screenshot capture failed:', error);
      
      if (loadingToast) {
        toast.dismiss(loadingToast);
      }
      
      // Provide helpful error messages based on error type
      let errorMessage = 'Failed to capture screenshot. ';
      
      if (error instanceof Error) {
        if (error.message.includes('canvas') || error.message.includes('dom-to-image')) {
          errorMessage += 'Layout rendering issue detected. Try refreshing the page and capturing again.';
        } else if (error.message.includes('network') || error.message.includes('cors')) {
          errorMessage += 'Network issue detected. Please check your connection and try again.';
        } else if (error.message.includes('memory') || error.message.includes('size')) {
          errorMessage += 'Content too large. Try capturing in fullscreen mode for better results.';
        } else {
          errorMessage += 'Please try refreshing the page or contact support if the issue persists.';
        }
      } else {
        errorMessage += 'Please try refreshing the page and try again.';
      }
      
      toast.error(errorMessage, {
        duration: 6000
      });
      
    } finally {
      setIsDownloading(false);
      if (loadingToast) {
        toast.dismiss(loadingToast);
      }
    }
  }, [projectId, isDownloading]);

  // Loading state
  if (loading) {
    return <BMCLoadingState />;
  }

  // Error state
  if (error) {
    return (
      <BMCErrorState
        error={error}
        onRetry={handleRetry}
        onGenerate={generateBMC}
        isGenerating={isGenerating}
        isAccessError={isAccessError}
      />
    );
  }

  // Data loading state (when loading is false but no data yet)
  if (!bmcData) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-8 dark:border-gray-800 dark:bg-white/[0.03]">
        <div className="flex flex-col items-center justify-center py-12 space-y-4">
          <div className="w-12 h-12 border-4 border-brand-200 border-t-brand-500 rounded-full animate-spin"></div>
          <div className="text-center">
            <p className="text-lg font-medium text-gray-600 dark:text-white">Loading Business Model Canvas</p>
            <p className="text-sm text-muted-foreground">Preparing your canvas data...</p>
          </div>
          
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageBreadcrumb pageTitle="Business Model Canvas" />
      <div className={`${isFullscreen ? 'fixed inset-0 z-50 bg-white dark:bg-gray-900 p-4 overflow-auto' : ' '}`}>
        
        {/* Fullscreen header */}
        {isFullscreen && (
          <div>
            <BMCFullscreenHeader
              onBack={handleBackToProject}
              onGenerate={generateBMC}
              onContinue={handleContinue}
              onToggleFullscreen={toggleFullscreen}
              isGenerating={isGenerating}
              isContinuing={isContinuing}
              projectName={projectName}
              isEditMode={isEditMode}
              onToggleEditMode={toggleEditMode}
              isEditing={isEditing || isAdding || isDeleting}
            />

            {/* Full Screen Canvas Container */}
            <motion.div
              ref={bmcCanvasRef}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.2 }}
              className="mt-4"
            >
              {bmcData && (
                <BMCCanvas 
                  bmcData={bmcData} 
                  fullscreen={true}
                  isEditMode={isEditMode}
                  onEditItem={startEditItem}
                  onDeleteItem={startDeleteItem}
                  onAddItem={startAddItem}
                />
              )}
            </motion.div>

            {/* Edit Modal */}
            <BMCEditModal
              isOpen={!!editingItem}
              onClose={cancelEdit}
              onSave={saveEditItem}
              blockName={editingBlock}
              item={editingItem}
              isLoading={isEditing}
            />

            {/* Add Item Modal */}
            <BMCAddItemModal
              isOpen={!!addingToBlock}
              onClose={cancelAdd}
              onAdd={addNewItem}
              blockName={addingToBlock}
              isLoading={isAdding}
            />

            {/* Delete Confirmation Modal */}
            <BMCDeleteConfirmModal
              isOpen={!!deletingItem}
              onClose={cancelDelete}
              onConfirm={confirmDeleteItem}
              itemName={deletingItem?.itemName || ''}
              blockName={deletingItem?.blockName || null}
              isLoading={isDeleting}
            />
          </div>
        )}

        {/* Regular view */}
        {!isFullscreen && (
          <>
            <BMCHeader
              onBack={handleBackToProject}
              onGenerate={generateBMC}
              onContinue={handleContinue}
              isGenerating={isGenerating}
              isContinuing={isContinuing}
              isFullscreen={isFullscreen}
              onToggleFullscreen={toggleFullscreen}
              onCaptureScreenshot={captureScreenshot}
              isDownloading={isDownloading}
            />

            {/* Regular Canvas Container */}
            <motion.div
              ref={bmcCanvasRef}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              {bmcData && <BMCCanvas bmcData={bmcData} compact={true} />}
            </motion.div>
          </>
        )}
      </div>
    </div>
  );
}
