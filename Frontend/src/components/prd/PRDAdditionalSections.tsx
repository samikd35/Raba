"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ChevronDown,
  ChevronRight,
  Factory,
  ShoppingCart,
  Package,
  Shield,
  FlaskConical,
  Truck,
  BarChart3,
  TrendingUp,
  Clock,
  CheckCircle,
  AlertTriangle,
  FileText,
  Tag,
  MapPin,
  Beaker,
  Award,
  Building,
  Calendar,
  Layers,
  Target,
} from "lucide-react";
import type {
  ProductionQC,
  ConsumerUseCase,
  PackagingFormats,
  RegulatorySafety,
  ProductComposition,
  DistributionChannels,
  SuccessSignals,
  FABAnalysis,
  SourceArtifacts,
  PRDMetadata,
} from "@/hooks/usePRD";

// Production QC Section
interface PRDProductionQCSectionProps {
  productionQC: ProductionQC;
  index?: number;
}

export function PRDProductionQCSection({ productionQC, index = 8 }: PRDProductionQCSectionProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Card className="border-gray-200 dark:border-gray-700 dark:bg-gray-900/50 transition-all hover:shadow-md hover:bg-gray-50 dark:hover:bg-gray-800/70 rounded-lg overflow-hidden">
      <div
        className="px-3 py-1 cursor-pointer select-none transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-start gap-2">
          <div className="text-gray-500 dark:text-gray-400 shrink-0 mt-0.5">
            {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </div>
          <div className="flex-1 flex flex-col gap-2">
            <Badge
              variant="outline"
              className="text-orange-600 border-orange-200 dark:text-orange-400 dark:border-orange-700 px-2 py-0.5 rounded-lg bg-orange-50 dark:bg-orange-900/30 w-fit"
            >
              <Factory className="w-3 h-3 mr-1" />
              <span className="text-[0.9rem] font-semibold">{index} · Production & QC</span>
            </Badge>
            <span className="text-sm font-medium text-gray-500 dark:text-brand-200">
              {productionQC.manufacturing_approach} · {productionQC.lead_time}
            </span>
          </div>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            style={{ overflow: "hidden" }}
          >
            <CardContent className="px-4 space-y-3 pb-4">
              {/* Manufacturing Approach */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg border border-orange-200 dark:border-orange-700/60">
                  <div className="flex items-center gap-2 mb-2">
                    <Building className="w-4 h-4 text-orange-600 dark:text-orange-400" />
                    <span className="text-xs font-semibold text-orange-700 dark:text-orange-400">Manufacturing Approach</span>
                  </div>
                  <p className="text-sm text-orange-700 dark:text-orange-200 capitalize">{productionQC.manufacturing_approach.replace(/_/g, ' ')}</p>
                </div>
                <div className="p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg border border-orange-200 dark:border-orange-700/60">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="w-4 h-4 text-orange-600 dark:text-orange-400" />
                    <span className="text-xs font-semibold text-orange-700 dark:text-orange-400">Lead Time</span>
                  </div>
                  <p className="text-sm text-orange-700 dark:text-orange-200">{productionQC.lead_time}</p>
                </div>
              </div>

              {/* Production Partner & Batch Size */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2 mb-2">
                    <Factory className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                    <span className="text-xs font-semibold text-gray-700 dark:text-gray-400">Production Partner</span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-300">{productionQC.production_partner}</p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2 mb-2">
                    <Layers className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                    <span className="text-xs font-semibold text-gray-700 dark:text-gray-400">Initial Batch Size</span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-300">{productionQC.batch_size_initial}</p>
                </div>
              </div>

              {/* Quality Controls */}
              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-700/60">
                <h4 className="text-sm font-semibold text-green-700 dark:text-green-400 mb-3 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  Quality Controls
                </h4>
                <div className="space-y-2">
                  {productionQC.quality_controls.map((control, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-sm text-green-700 dark:text-green-200">
                      <span className="shrink-0 w-2 h-2 rounded-full bg-green-500 dark:bg-green-600 mt-1.5" />
                      <span>{control}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

// Consumer Use Case Section
interface PRDConsumerUseCaseSectionProps {
  consumerUseCase: ConsumerUseCase;
  index?: number;
}

export function PRDConsumerUseCaseSection({ consumerUseCase, index = 9 }: PRDConsumerUseCaseSectionProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Card className="border-gray-200 dark:border-gray-700 dark:bg-gray-900/50 transition-all hover:shadow-md hover:bg-gray-50 dark:hover:bg-gray-800/70 rounded-lg overflow-hidden">
      <div
        className="px-3 py-1 cursor-pointer select-none transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-start gap-2">
          <div className="text-gray-500 dark:text-gray-400 shrink-0 mt-0.5">
            {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </div>
          <div className="flex-1 flex flex-col gap-2">
            <Badge
              variant="outline"
              className="text-purple-600 border-purple-200 dark:text-purple-400 dark:border-purple-700 px-2 py-0.5 rounded-lg bg-purple-50 dark:bg-purple-900/30 w-fit"
            >
              <ShoppingCart className="w-3 h-3 mr-1" />
              <span className="text-[0.9rem] font-semibold">{index} · Consumer Use Case</span>
            </Badge>
            <span className="text-sm font-medium text-gray-500 dark:text-brand-200">
              {consumerUseCase.product_category}
            </span>
          </div>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            style={{ overflow: "hidden" }}
          >
            <CardContent className="px-4 space-y-3 pb-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-700/60">
                  <div className="flex items-center gap-2 mb-2">
                    <Tag className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                    <span className="text-xs font-semibold text-purple-700 dark:text-purple-400">Product Category</span>
                  </div>
                  <p className="text-sm text-purple-700 dark:text-purple-200">{consumerUseCase.product_category}</p>
                </div>
                <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-700/60">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                    <span className="text-xs font-semibold text-purple-700 dark:text-purple-400">Usage Frequency</span>
                  </div>
                  <p className="text-sm text-purple-700 dark:text-purple-200">{consumerUseCase.usage_frequency}</p>
                </div>
              </div>

              <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-2 mb-2">
                  <ShoppingCart className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                  <span className="text-xs font-semibold text-gray-700 dark:text-gray-400">Purchase Occasion</span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-300">{consumerUseCase.purchase_occasion}</p>
              </div>

              <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-2 mb-2">
                  <Target className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                  <span className="text-xs font-semibold text-gray-700 dark:text-gray-400">Consumption Context</span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-300">{consumerUseCase.consumption_context}</p>
              </div>

              {/* Competing Alternatives */}
              <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-700/60">
                <h4 className="text-sm font-semibold text-red-700 dark:text-red-400 mb-3 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Competing Alternatives
                </h4>
                <div className="space-y-2">
                  {consumerUseCase.competing_alternatives.map((alt, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-sm text-red-700 dark:text-red-200">
                      <span className="shrink-0 w-2 h-2 rounded-full bg-red-500 dark:bg-red-600 mt-1.5" />
                      <span>{alt}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

// Packaging Formats Section
interface PRDPackagingFormatsSectionProps {
  packagingFormats: PackagingFormats;
  index?: number;
}

export function PRDPackagingFormatsSection({ packagingFormats, index = 10 }: PRDPackagingFormatsSectionProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Card className="border-gray-200 dark:border-gray-700 dark:bg-gray-900/50 transition-all hover:shadow-md hover:bg-gray-50 dark:hover:bg-gray-800/70 rounded-lg overflow-hidden">
      <div
        className="px-3 py-1 cursor-pointer select-none transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-start gap-2">
          <div className="text-gray-500 dark:text-gray-400 shrink-0 mt-0.5">
            {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </div>
          <div className="flex-1 flex flex-col gap-2">
            <Badge
              variant="outline"
              className="text-teal-600 border-teal-200 dark:text-teal-400 dark:border-teal-700 px-2 py-0.5 rounded-lg bg-teal-50 dark:bg-teal-900/30 w-fit"
            >
              <Package className="w-3 h-3 mr-1" />
              <span className="text-[0.9rem] font-semibold">{index} · Packaging Formats</span>
            </Badge>
            <span className="text-sm font-medium text-gray-500 dark:text-brand-200">
              {packagingFormats.sku_variants.length} SKU variants · {packagingFormats.primary_packaging.format}
            </span>
          </div>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            style={{ overflow: "hidden" }}
          >
            <CardContent className="px-4 space-y-3 pb-4">
              {/* Primary Packaging */}
              <div className="p-4 bg-teal-50 dark:bg-teal-900/20 rounded-lg border border-teal-200 dark:border-teal-700/60">
                <h4 className="text-sm font-semibold text-teal-700 dark:text-teal-400 mb-3 flex items-center gap-2">
                  <Package className="w-4 h-4" />
                  Primary Packaging
                </h4>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <span className="text-xs font-medium text-teal-600 dark:text-teal-400">Size</span>
                    <p className="text-sm text-teal-700 dark:text-teal-200">{packagingFormats.primary_packaging.size}</p>
                  </div>
                  <div>
                    <span className="text-xs font-medium text-teal-600 dark:text-teal-400">Format</span>
                    <p className="text-sm text-teal-700 dark:text-teal-200">{packagingFormats.primary_packaging.format}</p>
                  </div>
                  <div>
                    <span className="text-xs font-medium text-teal-600 dark:text-teal-400">Material</span>
                    <p className="text-sm text-teal-700 dark:text-teal-200">{packagingFormats.primary_packaging.material}</p>
                  </div>
                </div>
              </div>

              {/* SKU Variants */}
              <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                  <Layers className="w-4 h-4" />
                  SKU Variants
                </h4>
                <div className="space-y-2">
                  {packagingFormats.sku_variants.map((sku, idx) => (
                    <div key={idx} className="p-3 bg-white dark:bg-gray-900/50 rounded-lg border border-gray-100 dark:border-gray-700 flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{sku.variant_name}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Size: {sku.size}</p>
                      </div>
                      <Badge variant="outline" className="text-green-600 border-green-200 dark:text-green-400 dark:border-green-700">
                        {sku.target_price}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>

              {/* Labeling Requirements */}
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700/60">
                <h4 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-3 flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Labeling Requirements
                </h4>
                <div className="space-y-2">
                  {packagingFormats.labeling_requirements.map((req, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-sm text-blue-700 dark:text-blue-200">
                      <span className="shrink-0 w-2 h-2 rounded-full bg-blue-500 dark:bg-blue-600 mt-1.5" />
                      <span>{req}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

// Regulatory Safety Section
interface PRDRegulatorySafetySectionProps {
  regulatorySafety: RegulatorySafety;
  index?: number;
}

export function PRDRegulatorySafetySection({ regulatorySafety, index = 11 }: PRDRegulatorySafetySectionProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Card className="border-gray-200 dark:border-gray-700 dark:bg-gray-900/50 transition-all hover:shadow-md hover:bg-gray-50 dark:hover:bg-gray-800/70 rounded-lg overflow-hidden">
      <div
        className="px-3 py-1 cursor-pointer select-none transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-start gap-2">
          <div className="text-gray-500 dark:text-gray-400 shrink-0 mt-0.5">
            {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </div>
          <div className="flex-1 flex flex-col gap-2">
            <Badge
              variant="outline"
              className="text-red-600 border-red-200 dark:text-red-400 dark:border-red-700 px-2 py-0.5 rounded-lg bg-red-50 dark:bg-red-900/30 w-fit"
            >
              <Shield className="w-3 h-3 mr-1" />
              <span className="text-[0.9rem] font-semibold">{index} · Regulatory & Safety</span>
            </Badge>
            <span className="text-sm font-medium text-gray-500 dark:text-brand-200">
              {regulatorySafety.certifications_required.length} certifications · {regulatorySafety.regulatory_bodies.length} regulatory bodies
            </span>
          </div>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            style={{ overflow: "hidden" }}
          >
            <CardContent className="px-4 space-y-3 pb-4">
              {/* Compliance Timeline */}
              <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-700/60">
                <div className="flex items-center gap-2 mb-2">
                  <Calendar className="w-4 h-4 text-red-600 dark:text-red-400" />
                  <span className="text-sm font-semibold text-red-700 dark:text-red-400">Compliance Timeline</span>
                </div>
                <p className="text-sm text-red-700 dark:text-red-200">{regulatorySafety.compliance_timeline}</p>
              </div>

              {/* Certifications Required */}
              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-700/60">
                <h4 className="text-sm font-semibold text-green-700 dark:text-green-400 mb-3 flex items-center gap-2">
                  <Award className="w-4 h-4" />
                  Certifications Required
                </h4>
                <div className="space-y-2">
                  {regulatorySafety.certifications_required.map((cert, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-sm text-green-700 dark:text-green-200">
                      <span className="shrink-0 w-2 h-2 rounded-full bg-green-500 dark:bg-green-600 mt-1.5" />
                      <span>{cert}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Regulatory Bodies */}
              <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                  <Building className="w-4 h-4" />
                  Regulatory Bodies
                </h4>
                <div className="flex flex-wrap gap-2">
                  {regulatorySafety.regulatory_bodies.map((body, idx) => (
                    <Badge key={idx} variant="outline" className="text-gray-600 dark:text-gray-300">
                      {body}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Safety Testing */}
              <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-700/60">
                <h4 className="text-sm font-semibold text-amber-700 dark:text-amber-400 mb-3 flex items-center gap-2">
                  <Beaker className="w-4 h-4" />
                  Safety Testing
                </h4>
                <div className="space-y-2">
                  {regulatorySafety.safety_testing.map((test, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-sm text-amber-700 dark:text-amber-200">
                      <span className="shrink-0 w-2 h-2 rounded-full bg-amber-500 dark:bg-amber-600 mt-1.5" />
                      <span>{test}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

// Product Composition Section
interface PRDProductCompositionSectionProps {
  productComposition: ProductComposition;
  index?: number;
}

export function PRDProductCompositionSection({ productComposition, index = 12 }: PRDProductCompositionSectionProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Card className="border-gray-200 dark:border-gray-700 dark:bg-gray-900/50 transition-all hover:shadow-md hover:bg-gray-50 dark:hover:bg-gray-800/70 rounded-lg overflow-hidden">
      <div
        className="px-3 py-1 cursor-pointer select-none transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-start gap-2">
          <div className="text-gray-500 dark:text-gray-400 shrink-0 mt-0.5">
            {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </div>
          <div className="flex-1 flex flex-col gap-2">
            <Badge
              variant="outline"
              className="text-cyan-600 border-cyan-200 dark:text-cyan-400 dark:border-cyan-700 px-2 py-0.5 rounded-lg bg-cyan-50 dark:bg-cyan-900/30 w-fit"
            >
              <FlaskConical className="w-3 h-3 mr-1" />
              <span className="text-[0.9rem] font-semibold">{index} · Product Composition</span>
            </Badge>
            <span className="text-sm font-medium text-gray-500 dark:text-brand-200">
              {productComposition.key_ingredients.length} key ingredients · Shelf life: {productComposition.shelf_life}
            </span>
          </div>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            style={{ overflow: "hidden" }}
          >
            <CardContent className="px-4 space-y-3 pb-4">
              {/* Shelf Life */}
              <div className="p-3 bg-cyan-50 dark:bg-cyan-900/20 rounded-lg border border-cyan-200 dark:border-cyan-700/60">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                  <span className="text-xs font-semibold text-cyan-700 dark:text-cyan-400">Shelf Life</span>
                </div>
                <p className="text-sm text-cyan-700 dark:text-cyan-200">{productComposition.shelf_life}</p>
              </div>

              {/* Formulation Approach */}
              <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
                  <Beaker className="w-4 h-4" />
                  Formulation Approach
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">{productComposition.formulation_approach}</p>
              </div>

              {/* Key Ingredients */}
              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-700/60">
                <h4 className="text-sm font-semibold text-green-700 dark:text-green-400 mb-3 flex items-center gap-2">
                  <FlaskConical className="w-4 h-4" />
                  Key Ingredients
                </h4>
                <div className="space-y-2">
                  {productComposition.key_ingredients.map((ingredient, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-sm text-green-700 dark:text-green-200">
                      <span className="shrink-0 w-2 h-2 rounded-full bg-green-500 dark:bg-green-600 mt-1.5" />
                      <span>{ingredient}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Quality Attributes */}
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700/60">
                <h4 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-3 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  Quality Attributes
                </h4>
                <div className="space-y-2">
                  {productComposition.quality_attributes.map((attr, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-sm text-blue-700 dark:text-blue-200">
                      <span className="shrink-0 w-2 h-2 rounded-full bg-blue-500 dark:bg-blue-600 mt-1.5" />
                      <span>{attr}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

// Distribution Channels Section
interface PRDDistributionChannelsSectionProps {
  distributionChannels: DistributionChannels;
  index?: number;
}

export function PRDDistributionChannelsSection({ distributionChannels, index = 13 }: PRDDistributionChannelsSectionProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Card className="border-gray-200 dark:border-gray-700 dark:bg-gray-900/50 transition-all hover:shadow-md hover:bg-gray-50 dark:hover:bg-gray-800/70 rounded-lg overflow-hidden">
      <div
        className="px-3 py-1 cursor-pointer select-none transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-start gap-2">
          <div className="text-gray-500 dark:text-gray-400 shrink-0 mt-0.5">
            {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </div>
          <div className="flex-1 flex flex-col gap-2">
            <Badge
              variant="outline"
              className="text-indigo-600 border-indigo-200 dark:text-indigo-400 dark:border-indigo-700 px-2 py-0.5 rounded-lg bg-indigo-50 dark:bg-indigo-900/30 w-fit"
            >
              <Truck className="w-3 h-3 mr-1" />
              <span className="text-[0.9rem] font-semibold">{index} · Distribution Channels</span>
            </Badge>
            <span className="text-sm font-medium text-gray-500 dark:text-brand-200">
              {distributionChannels.primary_channels.length} primary channels · {distributionChannels.distribution_partners.length} partners
            </span>
          </div>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            style={{ overflow: "hidden" }}
          >
            <CardContent className="px-4 space-y-3 pb-4">
              {/* Route to Market */}
              <div className="p-4 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-200 dark:border-indigo-700/60">
                <h4 className="text-sm font-semibold text-indigo-700 dark:text-indigo-400 mb-2 flex items-center gap-2">
                  <Truck className="w-4 h-4" />
                  Route to Market
                </h4>
                <p className="text-sm text-indigo-700 dark:text-indigo-200 leading-relaxed">{distributionChannels.route_to_market}</p>
              </div>

              {/* Primary Channels */}
              <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                  <MapPin className="w-4 h-4" />
                  Primary Channels
                </h4>
                <div className="space-y-3">
                  {distributionChannels.primary_channels.map((channel, idx) => (
                    <div key={idx} className="p-3 bg-white dark:bg-gray-900/50 rounded-lg border border-gray-100 dark:border-gray-700">
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{channel.channel_name}</p>
                        <Badge variant="outline" className="text-xs capitalize">{channel.channel_type}</Badge>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        <MapPin className="w-3 h-3 inline mr-1" />
                        {channel.geographic_coverage}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Distribution Partners */}
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700/60">
                <h4 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-3 flex items-center gap-2">
                  <Building className="w-4 h-4" />
                  Distribution Partners
                </h4>
                <div className="space-y-2">
                  {distributionChannels.distribution_partners.map((partner, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-sm text-blue-700 dark:text-blue-200">
                      <span className="shrink-0 w-2 h-2 rounded-full bg-blue-500 dark:bg-blue-600 mt-1.5" />
                      <span>{partner}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

// Success Signals Section
interface PRDSuccessSignalsSectionProps {
  successSignals: SuccessSignals;
  index?: number;
}

export function PRDSuccessSignalsSection({ successSignals, index = 14 }: PRDSuccessSignalsSectionProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Card className="border-gray-200 dark:border-gray-700 dark:bg-gray-900/50 transition-all hover:shadow-md hover:bg-gray-50 dark:hover:bg-gray-800/70 rounded-lg overflow-hidden">
      <div
        className="px-3 py-1 cursor-pointer select-none transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-start gap-2">
          <div className="text-gray-500 dark:text-gray-400 shrink-0 mt-0.5">
            {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </div>
          <div className="flex-1 flex flex-col gap-2">
            <Badge
              variant="outline"
              className="text-emerald-600 border-emerald-200 dark:text-emerald-400 dark:border-emerald-700 px-2 py-0.5 rounded-lg bg-emerald-50 dark:bg-emerald-900/30 w-fit"
            >
              <BarChart3 className="w-3 h-3 mr-1" />
              <span className="text-[0.9rem] font-semibold">{index} · Success Signals</span>
            </Badge>
            <span className="text-sm font-medium text-gray-500 dark:text-brand-200">
              {successSignals.quantitative.length} quantitative · {successSignals.qualitative.length} qualitative metrics
            </span>
          </div>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            style={{ overflow: "hidden" }}
          >
            <CardContent className="px-4 space-y-3 pb-4">
              {/* Quantitative Signals */}
              <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg border border-emerald-200 dark:border-emerald-700/60">
                <h4 className="text-sm font-semibold text-emerald-700 dark:text-emerald-400 mb-3 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4" />
                  Quantitative Metrics
                </h4>
                <div className="space-y-3">
                  {successSignals.quantitative.map((signal, idx) => (
                    <div key={idx} className="p-3 bg-white dark:bg-gray-900/50 rounded-lg border border-emerald-100 dark:border-emerald-800">
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-sm font-medium text-emerald-800 dark:text-emerald-200">{signal.metric_name}</p>
                        <Badge className="bg-emerald-600 text-white dark:bg-emerald-700">{signal.target}</Badge>
                      </div>
                      <p className="text-xs text-emerald-700 dark:text-emerald-300 mb-2">{signal.description}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 italic">
                        <strong>Measurement:</strong> {signal.measurement_method}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Qualitative Signals */}
              <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-700/60">
                <h4 className="text-sm font-semibold text-purple-700 dark:text-purple-400 mb-3 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4" />
                  Qualitative Signals
                </h4>
                <div className="space-y-3">
                  {successSignals.qualitative.map((signal, idx) => (
                    <div key={idx} className="p-3 bg-white dark:bg-gray-900/50 rounded-lg border border-purple-100 dark:border-purple-800">
                      <p className="text-sm font-medium text-purple-800 dark:text-purple-200 mb-2">{signal.signal_name}</p>
                      <p className="text-xs text-purple-700 dark:text-purple-300 mb-2">{signal.description}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 italic">
                        <strong>Collection:</strong> {signal.collection_method}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

// FAB Analysis Section
interface PRDFABAnalysisSectionProps {
  mustHavesFAB: FABAnalysis[];
  niceToHavesFAB: FABAnalysis[];
  index?: number;
}

export function PRDFABAnalysisSection({ mustHavesFAB, niceToHavesFAB, index = 15 }: PRDFABAnalysisSectionProps) {
  const [isOpen, setIsOpen] = useState(false);

  const totalFAB = mustHavesFAB.length + niceToHavesFAB.length;

  return (
    <Card className="border-gray-200 dark:border-gray-700 dark:bg-gray-900/50 transition-all hover:shadow-md hover:bg-gray-50 dark:hover:bg-gray-800/70 rounded-lg overflow-hidden">
      <div
        className="px-3 py-1 cursor-pointer select-none transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-start gap-2">
          <div className="text-gray-500 dark:text-gray-400 shrink-0 mt-0.5">
            {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </div>
          <div className="flex-1 flex flex-col gap-2">
            <Badge
              variant="outline"
              className="text-amber-600 border-amber-200 dark:text-amber-400 dark:border-amber-700 px-2 py-0.5 rounded-lg bg-amber-50 dark:bg-amber-900/30 w-fit"
            >
              <Target className="w-3 h-3 mr-1" />
              <span className="text-[0.9rem] font-semibold">{index} · Feature-Advantage-Benefit Analysis</span>
            </Badge>
            <span className="text-sm font-medium text-gray-500 dark:text-brand-200">
              {totalFAB} FAB analyses ({mustHavesFAB.length} must-haves, {niceToHavesFAB.length} nice-to-haves)
            </span>
          </div>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            style={{ overflow: "hidden" }}
          >
            <CardContent className="px-4 space-y-3 pb-4">
              {/* Must-Haves FAB */}
              {mustHavesFAB.length > 0 && (
                <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-700/60">
                  <h4 className="text-sm font-semibold text-green-700 dark:text-green-400 mb-3 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    Must-Have Features FAB
                  </h4>
                  <div className="space-y-3">
                    {mustHavesFAB.map((fab, idx) => (
                      <div key={idx} className="p-3 bg-white dark:bg-gray-900/50 rounded-lg border border-green-100 dark:border-green-800">
                        <p className="text-sm font-medium text-green-800 dark:text-green-200 mb-2">{fab.feature}</p>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div className="p-2 bg-green-50 dark:bg-green-900/30 rounded">
                            <span className="font-semibold text-green-700 dark:text-green-400">Advantage:</span>
                            <p className="text-green-600 dark:text-green-300 mt-1">{fab.advantage}</p>
                          </div>
                          <div className="p-2 bg-emerald-50 dark:bg-emerald-900/30 rounded">
                            <span className="font-semibold text-emerald-700 dark:text-emerald-400">Benefit:</span>
                            <p className="text-emerald-600 dark:text-emerald-300 mt-1">{fab.benefit}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Nice-to-Haves FAB */}
              {niceToHavesFAB.length > 0 && (
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700/60">
                  <h4 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-3 flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    Nice-to-Have Features FAB
                  </h4>
                  <div className="space-y-3">
                    {niceToHavesFAB.map((fab, idx) => (
                      <div key={idx} className="p-3 bg-white dark:bg-gray-900/50 rounded-lg border border-blue-100 dark:border-blue-800">
                        <p className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">{fab.feature}</p>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div className="p-2 bg-blue-50 dark:bg-blue-900/30 rounded">
                            <span className="font-semibold text-blue-700 dark:text-blue-400">Advantage:</span>
                            <p className="text-blue-600 dark:text-blue-300 mt-1">{fab.advantage}</p>
                          </div>
                          <div className="p-2 bg-indigo-50 dark:bg-indigo-900/30 rounded">
                            <span className="font-semibold text-indigo-700 dark:text-indigo-400">Benefit:</span>
                            <p className="text-indigo-600 dark:text-indigo-300 mt-1">{fab.benefit}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

// Source Artifacts Section
interface PRDSourceArtifactsSectionProps {
  sourceArtifacts: SourceArtifacts;
  index?: number;
}

export function PRDSourceArtifactsSection({ sourceArtifacts, index = 16 }: PRDSourceArtifactsSectionProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Card className="border-gray-200 dark:border-gray-700 dark:bg-gray-900/50 transition-all hover:shadow-md hover:bg-gray-50 dark:hover:bg-gray-800/70 rounded-lg overflow-hidden">
      <div
        className="px-3 py-1 cursor-pointer select-none transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-start gap-2">
          <div className="text-gray-500 dark:text-gray-400 shrink-0 mt-0.5">
            {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </div>
          <div className="flex-1 flex flex-col gap-2">
            <Badge
              variant="outline"
              className="text-slate-600 border-slate-200 dark:text-slate-400 dark:border-slate-700 px-2 py-0.5 rounded-lg bg-slate-50 dark:bg-slate-900/30 w-fit"
            >
              <FileText className="w-3 h-3 mr-1" />
              <span className="text-[0.9rem] font-semibold">{index} · Source Artifacts Used</span>
            </Badge>
            <span className="text-sm font-medium text-gray-500 dark:text-brand-200">
              BMC {sourceArtifacts.bmc_version} · VPC {sourceArtifacts.vpc_version} · VPS {sourceArtifacts.vps_version}
            </span>
          </div>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            style={{ overflow: "hidden" }}
          >
            <CardContent className="px-4 space-y-3 pb-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700/60 text-center">
                  <span className="text-xs font-medium text-blue-600 dark:text-blue-400">BMC Version</span>
                  <p className="text-lg font-bold text-blue-700 dark:text-blue-300">{sourceArtifacts.bmc_version}</p>
                </div>
                <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-700/60 text-center">
                  <span className="text-xs font-medium text-green-600 dark:text-green-400">VPC Version</span>
                  <p className="text-lg font-bold text-green-700 dark:text-green-300">{sourceArtifacts.vpc_version}</p>
                </div>
                <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-700/60 text-center">
                  <span className="text-xs font-medium text-purple-600 dark:text-purple-400">VPS Version</span>
                  <p className="text-lg font-bold text-purple-700 dark:text-purple-300">{sourceArtifacts.vps_version}</p>
                </div>
                <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-700/60 text-center">
                  <span className="text-xs font-medium text-amber-600 dark:text-amber-400">Critique Used</span>
                  <p className="text-lg font-bold text-amber-700 dark:text-amber-300">
                    {sourceArtifacts.critique_used ? "Yes" : "No"}
                  </p>
                </div>
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

// PRD Metadata Section
interface PRDMetadataSectionProps {
  metadata: PRDMetadata;
  index?: number;
}

export function PRDMetadataSection({ metadata, index = 17 }: PRDMetadataSectionProps) {
  const [isOpen, setIsOpen] = useState(false);

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  return (
    <Card className="border-gray-200 dark:border-gray-700 dark:bg-gray-900/50 transition-all hover:shadow-md hover:bg-gray-50 dark:hover:bg-gray-800/70 rounded-lg overflow-hidden">
      <div
        className="px-3 py-1 cursor-pointer select-none transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-start gap-2">
          <div className="text-gray-500 dark:text-gray-400 shrink-0 mt-0.5">
            {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </div>
          <div className="flex-1 flex flex-col gap-2">
            <Badge
              variant="outline"
              className="text-gray-600 border-gray-200 dark:text-gray-400 dark:border-gray-700 px-2 py-0.5 rounded-lg bg-gray-50 dark:bg-gray-900/30 w-fit"
            >
              <Layers className="w-3 h-3 mr-1" />
              <span className="text-[0.9rem] font-semibold">{index} · PRD Metadata</span>
            </Badge>
            <span className="text-sm font-medium text-gray-500 dark:text-brand-200">
              Template: {metadata.template_name} ({metadata.template_code}) · Generated: {formatDate(metadata.generated_at)}
            </span>
          </div>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            style={{ overflow: "hidden" }}
          >
            <CardContent className="px-4 space-y-3 pb-4">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Template Code</span>
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{metadata.template_code}</p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Template Name</span>
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{metadata.template_name}</p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Template Version</span>
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{metadata.template_version}</p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Schema Version</span>
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{metadata.schema_version}</p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Research Used</span>
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    {metadata.research_used ? "Yes" : "No"}
                  </p>
                </div>
                {metadata.research_sources_count !== null && (
                  <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                    <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Research Sources</span>
                    <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{metadata.research_sources_count}</p>
                  </div>
                )}
              </div>
              <div className="p-3 bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-700/60">
                <div className="flex items-center gap-2 mb-1">
                  <Calendar className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                  <span className="text-xs font-medium text-brand-600 dark:text-brand-400">Generated At</span>
                </div>
                <p className="text-sm font-semibold text-brand-700 dark:text-brand-300">{formatDate(metadata.generated_at)}</p>
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
