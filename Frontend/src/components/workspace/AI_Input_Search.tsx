"use client";

import { Send } from "lucide-react";
import { useState, useEffect } from "react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { useAutoResizeTextarea } from "@/hooks/use-auto-resize-textarea";

interface AI_Input_SearchProps {
    initialValue?: string;
    onSubmit?: (value: string) => void;
}

export default function AI_Input_Search({ initialValue = "", onSubmit }: AI_Input_SearchProps) {
    const [value, setValue] = useState(initialValue);
    const { textareaRef, adjustHeight } = useAutoResizeTextarea({
        minHeight: 52,
        maxHeight: 200,
    });
    const [isFocused, setIsFocused] = useState(false);

    useEffect(() => {
        if (initialValue && initialValue !== value) {
            setValue(initialValue);
            // Adjust height after setting initial value
            setTimeout(() => {
                if (adjustHeight) {
                    adjustHeight();
                }
            }, 100);
        }
    }, [initialValue]);

    const handleSubmit = () => {
        if (onSubmit && value.trim()) {
            onSubmit(value.trim());
        }
        setValue("");
        adjustHeight(true); 
    };

    const handleFocus = () => {
        setIsFocused(true);
    };

    const handleBlur = () => {
        setIsFocused(false);
    };

    const handleContainerClick = () => {
        if (textareaRef.current) {
            textareaRef.current.focus();
        }
    };

    return (
        <div className="w-full py-4">
            <div className="relative max-w-xl w-full mx-auto">
                <div
                    role="textbox"
                    tabIndex={0}
                    aria-label="Search input container"
                    className={cn(
                        "relative flex flex-col rounded-xl transition-all duration-200 w-full text-left cursor-text",
                        "ring-1 ring-black/10 dark:ring-white/10",
                        isFocused && "ring-black/20 dark:ring-white/20"
                    )}
                    onClick={handleContainerClick}
                    onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                            handleContainerClick();
                        }
                    }}
                >
                    <div className="overflow-y-auto max-h-[200px]">
                        <Textarea
                            id="ai-input-04"
                            value={value}
                            placeholder="Enter your problem statement…"
                            className="w-full rounded-xl rounded-b-none px-4 py-3 bg-brand-25 dark:bg-[#101828] border-none dark:text-white placeholder:text-black/70 dark:placeholder:text-white/70 resize-none focus-visible:ring-0 leading-[1.2]"
                            ref={textareaRef}
                            onFocus={handleFocus}
                            onBlur={handleBlur}
                            onKeyDown={(e) => {
                                if (e.key === "Enter" && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSubmit();
                                }
                            }}
                            onChange={(e) => {
                                setValue(e.target.value);
                                adjustHeight();
                            }}
                        />
                    </div>

                    <div className="h-12 bg-brand-25 dark:bg-[#101828] rounded-b-xl">
                        <div className="absolute right-3 bottom-3">
                            <button
                                type="button"
                                onClick={handleSubmit}
                                className={cn(
                                    "rounded-lg p-2 transition-colors",
                                    value
                                        ? "bg-brand-500/15 text-brand-500 hover:bg-brand-500/20"
                                        : "bg-black/5 dark:bg-white/5 text-black/40 dark:text-white/40 hover:text-black dark:hover:text-white cursor-pointer"
                                )}
                            >
                                <Send className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
