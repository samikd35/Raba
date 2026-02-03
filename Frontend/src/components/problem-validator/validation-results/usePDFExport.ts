"use client";

import { useState, useCallback } from "react";
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';
import { PDFExportState } from "./types";

export const usePDFExport = () => {
    const [exportState, setExportState] = useState<PDFExportState>({
        isExporting: false,
        progress: 0,
        error: null
    });

    const exportToPdf = useCallback(async (element: HTMLElement, filename: string) => {
        if (!element) {
            setExportState({ isExporting: false, progress: 0, error: 'No element to export' });
            return false;
        }

        try {
            setExportState({ isExporting: true, progress: 0, error: null });

            // Hide export-exclude elements
            const elementsToHide = element.querySelectorAll('.export-exclude');
            const originalStyles: { element: Element; display: string }[] = [];

            elementsToHide.forEach(el => {
                originalStyles.push({ element: el, display: (el as HTMLElement).style.display });
                (el as HTMLElement).style.display = 'none';
            });

            setExportState(prev => ({ ...prev, progress: 30 }));

            // Create canvas with better quality but reasonable limits
            const canvas = await html2canvas(element, {
                scale: 1.5,
                useCORS: true,
                logging: false,
                scrollY: -window.scrollY,
                removeContainer: true,
                onclone: (clonedDoc) => {
                    const clonedElement = clonedDoc.getElementById(element.id);
                    if (clonedElement) {
                        clonedElement.style.width = '210mm';
                        clonedElement.style.padding = '20mm';
                    }
                }
            });

            setExportState(prev => ({ ...prev, progress: 70 }));

            // Create PDF
            const pdf = new jsPDF({
                orientation: 'portrait',
                unit: 'mm',
                format: 'a4'
            });

            const imgData = canvas.toDataURL('image/png', 0.9);
            const pdfWidth = pdf.internal.pageSize.getWidth();
            const pdfHeight = (canvas.height * pdfWidth) / canvas.width;

            pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);

            setExportState(prev => ({ ...prev, progress: 90 }));

            // Save PDF
            pdf.save(`${filename}.pdf`);

            // Restore original styles
            elementsToHide.forEach((el, index) => {
                (el as HTMLElement).style.display = originalStyles[index]?.display || '';
            });

            // Clean up canvas
            if (canvas.parentNode) {
                canvas.parentNode.removeChild(canvas);
            }

            setExportState({ isExporting: false, progress: 100, error: null });

            return true;
        } catch (error) {
            console.error('PDF export error:', error);
            const errorMessage = error instanceof Error ? error.message : 'Export failed';
            setExportState({ isExporting: false, progress: 0, error: errorMessage });
            return false;
        }
    }, []);

    return { exportState, exportToPdf };
};
