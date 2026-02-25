'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import * as z from 'zod'
import { toast } from 'sonner'
import { Loader2, Sparkles, Upload } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { api } from '@/lib/api'
import { BorderBeam } from '@/components/ui/border-beam'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import Link from 'next/link'

type ToolListItem = {
  tool_id: string
  tool_name: string
  category: string
  is_active: boolean
}

const formSchema = z.object({
  topic: z.string().min(3, {
    message: "Topic must be at least 3 characters.",
  }).max(2000, {
    message: "Topic must not exceed 2000 characters.",
  }),
  duration_seconds: z.string(),
  aspect_ratio: z.string(),
  resolution: z.string(),
  category: z.string(),
  tool_id: z.string().optional().nullable(),
  hitl_mode: z.enum(["auto", "manual"]),
  enable_audio: z.boolean(),
  enable_subtitles: z.boolean(),
  video_model: z.enum(["veo_3_1", "veo_3_1_fast"]),
})

export default function CreatePage() {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [tools, setTools] = useState<ToolListItem[] | null>(null)
  const [isLoadingTools, setIsLoadingTools] = useState(false)
  const durationOptions = [8, 15, 22, 29, 36, 43, 50, 57, 60]

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      topic: "",
      duration_seconds: "15",
      aspect_ratio: "9:16",
      resolution: "1080p",
      category: "auto",
      tool_id: null,
      hitl_mode: "auto",
      enable_audio: true,
      enable_subtitles: false,
      video_model: "veo_3_1",
    },
  })

  // Handle file selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      if (file.size > 10 * 1024 * 1024) {
        toast.error("File size must be less than 10MB")
        return
      }
      setSelectedFile(file)
    }
  }

  // Trigger file input click
  const triggerFileInput = () => {
    document.getElementById('file-upload')?.click()
  }

  // Remove selected file
  const removeFile = () => {
    setSelectedFile(null)
    const fileInput = document.getElementById('file-upload') as HTMLInputElement
    if (fileInput) fileInput.value = ''
  }

  // Dynamically fetch tools when category changes (non-auto)
  React.useEffect(() => {
    const category = form.watch('category')
    if (!category) return

    // Reset tool selection on category change
    form.setValue('tool_id', null)

    if (category === 'auto') {
      setTools(null)
      return
    }

    ;(async () => {
      try {
        setIsLoadingTools(true)
        const res = await api.get<{ tools: ToolListItem[]; total: number }>(`/tools?category=${encodeURIComponent(category)}&is_active=true&limit=100`)
        setTools((res?.tools || []).filter(t => t.is_active))
      } catch (e) {
        setTools([])
      } finally {
        setIsLoadingTools(false)
      }
    })()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.watch('category')])

  async function onSubmit(values: z.infer<typeof formSchema>) {
    setIsSubmitting(true)
    try {
      let response;

      if (selectedFile) {
        // Multipart upload
        const formData = new FormData()
        formData.append('topic', values.topic)
        formData.append('duration_seconds', values.duration_seconds)
        formData.append('aspect_ratio', values.aspect_ratio)
        formData.append('resolution', values.resolution)
        formData.append('category', values.category)
        if (values.tool_id) {
          formData.append('tool_id', values.tool_id)
        }
        formData.append('hitl_mode', values.hitl_mode)
        formData.append('enable_audio', String(values.enable_audio))
        formData.append('enable_subtitles', String(values.enable_subtitles))
        formData.append('video_model', values.video_model)
        formData.append('reference_image', selectedFile)

        response = await api.postMultipart<{ workflow_id: string }>('/generate/with-image', formData)
      } else {
        // JSON upload
        response = await api.post<{ workflow_id: string }>('/generate', {
          ...values,
          duration_seconds: parseInt(values.duration_seconds),
        })
      }

      toast.success("Workflow initiated!", {
        description: "Redirecting to mission control...",
      })

      router.push(`/workflows/${response.workflow_id}`)
    } catch (error: any) {
      toast.error("Failed to start generation", {
        description: error.message || "Something went wrong.",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="container py-4 max-w-3xl mx-auto">
      <div className="flex flex-col items-center text-center gap-2 mb-4 w-full">
        <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent">
          Create Your Video
        </h1>
        <p className="text-muted-foreground text-lg">
          Transform your ideas into viral YouTube Shorts with RABA.
        </p>
      </div>

      <Card className="relative overflow-hidden border-muted/40 shadow-xl bg-card/50 backdrop-blur-md">
        <BorderBeam size={300} duration={12} delay={9} colorFrom="#6366F1" colorTo="#06B6D4" />

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
            <CardContent className="space-y-6 pt-6">

              <FormField
                control={form.control}
                name="topic"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Topic / Concept</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Textarea
                          placeholder="Describe your video idea in detail..."
                          className="min-h-[120px] resize-none text-base pr-12 pb-10" // Added padding for button
                          {...field}
                        />

                        {/* Integrated Image Upload & Preview Area */}
                        <div className="absolute bottom-3 left-3 flex items-center gap-2 z-10">
                          <Input
                            id="file-upload"
                            type="file"
                            className="hidden"
                            accept="image/jpeg,image/png,image/webp"
                            onChange={handleFileChange}
                          />

                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-8 gap-2 text-xs rounded-full shadow-sm hover:bg-muted"
                            onClick={triggerFileInput}
                          >
                            <Upload className="h-3.5 w-3.5" />
                            {selectedFile ? 'Change Image' : 'Attach Image'}
                          </Button>

                          {/* Model Picker Dropdown */}
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="h-8 text-xs rounded-full shadow-sm hover:bg-muted"
                              >
                                {form.watch('video_model') === 'veo_3_1' ? 'Model: Veo 3.1' : 'Model: Veo 3.1 Fast'}
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="start" className="min-w-[12rem]">
                              <DropdownMenuItem onClick={() => form.setValue('video_model', 'veo_3_1')}>
                                Veo 3.1 (Quality)
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => form.setValue('video_model', 'veo_3_1_fast')}>
                                Veo 3.1 Fast (Speed)
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>

                          {selectedFile && (
                            <div className="flex items-center gap-2 bg-background/80 rounded-full px-3 py-1 border text-xs animate-in fade-in zoom-in">
                              <span className="max-w-[100px] truncate">{selectedFile.name}</span>
                              <button
                                type="button"
                                onClick={(e) => { e.stopPropagation(); removeFile(); }}
                                className="text-muted-foreground hover:text-foreground"
                              >
                                ×
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormField
                  control={form.control}
                  name="duration_seconds"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Duration</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select duration" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {durationOptions.map((duration) => (
                            <SelectItem key={duration} value={String(duration)}>
                              {duration === 60 ? `${duration} Seconds (Max)` : `${duration} Seconds`}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="category"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Visual Style</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select style" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="auto">Auto (AI Selects)</SelectItem>
                          <SelectItem value="realistic">Realistic</SelectItem>
                          <SelectItem value="anime">Anime</SelectItem>
                          <SelectItem value="animation">Animation</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Tool selector (optional), enabled when category != auto */}
                <FormField
                  control={form.control}
                  name="tool_id"
                  render={({ field }) => (
                    <FormItem>
                      <div className="flex items-center justify-between">
                        <FormLabel>Tool (Optional)</FormLabel>
                        {form.watch('category') !== 'auto' && (
                          <div className="flex items-center gap-3">
                            <Link
                              href={`/tools${form.watch('category') ? `?category=${encodeURIComponent(form.watch('category'))}` : ''}`}
                              className="text-primary hover:underline text-xs"
                              target="_blank"
                            >
                              View tools
                            </Link>
                            {form.watch('tool_id') && (
                              <Link
                                href={`/tools?tool=${encodeURIComponent(form.watch('tool_id') || '')}${form.watch('category') ? `&category=${encodeURIComponent(form.watch('category'))}` : ''}`}
                                className="text-primary hover:underline text-xs"
                                target="_blank"
                              >
                                View tool details
                              </Link>
                            )}
                          </div>
                        )}
                      </div>
                      <Select
                        onValueChange={field.onChange}
                        defaultValue={field.value ?? undefined}
                        disabled={form.watch('category') === 'auto' || isLoadingTools || (tools?.length ?? 0) === 0}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue
                              placeholder={
                                form.watch('category') === 'auto'
                                  ? 'Select a category to choose a tool'
                                  : isLoadingTools
                                    ? 'Loading tools...'
                                    : (tools?.length ?? 0) === 0
                                      ? 'No tools available in this category'
                                      : 'Select a tool (optional)'
                              }
                            />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {(tools || []).map((t) => (
                            <SelectItem key={t.tool_id} value={t.tool_id}>
                              {t.tool_name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {/* Links moved beside the picker label for better use of space */}
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormField
                  control={form.control}
                  name="aspect_ratio"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Aspect Ratio</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select aspect ratio" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="9:16">9:16 (Shorts/Reels/TikTok)</SelectItem>
                          <SelectItem value="16:9">16:9 (Cinematic)</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="resolution"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Resolution</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select resolution" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="720p">720p (Fast)</SelectItem>
                          <SelectItem value="1080p">1080p (HQ)</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="space-y-4 rounded-lg border p-4 bg-muted/20">
                <div className="flex items-center justify-between">
                  <FormField
                    control={form.control}
                    name="hitl_mode"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg p-0 space-y-0 w-full">
                        <div className="space-y-0.5">
                          <FormLabel className="text-base">Manual Approval Mode</FormLabel>
                          <FormDescription>
                            Review & approve each step (Script, Images, etc.).
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value === 'manual'}
                            onCheckedChange={(checked) => field.onChange(checked ? 'manual' : 'auto')}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2 border-t border-muted/50">
                  <FormField
                    control={form.control}
                    name="enable_audio"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg p-0 space-y-0">
                        <div className="space-y-0.5">
                          <FormLabel className="text-sm font-medium">Generate Audio</FormLabel>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="enable_subtitles"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg p-0 space-y-0">
                        <div className="space-y-0.5">
                          <FormLabel className="text-sm font-medium">Subtitles</FormLabel>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                </div>
              </div>

              {/* Reference Image Upload Removed - Integrated above */}

            </CardContent>
            <CardFooter className="flex justify-end border-t pt-6 bg-muted/10">
              <Button
                type="submit"
                size="lg"
                className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-[0_0_20px_rgba(99,102,241,0.5)]"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Initializing...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2 h-4 w-4" />
                    Generate Video
                  </>
                )}
              </Button>
            </CardFooter>
          </form>
        </Form>
      </Card>
    </div>
  )
}
