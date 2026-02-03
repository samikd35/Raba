"use client";

import PageBreadcrumb from "@/components/common/module 2/sub-module-2/PageBreadCrumb";
import FeatureVideoOverlay from "@/components/feature-videos/FeatureVideoOverlay";
import { FEATURE_IDS, getFeatureVideoConfig } from "@/lib/featureVideos";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { authService } from "@/services/authService";
import domtoimage from 'dom-to-image';
import { 
  RefreshCw, 
  ChevronRight, 
  TrendingUp,
  Loader2,
  AlertCircle,
  Package,
  Heart,
  Briefcase,
  Frown,
  Smile,
  Maximize2,
  Minimize2,
  UserCircle2,
  Edit,
  Camera
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState, useCallback, useRef } from "react";
import toast from "react-hot-toast";
import { motion, AnimatePresence } from "framer-motion";
import html2canvas from "html2canvas";

// Types for the VPC data
interface VPCItem {
  id: string;
  label: string;
  position: number;
  persona_name: string;
}

interface VPCSection {
  section_name: string;
  items: VPCItem[];
  max_items: number;
  position: string;
}

interface CustomerProfile {
  jobs: VPCSection;
  pains: VPCSection;
  gains: VPCSection;
}

interface ValueMap {
  status: string;
  message: string;
}

interface TemplateData {
  template_id: string;
  layout: string;
  customer_profile: CustomerProfile;
  value_map: ValueMap;
}

interface VPCResponse {
  success: boolean;
  vpc_v2: Record<string, {
    status: string;
    version: string;
    persona_id: string;
    updated_at: string;
    persona_name: string;
    customer_profile: {
      gains: Array<{ id: string; label: string; description?: string; text?: string }>;
      pains: Array<{ id: string; label: string; description?: string; text?: string }>;
      jobs_to_be_done: Array<{ id: string; label: string; description?: string; text?: string }>;
    };
    value_map_candidates?: {
      gain_creators_candidates?: Array<{ id: string; label: string }>;
      pain_relievers_candidates?: Array<{ id: string; label: string }>;
      products_services_candidates?: Array<{ id: string; label: string }>;
    };
    value_map_selections?: {
      gain_creators?: Array<{ id: string; label: string }>;
      pain_relievers?: Array<{ id: string; label: string }>;
      products_services?: Array<{ id: string; label: string }>;
    };
  }>;
  message: string;
}

// Glassmorphic section overlay label component
const SectionOverlayLabel = ({ text, className = "" }: { text: string; className?: string }) => (
  <div 
    className={`inline-flex items-center px-3 py-1 rounded-full bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-gray-200/50 dark:border-gray-600/50 shadow-sm ${className}`}
  >
    <span className="text-sm font-bold text-gray-600 dark:text-gray-300 tracking-wide">
      {text}
    </span>
  </div>
);

// Helper function to create SVG path for pie segments
const createSegmentPath = (index: number, outerRadius: number, innerRadius: number): string => {
  const startAngle = (index * 120 - 90) * (Math.PI / 180);
  const endAngle = ((index + 1) * 120 - 90) * (Math.PI / 180);
  
  const x1 = Math.cos(startAngle) * outerRadius;
  const y1 = Math.sin(startAngle) * outerRadius;
  const x2 = Math.cos(endAngle) * outerRadius;
  const y2 = Math.sin(endAngle) * outerRadius;
  
  const x3 = Math.cos(endAngle) * innerRadius;
  const y3 = Math.sin(endAngle) * innerRadius;
  const x4 = Math.cos(startAngle) * innerRadius;
  const y4 = Math.sin(startAngle) * innerRadius;
  
  const largeArcFlag = (endAngle - startAngle) <= Math.PI ? 0 : 1;
  
  return [
    `M ${x1} ${y1}`,
    `A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${x2} ${y2}`,
    `L ${x3} ${y3}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${x4} ${y4}`,
    'Z'
  ].join(' ');
};

// Internal mapping helpers to keep UI types unchanged
const mapVPCV2ToTemplateData = (resp: VPCResponse): TemplateData => {
  const personas = Object.values(resp.vpc_v2 || {});

  // Aggregate items from all personas into the existing section shape
  const jobsItems: VPCItem[] = [];
  const painsItems: VPCItem[] = [];
  const gainsItems: VPCItem[] = [];

  personas.forEach((p) => {
    const pid = p.persona_id || p.persona_name || "P1";
    p.customer_profile?.jobs_to_be_done?.forEach((item, idx) => {
      jobsItems.push({ id: item.id, label: item.label || item.id, position: idx, persona_name: pid });
    });
    p.customer_profile?.pains?.forEach((item, idx) => {
      painsItems.push({ id: item.id, label: item.label || item.id, position: idx, persona_name: pid });
    });
    p.customer_profile?.gains?.forEach((item, idx) => {
      gainsItems.push({ id: item.id, label: item.label || item.id, position: idx, persona_name: pid });
    });
  });

  const customer_profile: CustomerProfile = {
    jobs: { section_name: 'jobs', items: jobsItems, max_items: 999, position: 'right' },
    pains: { section_name: 'pains', items: painsItems, max_items: 999, position: 'right' },
    gains: { section_name: 'gains', items: gainsItems, max_items: 999, position: 'right' },
  };

  // Map value map selections (if available) for hover modal usage
  const vmProducts: VPCItem[] = [];
  const vmPainRelievers: VPCItem[] = [];
  const vmGainCreators: VPCItem[] = [];

  personas.forEach((p) => {
    const pid = p.persona_id || p.persona_name || 'P1';
    const sel = p.value_map_selections || {};
    sel.products_services?.forEach((item, idx) => {
      vmProducts.push({ id: item.id, label: item.label || item.id, position: idx, persona_name: pid });
    });
    sel.pain_relievers?.forEach((item, idx) => {
      vmPainRelievers.push({ id: item.id, label: item.label || item.id, position: idx, persona_name: pid });
    });
    sel.gain_creators?.forEach((item, idx) => {
      vmGainCreators.push({ id: item.id, label: item.label || item.id, position: idx, persona_name: pid });
    });
  });

  const value_map: ValueMap = { status: (vmProducts.length + vmPainRelievers.length + vmGainCreators.length) > 0 ? 'ready' : 'pending', message: resp.message || '' };

  const templateData: TemplateData = {
    template_id: 'vpc-v2',
    layout: 'v2-default',
    customer_profile,
    value_map,
  };

  // Attach value map items non-destructively for UI use
  (templateData as any).value_map_items = {
    products_services: vmProducts,
    pain_relievers: vmPainRelievers,
    gain_creators: vmGainCreators,
  };

  return templateData;
};

export default function ValuePropositionCanvasPage() {
  const params = useParams();
  const projectId = params.id as string;
  const router = useRouter();
  
  // const featureConfig = getFeatureVideoConfig(FEATURE_IDS.VPC_V2);
  
  const [vpcData, setVpcData] = useState<TemplateData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredValueMapSection, setHoveredValueMapSection] = useState<string | null>(null);
  const [hoveredCustomerSection, setHoveredCustomerSection] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
  const [availablePersonas, setAvailablePersonas] = useState<string[]>([]);
  const [personaMapping, setPersonaMapping] = useState<Record<string, string>>({});
  const [isNavigating, setIsNavigating] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  
  // Ref for the VPC canvas container
  const vpcCanvasRef = useRef<HTMLDivElement>(null);

  // Toggle fullscreen mode
  const toggleFullscreen = useCallback(() => {
    setIsFullscreen(prev => !prev);
  }, []);

// Enhanced screenshot function with improved UX and reliability
const captureScreenshot = useCallback(async () => {
  if (!vpcCanvasRef.current || isDownloading) return;

  setIsDownloading(true);
  let loadingToast: string | undefined;

  try {
    loadingToast = toast.loading('Preparing to capture screenshot...', {
      duration: 15000
    });

    // Wait for any animations and transitions to complete
    await new Promise(resolve => setTimeout(resolve, 500));

    const element = vpcCanvasRef.current;
    
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

    console.log(`📸 Capturing VPC canvas - Natural dimensions: ${naturalWidth}x${naturalHeight}, Pixel ratio: ${pixelRatio}`);

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
        filter: (node) => {
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
        pixelRatio: Math.min(pixelRatio, 4) // Cap at 2x to avoid memory issues
      });
      
      // Create and trigger download
      const link = document.createElement('a');
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
      const personaLabel = selectedPersona ? getPersonaDisplayName(selectedPersona).replace(/\s+/g, '-') : 'all-personas';
      link.download = `VPC-${personaLabel}-${timestamp}.png`;
      link.href = dataUrl;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
  
      toast.dismiss(loadingToast);
      toast.success('🎉 VPC screenshot captured successfully!', {
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
            const personaLabel = selectedPersona ? getPersonaDisplayName(selectedPersona).replace(/\s+/g, '-') : 'all-personas';
            link.download = `VPC-${personaLabel}-${timestamp}.png`;
            link.href = url;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            
            toast.dismiss(loadingToast);
            toast.success('🎉 VPC screenshot captured successfully!', {
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
}, [projectId, selectedPersona, isDownloading]);

  // Fetch VPC template data
  const fetchVPCData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const token = authService.getCurrentToken();
      if (!token) {
        toast.error("Authentication required. Please sign in again.");
        router.push("/signin");
        return;
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL ;
      const response = await fetch(`${apiUrl}/api/v2/vmp/projects/${projectId}/vpc-v2`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          toast.error("Session expired. Please sign in again.");
          router.push("/signin");
          return;
        }
        if (response.status === 404) {
          // Handle 404 - VPC data not found, but don't treat as error
          setVpcData(null);
          setError('vpc_not_found');
          return;
        }
        throw new Error(`Failed to fetch VPC data: ${response.status}`);
      }

      const data: VPCResponse = await response.json();
      if (data.success && data.vpc_v2) {
        const mapped = mapVPCV2ToTemplateData(data);
        setVpcData(mapped);

        // Extract persona IDs and names from the vpc_v2 structure
        const personaIds: string[] = [];
        const personaNameMapping: Record<string, string> = {};
        
        Object.values(data.vpc_v2).forEach(p => {
          const personaId = p.persona_id;
          const personaName = p.persona_name || personaId;
          personaIds.push(personaId);
          personaNameMapping[personaId] = personaName;
        });
        
        const sortedPersonas = personaIds.sort();
        setAvailablePersonas(sortedPersonas);
        setPersonaMapping(personaNameMapping);

        // Set first persona as default if available
        if (sortedPersonas.length > 0 && !selectedPersona) {
          setSelectedPersona(sortedPersonas[0]);
        }

        if (process.env.NODE_ENV === 'development') {
          console.log('📊 VPC v2 Data loaded with personas:', sortedPersonas);
          console.log('📊 Persona mapping:', personaNameMapping);
        }
      } else {
        throw new Error(data.message || 'Failed to load VPC data');
      }
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Error fetching VPC data:', err);
      }
      const errorMessage = err instanceof Error ? err.message : 'Failed to load VPC data';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [projectId, router, selectedPersona]);

  // Generate VPC data function
  const generateVPCData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const token = authService.getCurrentToken();
      if (!token) {
        toast.error("Authentication required. Please sign in again.");
        router.push("/signin");
        return;
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL ;
      const response = await fetch(`${apiUrl}/api/v2/vmp/projects/${projectId}/vpc/generate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          toast.error("Session expired. Please sign in again.");
          router.push("/signin");
          return;
        }
        throw new Error(`Failed to generate VPC data: ${response.status}`);
      }

      const data = await response.json();
      if (data.success) {
        toast.success('VPC data generated successfully!');
        // Refresh the data
        fetchVPCData();
      } else {
        throw new Error(data.message || 'Failed to generate VPC data');
      }
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Error generating VPC data:', err);
      }
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate VPC data';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [projectId, router, fetchVPCData]);

  useEffect(() => {
    if (projectId) {
      fetchVPCData();
    }
  }, [projectId, fetchVPCData]);

  // Get section data for display with persona filtering
  const getSectionData = (sectionType: string, personaId: string | null = selectedPersona) => {
    const data = vpcData?.customer_profile[sectionType as keyof CustomerProfile];
    const items = data?.items || [];
    
    // Filter items by selected persona if a persona is selected
    const filteredItems = personaId 
      ? items.filter(item => item.persona_name === personaId)
      : items;

    return {
      items: filteredItems,
      count: filteredItems.length,
      maxItems: data?.max_items || 0,
      allItems: items // Keep all items for "All Personas" view
    };
  };

  // Get display name for persona
  const getPersonaDisplayName = (personaId: string | null) => {
    if (!personaId) return "All Personas";
    if (personaId === "all") return "All Personas";
    
    // Use the persona mapping to get the actual name
    return personaMapping[personaId] || personaId;
  };

  // Helper: get value map items by section id and persona
  const getValueMapItems = (sectionId: 'products' | 'pain_relievers' | 'gain_creators', personaId: string | null = selectedPersona) => {
    const vm = (vpcData as any)?.value_map_items || {};
    const key = sectionId === 'products' ? 'products_services' : sectionId;
    const items: VPCItem[] = vm[key] || [];
    return personaId ? items.filter(i => i.persona_name === personaId) : items;
  };

  // Value Map sections for the left side bento grid
  const valueMapSections = [
    {
      id: 'products',
      title: 'PRODUCTS & SERVICES',
      subtitle: 'All products and services your value proposition is built around',
      icon: Package,
      color: '#10B981', // Green
      bgColor: 'bg-green-50 dark:bg-green-900/10',
      borderColor: 'border-green-200 dark:border-green-800',
      hoverColor: 'hover:bg-green-100 dark:hover:bg-green-900/20',
      iconColor: 'text-green-600 dark:text-green-400',
      textColor: 'text-green-700 dark:text-green-300',
      data: { items: [], count: 0, maxItems: 5 }
    },
    {
      id: 'pain_relievers',
      title: 'PAIN RELIEVERS',
      subtitle: 'How your products alleviate customer pains',
      icon: Heart,
      color: '#EF4444', // Red
      bgColor: 'bg-red-50 dark:bg-red-900/10',
      borderColor: 'border-red-200 dark:border-red-800',
      hoverColor: 'hover:bg-red-100 dark:hover:bg-red-900/20',
      iconColor: 'text-red-600 dark:text-red-400',
      textColor: 'text-red-700 dark:text-red-300',
      data: { items: [], count: 0, maxItems: 5 }
    },
    {
      id: 'gain_creators',
      title: 'GAIN CREATORS',
      subtitle: 'How your product or service creates customer gains',
      icon: TrendingUp,
      color: '#3B82F6', // Blue
      bgColor: 'bg-blue-50 dark:bg-blue-900/10',
      borderColor: 'border-blue-200 dark:border-blue-800',
      hoverColor: 'hover:bg-blue-100 dark:hover:bg-blue-900/20',
      iconColor: 'text-blue-600 dark:text-blue-400',
      textColor: 'text-blue-700 dark:text-blue-300',
      data: { items: [], count: 0, maxItems: 5 }
    }
  ];

  // Customer Profile segments for the pie chart
  const segments = [
    {
      id: 'jobs',
      title: 'Customer Jobs',
      subtitle: getSectionData('jobs').items.length > 0 
        ? getSectionData('jobs').items.map(item => item.label).join(' • ')
        : 'No jobs identified yet',
      icon: Briefcase,
      color: '#10B981', // green
      borderColor: 'border-green-200 dark:border-green-800',
      fillColor: '#10B981',
      data: getSectionData('jobs')
    },
    {
      id: 'pains',
      title: 'PAINS',
      subtitle: getSectionData('pains').items.length > 0 
        ? getSectionData('pains').items.map(item => item.label).join(' • ')
        : 'No pains identified yet',
      icon: Frown,
      color: '#EF4444', // red
      borderColor: 'border-red-200 dark:border-red-800',
      fillColor: '#EF4444',
      data: getSectionData('pains')
    },
    {
      id: 'gains',
      title: 'GAINS',
      subtitle: getSectionData('gains').items.length > 0 
        ? getSectionData('gains').items.map(item => item.label).join(' • ')
        : 'No gains identified yet',
      icon: Smile,
      color: '#3B82F6', // blue
      borderColor: 'border-blue-200 dark:border-blue-800',
      fillColor: '#3B82F6',
      data: getSectionData('gains')
    }
  ];

  // Animation variants
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, scale: 0.8 },
    visible: { 
      opacity: 1, 
      scale: 1,
      transition: {
        type: "spring" as const,
        stiffness: 100,
        damping: 15
      }
    }
  };

  // Persona selector component
  const PersonaSelector = ({ compact = false }: { compact?: boolean }) => {
    if (availablePersonas.length <= 1) return null;

    return (
      <div className={`flex justify-center ${compact ? 'mb-0' : 'mb-6'} w-full max-w-full`}>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-1 shadow-sm max-w-full overflow-hidden">
          <Tabs 
            value={selectedPersona || "all"} 
            onValueChange={(value) => setSelectedPersona(value === "all" ? null : value)}
            className="w-full"
          >
            <TabsList className="flex w-full overflow-x-auto scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600">
              {availablePersonas.map((personaId, index) => (
                <TabsTrigger 
                  key={personaId} 
                  value={personaId}
                  title={getPersonaDisplayName(personaId)}
                  className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 text-brand-500 min-w-0 flex-shrink-0"
                >
                  <UserCircle2 className="w-4 h-4 flex-shrink-0" />
                  <span className="truncate max-w-[80px] sm:max-w-[120px] md:max-w-[160px]">
                    {getPersonaDisplayName(personaId)}
                  </span>
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div>
        <PageBreadcrumb pageTitle="Value Proposition Canvas" />
        <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-700 dark:bg-gray-900 xl:px-10">
         <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col items-center justify-center py-12"
          >
            <Loader2 className="w-8 h-8 animate-spin text-gray-600 dark:text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-200 mb-2">
              Loading Value Proposition Canvas...
            </h3>
            <p className="text-gray-600 dark:text-gray-400 text-center max-w-md text-md">
              Preparing your interactive canvas with customer profiles and value propositions.
            </p>
          </motion.div>
        </div>
      </div>
    );
  }

  if (error) {
    if (error === 'vpc_not_found') {
      return (
        <div>
          <PageBreadcrumb pageTitle="Value Proposition Canvas" />
          <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-700 dark:bg-gray-900 xl:px-10">
            <div className="flex flex-col items-center justify-center py-16">
              <div className="p-4 rounded-full bg-yellow-100 dark:bg-yellow-900/20 mb-4">
                <AlertCircle className="w-8 h-8 text-yellow-600 dark:text-yellow-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                No Value Proposition Canvas Found
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6 text-center max-w-md">
                It seems that no Value Proposition Canvas has been created for this project yet.
              </p>
              <div className="flex gap-3">
                <Button
                  onClick={generateVPCData}
                  className="bg-brand-600 hover:bg-brand-700 text-white"
                >
                  <Package className="w-4 h-4 mr-2" />
                  Generate VPC Data
                </Button>
                <Button
                  onClick={() => router.push(`/team-workspace/projects/${projectId}`)}
                  variant="outline"
                >
                  Back to Project
                </Button>
              </div>
            </div>
          </div>
        </div>
      );
    } else {
      return (
        <div>
          <PageBreadcrumb pageTitle="Value Proposition Canvas" />
          <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-700 dark:bg-gray-900 xl:px-10">
            <div className="flex flex-col items-center justify-center py-16">
              <div className="p-4 rounded-full bg-red-100 dark:bg-red-900/20 mb-4">
                <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Failed to Load Canvas
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6 text-center max-w-md">
                {error}
              </p>
              <div className="flex gap-3">
                <Button
                  onClick={fetchVPCData}
                  className="bg-brand-600 hover:bg-brand-700 text-white"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Try Again
                </Button>
                <Button
                  onClick={() => router.push(`/team-workspace/projects/${projectId}`)}
                  variant="outline"
                >
                  Back to Project
                </Button>
              </div>
            </div>
          </div>
        </div>
      );
    }
  }

  if (!vpcData) {
    return null;
  }

  return (
    <div>
      {/* <FeatureVideoOverlay
        featureId={FEATURE_IDS.VPC_V2}
        youtubeId={featureConfig.youtubeId}
        resourcesHref={featureConfig.resourcesHref}
        title={featureConfig.title}
      /> */}
      <PageBreadcrumb pageTitle="The Full Value Proposition Canvas"/>
      <div className={`${isFullscreen ? 'fixed inset-0 z-50 bg-white dark:bg-gray-900 p-4 overflow-auto' : ' rounded-2xl border border-gray-200 bg-white px-5 py-4 dark:border-gray-700 dark:bg-gray-900 xl:px-10'}`}>
        
        {/* Fullscreen header */}
        {isFullscreen && (
          <div>
            <div className="grid grid-cols-3 md:flex-row md:items-center md:justify-between gap-3 mb-1 pb-4 border-b border-gray-200 dark:border-gray-700">
              <div className="min-w-0">
                <h1 className="text-xl font-semibold text-gray-900 dark:text-white truncate">
                  Value Proposition Canvas - Fullscreen View
                </h1>
              </div>
              <div className="flex-1 flex justify-center">
                <PersonaSelector compact />
              </div>
              <div className="flex justify-end gap-2 items-center">
              <Button
    onClick={captureScreenshot}
    disabled={isDownloading}
    variant="outline"
    size="sm"
                    className="flex items-center gap-2 bg-blue-50 hover:bg-blue-100 text-blue-600 border-blue-200 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-blue-400 dark:border-gray-600"
  >
    {isDownloading ? (
      <>
        <Loader2 className="w-4 h-4 animate-spin" />
        <span className="hidden lg:inline">Capturing...</span>
      </>
    ) : (
      <>
        <Camera className="w-4 h-4" />
        <span className="hidden lg:inline">Save as Image</span>
      </>
    )}
  </Button>

                <Button
                  onClick={(e) => {
                    const btn = e.currentTarget as HTMLButtonElement;
                    btn.dataset.loading = 'true';
                    btn.setAttribute('aria-busy', 'true');
                    btn.disabled = true;
                    router.push(`/team-workspace/value-map/${projectId}`);
                  }}
                  data-loading="false"
                  variant="default"
                  aria-label="Edit value map"
                  size="sm"
                  className="relative flex items-center gap-2 bg-green-500 hover:bg-green-600 text-white dark:bg-green-600 dark:hover:bg-green-700 shadow-sm data-[loading=true]:opacity-80 data-[loading=true]:cursor-wait"
                >
                  <span className="inline-flex items-center gap-2 data-[loading=true]:hidden">
                    <Edit className="w-4 h-4" />
                    <span className="hidden lg:inline">Edit</span>
                  </span>
                  <span className="hidden items-center gap-2 data-[loading=true]:inline-flex">
                    <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" aria-hidden="true" />
                    <span className="hidden lg:inline">Opening...</span>
                  </span>
                </Button>

                <Button
                  onClick={toggleFullscreen}
                  variant="outline"
                  size="sm"
                  className="flex items-center gap-2"
                >
                  <Minimize2 className="w-4 h-4" />
                  <span className="hidden lg:inline">Exit Fullscreen</span>
                </Button>
              </div>
            </div>

            {/* Full Screen Canvas Container */}
            <motion.div
              ref={vpcCanvasRef}
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              className={`grid grid-cols-1 xl:grid-cols-2 gap-8 mx-auto ${isFullscreen ? 'max-w-7xl' : 'max-w-7xl'}`}
            >
              
              {/* Value Map Section - Bento Grid Design */}
              <motion.div variants={itemVariants} className="order-2 xl:order-1 flex items-center justify-center ">
                <div className="relative flex items-center justify-center p-2 rounded-2xl">
                  {/* Bento Grid Container */}
                  <div className="grid grid-cols-2 grid-rows-2 gap-2">
                    
                    {/* Products & Services - Large Top Section */}
                    <div className="col-span-2 row-span-2 rounded-t-2xl border-2 transition-all duration-300 group  bg-green-50 dark:bg-gray-800 border-green-200 dark:border-green-800">
                      <div className="p-8 pt-6 h-full flex flex-col items-center justify-center">
                        <div className="flex items-center gap-4 mb-2 justify-center">
                          <div className="p-2 rounded-lg bg-green-200 dark:bg-gray-700">
                            <Package className="w-4 h-4 text-green-600 dark:text-green-400" />
                          </div>
                          <div>
                            <h4 className="text-xl font-bold text-green-700 dark:text-green-300">
                              Products & Services
                            </h4>
                          </div>
                          <Badge className="bg-green-600 text-white">
                            {getValueMapItems('products').length}
                          </Badge>
                        </div>
                        
                        {/* Products & Services Items List */}
                        <div className="flex-1 overflow-y-auto">
                          {(() => {
                            const items = getValueMapItems('products');
                            if (items.length > 0) {
                              return (
                                <div className="space-y-2 flex flex-col items-center justify-center pb-4">
                                  {items.map((item, idx) => (
                                    <div key={item.id} className="px-3 py-1 bg-white dark:bg-gray-700 rounded-lg border border-green-200 dark:border-green-600 flex items-center justify-center w-[300px]">
                                      <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{item.label}</p>
                                      {availablePersonas.length > 1 && selectedPersona === null && (
                                        <Badge variant="outline" className="text-xs ml-2">{getPersonaDisplayName(item.persona_name)}</Badge>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              );
                            }
                            if (vpcData.value_map.status === 'pending') {
                              return (
                                <div className="text-center py-6">
                                  <div className="w-12 h-12 bg-yellow-100 dark:bg-yellow-900/20 rounded-full flex items-center justify-center mx-auto mb-3">
                                    <AlertCircle className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />
                                  </div>
                                  <h4 className="font-semibold text-gray-800 dark:text-white mb-2">
                                    Coming Soon
                                  </h4>
                                  <p className="text-gray-600 dark:text-gray-400 text-sm mb-3">
                                    {vpcData.value_map.message}
                                  </p>
                                </div>
                              );
                            }
                            return (
                              <div className="text-center py-6">
                                <div className="w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-3">
                                  <Package className="w-6 h-6 text-gray-400" />
                                </div>
                                <p className="text-gray-500 dark:text-gray-400 text-sm">
                                  No items available yet
                                </p>
                              </div>
                            );
                          })()}
                        </div>
                      </div>
                    </div>
                    {/* Value Map Label - positioned as overlay at top-left */}
                    <div className="absolute top-[39%] left-1/2 -translate-x-1/2 xl:top-[39%] xl:left-[42%] xl:translate-x-0 z-10">
                      <SectionOverlayLabel text="Value Map" />
                    </div>
                    {/* Pain Relievers - Bottom Left */}
                    <div className="col-span-1 row-span-1 rounded-bl-2xl border-2 transition-all duration-300 group p-4 bg-red-50 dark:bg-gray-800 border-red-200 dark:border-red-800">
                      <div className="p-4 h-full flex flex-col items-center justify-center">
                        <div className="flex items-center gap-4 mb-4 justify-center">
                          <div className="p-2 rounded-lg bg-red-200/60 dark:bg-gray-700">
                            <Heart className="w-4 h-4 text-red-600 dark:text-red-400" />
                          </div>
                          <div>
                            <h4 className="text-xl font-bold text-red-700 dark:text-red-300">
                              Pain Relievers
                            </h4>
                          </div>
                          <Badge className="bg-red-600 text-white">
                            {getValueMapItems('pain_relievers').length}
                          </Badge>
                        </div>
                        
                        {/* Pain Relievers Items List */}
                        <div>
                          {(() => {
                            const items = getValueMapItems('pain_relievers');
                            if (items.length > 0) {
                              return (
                                <div className="space-y-1">
                                  {items.map((item, idx) => (
                                    <div key={item.id} className="px-3 py-2 bg-white dark:bg-gray-700 rounded-lg border border-red-200 dark:border-red-600 flex items-center justify-center w-[250px]">
                                      <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{item.label}</p>
                                     
                                    </div>
                                  ))}
                                </div>
                              );
                            }
                            if (vpcData.value_map.status === 'pending') {
                              return (
                                <div className="text-center py-6">
                                  <div className="w-12 h-12 bg-yellow-100 dark:bg-yellow-900/20 rounded-full flex items-center justify-center mx-auto mb-3">
                                    <AlertCircle className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />
                                  </div>
                                  <h4 className="font-semibold text-gray-800 dark:text-white mb-2">
                                    Coming Soon
                                  </h4>
                                  <p className="text-gray-600 dark:text-gray-400 text-sm mb-3">
                                    {vpcData.value_map.message}
                                  </p>
                                </div>
                              );
                            }
                            return (
                              <div className="text-center py-6">
                                <div className="w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-3">
                                  <Heart className="w-6 h-6 text-gray-400" />
                                </div>
                                <p className="text-gray-500 dark:text-gray-400 text-sm">
                                  No items available yet
                                </p>
                              </div>
                            );
                          })()}
                        </div>
                      </div>
                    </div>

                    {/* Gain Creators - Bottom Right */}
                    <div className="col-span-1 row-span-1 rounded-br-2xl border-2 transition-all duration-300 group p-4 bg-blue-50 dark:bg-gray-800 border-blue-200 dark:border-blue-800">
                      <div className="p-4 h-full flex flex-col">
                        <div className="flex items-center gap-4 mb-4 justify-center">
                          <div className="p-2 rounded-lg bg-blue-200/60 dark:bg-gray-700">
                            <TrendingUp className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                          </div>
                          <div>
                            <h4 className="text-xl font-bold text-blue-700 dark:text-blue-300">
                              Gain Creators
                            </h4>
                          </div>
                          <Badge className="bg-blue-600 text-white">
                            {getValueMapItems('gain_creators').length}
                          </Badge>
                        </div>
                        
                        {/* Gain Creators Items List */}
                        <div>
                          {(() => {
                            const items = getValueMapItems('gain_creators');
                            if (items.length > 0) {
                              return (
                                <div className="space-y-1">
                                  {items.map((item, idx) => (
                                    <div key={item.id} className="px-3 py-2 bg-white dark:bg-gray-700 rounded-lg border border-blue-200 dark:border-blue-600 flex items-center justify-center w-[250px]">
                                      <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{item.label}</p>
                                     
                                    </div>
                                  ))}
                                </div>
                              );
                            }
                            if (vpcData.value_map.status === 'pending') {
                              return (
                                <div className="text-center py-6">
                                  <div className="w-12 h-12 bg-yellow-100 dark:bg-yellow-900/20 rounded-full flex items-center justify-center mx-auto mb-3">
                                    <AlertCircle className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />
                                  </div>
                                  <h4 className="font-semibold text-gray-800 dark:text-white mb-2">
                                    Coming Soon
                                  </h4>
                                  <p className="text-gray-600 dark:text-gray-400 text-sm mb-3">
                                    {vpcData.value_map.message}
                                  </p>
                                </div>
                              );
                            }
                            return (
                              <div className="text-center py-6">
                                <div className="w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-3">
                                  <TrendingUp className="w-6 h-6 text-gray-400" />
                                </div>
                                <p className="text-gray-500 dark:text-gray-400 text-sm">
                                  No items available yet
                                </p>
                              </div>
                            );
                          })()}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* Customer Profile Section - Card-based Layout */}
              <motion.div 
                variants={itemVariants} 
                className={`order-1 xl:order-2 grid grid-cols-2 gap-2 rounded-full p-2 h-[600px] w-[600px] mx-auto`}
              >
                  
                  {/* Jobs-to-be-Done Section */}
                  <Card className="col-span-2 p-2 border-2 border-green-200 dark:border-green-700 bg-green-50 dark:bg-gray-800 rounded-t-full flex justify-center items-center h-full row-span-1 hover:scale-[1.01] transition-all duration-300 cursor-pointer">
                    <div className="flex items-center justify-center gap-2">
                      <div className="p-2 bg-green-200 dark:bg-green-800/30 rounded-lg">
                        <Briefcase className="w-4 h-4 text-green-600 dark:text-green-400" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-lg font-bold text-green-800 dark:text-green-200">
                          Customer Jobs
                        </h3>
                      </div>
                      {getSectionData('jobs').count > 0 && (
                        <Badge className="bg-green-600 text-white">
                          {getSectionData('jobs').count}
                        </Badge>
                      )}
                    </div>
                    
                    {isFullscreen && getSectionData('jobs').items.length > 0 ? (
                      <div className="flex flex-col gap-1 -mt-2">
                        {getSectionData('jobs').items.map((item, index) => (
                          <motion.div
                            key={item.id}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.3 + index * 0.1 }}
                            className="p-2 bg-white dark:bg-gray-700 rounded-lg border border-green-200 dark:border-green-600 px-4"
                          >
                            <div className="flex items-center justify-between">
                              <p className="text-sm font-medium text-gray-800 dark:text-white">
                                {item.label}
                              </p>
                              {availablePersonas.length > 1 && selectedPersona === null && (
                                <Badge variant="outline" className="text-xs">
                                  {getPersonaDisplayName(item.persona_name)}
                                </Badge>
                              )}
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    ) : isFullscreen && (
                      <div className="text-center py-4 text-green-600 dark:text-green-400 text-sm">
                        No jobs identified yet
                      </div>
                    )}
                    {/* Customer Profile Label - positioned as overlay at top-right */}
                    <div className="sticky top-[43%] left-[50%] -translate-x-1/2 xl:top-[55.8%] xl:left-[63%] xl:translate-x-0 z-10">
                      <SectionOverlayLabel text="Customer Profile" />
                    </div>
                  </Card>
                  
                  {/* Pains Section */}
                  <Card className="row-span-1 p-2 border-2 border-red-200 dark:border-red-700 bg-red-50 dark:bg-gray-800 h-full rounded-bl-full hover:scale-[1.01] transition-all duration-300 cursor-pointer">
                    <div className="flex items-center gap-2">
                      <div className="p-2 bg-red-200 dark:bg-red-800/30 rounded-lg">
                        <Frown className="w-4 h-4 text-red-600 dark:text-red-400" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-lg font-bold text-red-800 dark:text-red-200">
                          Customer Pains
                        </h3>
                      </div>
                      {getSectionData('pains').count > 0 && (
                        <Badge className="bg-red-600 text-white">
                          {getSectionData('pains').count}
                        </Badge>
                      )}
                    </div>
                    
                    {isFullscreen && getSectionData('pains').items.length > 0 ? (
                      <div className="flex flex-col items-end space-y-1 -mt-3">
                        {getSectionData('pains').items.map((item, index) => (
                          <motion.div
                            key={item.id}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.5 + index * 0.1 }}
                            className="p-2 bg-white dark:bg-gray-700 rounded-lg border border-red-200 dark:border-red-600 w-50"
                          >
                            <div className="flex items-center justify-center">
                              {availablePersonas.length > 1 && selectedPersona === null && (
                                <Badge variant="outline" className="text-xs mr-2">
                                  {getPersonaDisplayName(item.persona_name)}
                                </Badge>
                              )}
                              <p className="text-sm font-medium text-gray-800 dark:text-white">
                                {item.label}
                              </p>
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    ) : isFullscreen && (
                      <div className="text-center py-4 text-red-600 dark:text-red-400 text-sm">
                        No pains identified yet
                      </div>
                    )}
                  </Card>

                  {/* Gains Section */}
                  <Card className="row-span-1 p-2 border-2 border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-gray-800 h-full rounded-br-full hover:scale-[1.01] transition-all duration-300 cursor-pointer">
                    <div className="flex items-center gap-2">
                      <div className="p-2 bg-blue-200 dark:bg-blue-800/30 rounded-lg">
                        <Smile className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-lg font-bold text-blue-800 dark:text-blue-200">
                          Customer Gains
                        </h3>
                      </div>
                      {getSectionData('gains').count > 0 && (
                        <Badge className="bg-blue-600 text-white">
                          {getSectionData('gains').count}
                        </Badge>
                      )}
                    </div>
                    
                    {isFullscreen && getSectionData('gains').items.length > 0 ? (
                      <div className="flex flex-col items-start space-y-1 -mt-3">
                        {getSectionData('gains').items.map((item, index) => (
                          <motion.div
                            key={item.id}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.7 + index * 0.1 }}
                            className="p-2 bg-white dark:bg-gray-700 rounded-lg border border-blue-200 dark:border-blue-600 w-52"
                          >
                            <div className="flex items-center justify-center">
                              <p className="text-sm font-medium text-gray-800 dark:text-white">
                                {item.label}
                              </p>
                              {availablePersonas.length > 1 && selectedPersona === null && (
                                <Badge variant="outline" className="text-xs ml-2">
                                  {getPersonaDisplayName(item.persona_name)}
                                </Badge>
                              )}
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    ) : isFullscreen && (
                      <div className="text-center py-4 text-blue-600 dark:text-blue-400 text-sm">
                        No gains identified yet
                      </div>
                    )}
                  </Card>
              </motion.div>
            </motion.div>
          </div>
        )}
        
        {/* Main Canvas Container */}
        {!isFullscreen && (
          <>
            {/* Persona Selector */}
            <PersonaSelector />

            <motion.div
              ref={vpcCanvasRef}
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              className={`grid grid-cols-1 xl:grid-cols-2 gap-12 mx-auto max-w-7xl`}
            >
              
              {/* Value Map Section - Bento Grid Design */}
              <motion.div variants={itemVariants} className="order-2 xl:order-1 flex items-center justify-center">
                <div 
                  className="relative flex items-center justify-center p-2 rounded-2xl"
                  onMouseLeave={() => setHoveredValueMapSection(null)}
                >
                    {/* Value Map Label - positioned as overlay at top-left */}
                    <div className="absolute top-30 left-1/2 -translate-x-1/2 xl:top-[34.5%] xl:left-[41%] xl:translate-x-0 z-10">
                      <SectionOverlayLabel text="Value Map" />
                    </div>
                 
                  {/* Bento Grid Container */}
                  <div className="grid grid-cols-2 grid-rows-2 gap-2">
                    
                    {/* Products & Services - Large Top Section */}
                    <div
                      className={`col-span-2 row-span-2 rounded-t-2xl border-2 cursor-pointer transition-all duration-300 group h-[150px] bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-700 hover:bg-green-100 dark:hover:bg-green-900/20 ${
                        hoveredValueMapSection === 'products' ? 'scale-[1.02] shadow-lg' : 'hover:scale-[1.01]'
                      }`}
                      onMouseEnter={() => setHoveredValueMapSection('products')}
                    >
                      <div className="p-6">
                        <div className="flex items-center gap-4">
                          <div className={`p-4 rounded-xl transition-all duration-300 dark:bg-green-800/30 bg-green-200 ${
                            hoveredValueMapSection === 'products' ? 'shadow-md scale-110' : ''
                          }`}>
                            <Package className={`w-8 h-8 text-green-600 dark:text-green-400 transition-all duration-300`} />
                          </div>
                          <div>
                            <h4 className={`text-xl font-bold text-green-700 dark:text-green-300 mb-1`}>
                              Products & Services
                            </h4>
                            <p className="text-sm text-gray-600 dark:text-gray-400 max-w-xs">
                              All products and services your value proposition is built around
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Pain Relievers - Bottom Left */}
                    <div
                      className={`col-span-1 row-span-1 rounded-bl-2xl border-2 cursor-pointer transition-all duration-300 group bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/20 ${
                        hoveredValueMapSection === 'pain_relievers' ? 'scale-[1.02] shadow-lg' : 'hover:scale-[1.01]'
                      }`}
                      onMouseEnter={() => setHoveredValueMapSection('pain_relievers')}
                    >
                      <div className="p-4 h-full flex flex-col justify-between">
                        <div className="flex items-center gap-4 mb-3 justify-left">
                          <div className={`p-3 rounded-xl transition-all duration-300 bg-red-200 dark:bg-red-800/30 ${
                            hoveredValueMapSection === 'pain_relievers' ? ' shadow-md scale-110' : ''
                          }`}>
                            <Heart className={`w-6 h-6 text-red-600 dark:text-red-400 transition-all duration-300`} />
                          </div>
                         
                        </div>
                        <div>
                          <h4 className={`text-lg font-bold text-red-700 dark:text-red-300 mb-2`}>
                            Pain Relievers
                          </h4>
                          <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                            How your products alleviate customer pains
                          </p>
                        </div>
                        
                      </div>
                    </div>

                    {/* Gain Creators - Bottom Right */}
                    <div
                      className={`col-span-1 row-span-1 rounded-br-2xl border-2 cursor-pointer transition-all duration-300 group ${
                        valueMapSections[2].bgColor
                      } ${valueMapSections[2].borderColor} ${valueMapSections[2].hoverColor} ${
                        hoveredValueMapSection === 'gain_creators' ? 'scale-[1.02] shadow-lg' : 'hover:scale-[1.01]'
                      }`}
                      onMouseEnter={() => setHoveredValueMapSection('gain_creators')}
                    >
                      <div className="p-4 h-full flex flex-col justify-between">
                        <div className="flex items-center gap-4 mb-3 justify-left">
                          <div className={`p-3 rounded-xl transition-all duration-300 bg-blue-200 dark:bg-blue-800/30 ${
                            hoveredValueMapSection === 'gain_creators' ? 'shadow-md scale-110' : ''
                          }`}>
                            <TrendingUp className={`w-6 h-6 ${valueMapSections[2].iconColor} transition-all duration-300`} />
                          </div>
                         
                        </div>
                        <div>
                          <h4 className={`text-lg font-bold ${valueMapSections[2].textColor} mb-2`}>
                            Gain Creators
                          </h4>
                          <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                            How your products or services create customer gains
                          </p>
                        </div>
                       
                      </div>
                    </div>
                  </div>

                  {/* Value Map hover details modal */}
                  <AnimatePresence>
                    {hoveredValueMapSection && valueMapSections.find(s => s.id === hoveredValueMapSection) && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: -20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: -20 }}
                        transition={{ duration: 0.2, ease: "easeOut" }}
                        className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-4 w-80 max-w-[90vw] bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-600 z-30 overflow-hidden pointer-events-none"
                      >
                        {(() => {
                          const section = valueMapSections.find(s => s.id === hoveredValueMapSection);
                          const IconComponent = section?.icon || Package;
                          
                          return (
                            <>
                              {/* Header */}
                              <div 
                                className="p-4 text-white"
                                style={{ backgroundColor: section?.color }}
                              >
                                <div className="flex items-center gap-3">
                                  <div className="p-2 bg-white/20 rounded-lg backdrop-blur-sm">
                                    <IconComponent className="w-5 h-5 text-white" />
                                  </div>
                                  <div>
                                    <h3 className="font-bold text-lg">
                                      {section?.title}
                                    </h3>
                                    <p className="text-white/80 text-sm">
                                      {section?.subtitle}
                                    </p>
                                  </div>
                                </div>
                              </div>
                              
                              {/* Content */}
                              <div className="p-4">
                                {(() => {
                                  const items = getValueMapItems(section?.id as any);
                                  if (items.length > 0) {
                                    return (
                                      <div className="space-y-2 max-h-60 overflow-y-auto">
                                        {items.map((item, idx) => (
                                          <div key={item.id} className="p-2 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600 flex items-center justify-between">
                                            <p className="text-sm font-medium text-gray-800 dark:text-white truncate">{item.label}</p>
                                            {availablePersonas.length > 1 && selectedPersona === null && (
                                              <Badge variant="outline" className="text-xs ml-2">{getPersonaDisplayName(item.persona_name)}</Badge>
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    );
                                  }
                                  if (vpcData.value_map.status === 'pending') {
                                    return (
                                      <div className="text-center py-6">
                                        <div className="w-12 h-12 bg-yellow-100 dark:bg-yellow-900/20 rounded-full flex items-center justify-center mx-auto mb-3">
                                          <AlertCircle className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />
                                        </div>
                                        <h4 className="font-semibold text-gray-800 dark:text-white mb-2">
                                          Coming Soon
                                        </h4>
                                        <p className="text-gray-600 dark:text-gray-400 text-sm mb-3">
                                          {vpcData.value_map.message}
                                        </p>
                                      </div>
                                    );
                                  }
                                  return (
                                    <div className="text-center py-6">
                                      <div className="w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-3">
                                        <IconComponent className="w-6 h-6 text-gray-400" />
                                      </div>
                                      <p className="text-gray-500 dark:text-gray-400 text-sm">
                                        No items available yet
                                      </p>
                                    </div>
                                  );
                                })()}
                              </div>
                            </>
                          );
                        })()}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </motion.div>

              {/* Customer Profile Section - Card-based Layout */}
              <motion.div 
                variants={itemVariants} 
                className="order-1 xl:order-2 relative flex flex-col items-center"
                onMouseLeave={() => setHoveredCustomerSection(null)}
              >                  
                  <div className="relative grid grid-cols-2 gap-2 rounded-full p-2 h-[450px] w-[450px] mx-auto">
                  {/* Jobs-to-be-Done Section */}
                  <Card 
                    className="col-span-2 p-2 border-2 border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/10 rounded-t-full flex justify-center items-center h-full row-span-1 cursor-pointer transition-all duration-300 hover:scale-[1.02] hover:shadow-lg"
                    onMouseEnter={() => setHoveredCustomerSection('jobs')}
                  >
                    <div className="flex items-center justify-center gap-2">
                      <div className="p-2 bg-green-200 dark:bg-green-800/30 rounded-lg">
                        <Briefcase className="w-4 h-4 text-green-600 dark:text-green-400" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-lg font-bold text-green-800 dark:text-green-200">
                          Customer Jobs
                        </h3>
                      </div>
                      {getSectionData('jobs').count > 0 && (
                        <Badge className="bg-green-600 text-white">
                          {getSectionData('jobs').count}
                        </Badge>
                      )}
                    </div>
                    {/* Customer Profile Label - positioned as overlay at top-right */}
                    <div className="absolute top-43 left-1/2 -translate-x-1/2 xl:top-43 xl:left-39 xl:translate-x-0 z-10">
                      <SectionOverlayLabel text="Customer Profile" />
                    </div>
                  </Card>

                  {/* Pains Section */}
                  <Card 
                    className="row-span-1 p-2 border-2 border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10 h-full rounded-bl-full cursor-pointer transition-all duration-300 hover:scale-[1.02] hover:shadow-lg"
                    onMouseEnter={() => setHoveredCustomerSection('pains')}
                  >
                    <div className="flex items-center gap-2">
                      <div className="p-2 bg-red-200 dark:bg-red-800/30 rounded-lg">
                        <Frown className="w-4 h-4 text-red-600 dark:text-red-400" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-lg font-bold text-red-800 dark:text-red-200">
                          Customer Pains
                        </h3>
                      </div>
                      {getSectionData('pains').count > 0 && (
                        <Badge className="bg-red-600 text-white">
                          {getSectionData('pains').count}
                        </Badge>
                      )}
                    </div>
                  </Card>

                  {/* Gains Section */}
                  <Card 
                    className="row-span-1 p-2 border-2 border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/10 h-full rounded-br-full cursor-pointer transition-all duration-300 hover:scale-[1.02] hover:shadow-lg"
                    onMouseEnter={() => setHoveredCustomerSection('gains')}
                  >
                    <div className="flex items-center gap-2">
                      <div className="p-2 bg-blue-200 dark:bg-blue-800/30 rounded-lg">
                        <Smile className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-lg font-bold text-blue-800 dark:text-blue-200">
                          Customer Gains
                        </h3>
                      </div>
                      {getSectionData('gains').count > 0 && (
                        <Badge className="bg-blue-600 text-white">
                          {getSectionData('gains').count}
                        </Badge>
                      )}
                    </div>
                  </Card>

                  {/* Customer Profile hover details modal */}
                  <AnimatePresence>
                    {hoveredCustomerSection && segments.find(s => s.id === hoveredCustomerSection) && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: -20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: -20 }}
                        transition={{ duration: 0.2, ease: "easeOut" }}
                        className="absolute top-12 left-1/2 transform -translate-x-1/2 -translate-y-4 w-80 max-w-[90vw] bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-600 z-30 overflow-hidden pointer-events-none"
                      >
                        {(() => {
                          const segment = segments.find(s => s.id === hoveredCustomerSection);
                          const IconComponent = segment?.icon || Briefcase;
                          
                          return (
                            <>
                              {/* Header */}
                              <div 
                                className="p-4 text-white"
                                style={{ backgroundColor: segment?.fillColor }}
                              >
                                <div className="flex items-center gap-3">
                                  <div className="p-2 bg-white/20 rounded-lg backdrop-blur-sm">
                                    <IconComponent className="w-5 h-5 text-white" />
                                  </div>
                                  <div>
                                    <h3 className="font-bold text-lg">
                                      {segment?.title}
                                    </h3>
                                    <p className="text-white/80 text-sm">
                                      {segment?.data.count} {segment?.data.count === 1 ? 'item' : 'items'}
                                      {selectedPersona && ` for ${getPersonaDisplayName(selectedPersona)}`}
                                    </p>
                                  </div>
                                </div>
                              </div>
                              
                              {/* Content */}
                              <div className="p-4 max-h-92 overflow-y-auto">
                                {segment?.data?.items && segment.data.items.length > 0 ? (
                                  <div className="space-y-3">
                                    {segment.data.items.map((item, index) => (
                                      <motion.div
                                        key={item.id}
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: index * 0.1 }}
                                        className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600"
                                      >
                                        <p className="text-sm font-medium text-gray-800 dark:text-white">
                                          {item.label}
                                        </p>
                                        {availablePersonas.length > 1 && selectedPersona === null && (
                                          <div className="mt-2 flex items-center gap-2">
                                            <UserCircle2 className="w-3 h-3 text-gray-400" />
                                            <span className="text-xs text-gray-500 dark:text-gray-400">
                                              {getPersonaDisplayName(item.persona_name)}
                                            </span>
                                          </div>
                                        )}
                                      </motion.div>
                                    ))}
                                  </div>
                                ) : (
                                  <div className="text-center py-6">
                                    <div className="w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-3">
                                      <IconComponent className="w-6 h-6 text-gray-400" />
                                    </div>
                                    <p className="text-gray-500 dark:text-gray-400 text-sm">
                                      No {hoveredCustomerSection} identified yet
                                      {selectedPersona && ` for ${getPersonaDisplayName(selectedPersona)}`}
                                    </p>
                                  </div>
                                )}
                              </div>
                            </>
                          );
                        })()}
                      </motion.div>
                    )}
                  </AnimatePresence>
                  </div>
              </motion.div>
            </motion.div>

            {/* Action Buttons */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.2 }}
              className="flex justify-center mt-6 gap-2 items-center"
            >
             

              <Button
                onClick={(e) => {
                  const btn = e.currentTarget as HTMLButtonElement;
                  btn.dataset.loading = 'true';
                  btn.setAttribute('aria-busy', 'true');
                  btn.disabled = true;
                  router.push(`/team-workspace/value-map/${projectId}`);
                }}
                data-loading="false"
                variant="default"
                aria-label="Edit value map"
                className="relative flex items-center gap-2 bg-green-500 hover:bg-green-600 text-white dark:bg-green-500/90 dark:hover:bg-green-400 shadow-sm data-[loading=true]:opacity-80 data-[loading=true]:cursor-wait"
              >
                <span className="inline-flex items-center gap-2 data-[loading=true]:hidden">
                  <Edit className="w-4 h-4" />
                  Edit
                </span>
                <span className="hidden items-center gap-2 data-[loading=true]:inline-flex">
                  <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" aria-hidden="true" />
                  Opening...
                </span>
              </Button>
              
              <Button
                onClick={toggleFullscreen}
                variant="outline"
                size="sm"
                className="flex items-center gap-2"
              >
                <Maximize2 className="w-4 h-4" />
                View Fullscreen
              </Button>
            </motion.div>
          </>
        )}

        {/* Navigation Buttons */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.4 }}
          className="flex justify-center gap-4 mt-8"
        >
          <Button
            onClick={() => router.push(`/team-workspace/customer-profile/${projectId}`)}
            variant="outline"
            className="dark:border-brand-600 dark:text-brand-300 dark:hover:bg-brand-800"
          >
            <ChevronRight className="w-4 h-4 rotate-180" />
            Back to Customer Profile
          </Button>
          <Button
            onClick={() => {
              setIsNavigating(true);
              router.push(`/team-workspace/projects-mvp`);
            }}
            aria-busy={isNavigating}
            className="bg-brand-600 hover:bg-brand-700 text-white"
          >
            {isNavigating ? (
              <>
                <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
                Continuing...
              </>
            ) : (
              <>
                Continue to Next Module
                <ChevronRight className="w-4 h-4 ml-2" />
              </>
            )}
          </Button>
        </motion.div>
      </div>
    </div>
  );
}