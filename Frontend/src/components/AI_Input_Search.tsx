"use client";

import { Send } from "lucide-react";
import { useState, useEffect } from "react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { useAutoResizeTextarea } from "@/hooks/use-auto-resize-textarea";

interface AI_Input_SearchProps {
    initialValue?: string;
    onSubmit?: (value: string) => void;
    placeholder?: string;
    disabled?: boolean;
    autoFocus?: boolean;
    maxLength?: number;
    showCounter?: boolean;
}

export default function AI_Input_Search({
    initialValue = "",
    onSubmit,
    placeholder = "Enter your problem statement…",
    disabled = false,
    autoFocus = false,
    maxLength = 1000,
    showCounter = true,
}: AI_Input_SearchProps) {
    const [value, setValue] = useState(initialValue);
    const { textareaRef, adjustHeight } = useAutoResizeTextarea({
        minHeight: 52,
        maxHeight: 200,
    });
    const [isFocused, setIsFocused] = useState(false);
    
    const isOverLimit = maxLength > 0 && value.length > maxLength;
    const isSubmitDisabled = disabled || isOverLimit || !value.trim();

    useEffect(() => {
        console.log(`initialValue: ${initialValue}`);
        console.log(`value: ${value}`);
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
        if (isSubmitDisabled) return;
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
        if (disabled) return;
        if (textareaRef.current) {
            textareaRef.current.focus();
        }
    };

    return (
        <div className="w-full pt-4 pb-1">
            <div className="relative max-w-xl w-full mx-auto">
                <div
                    role="textbox"
                    tabIndex={0}
                    aria-label="Search input container"
                    className={cn(
                        "relative flex flex-col rounded-xl transition-all duration-200 w-full text-left",
                        "ring-1 ring-black/10 dark:ring-white/10",
                        isFocused && "ring-black/20 dark:ring-white/20",
                        disabled ? "cursor-not-allowed opacity-60" : "cursor-text"
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
                            placeholder={placeholder}
                            disabled={disabled}
                            autoFocus={autoFocus}
                            className={cn(
                                "w-full rounded-xl rounded-b-none px-4 py-3 bg-brand-25 dark:bg-[#101828] border-none dark:text-white placeholder:text-black/70 dark:placeholder:text-white/70 resize-none focus-visible:ring-0 leading-[1.2]",
                                disabled && "cursor-not-allowed"
                            )}
                            ref={textareaRef}
                            onFocus={handleFocus}
                            onBlur={handleBlur}
                            onKeyDown={(e) => {
                                if (e.key === "Enter" && !e.shiftKey && !isSubmitDisabled) {
                                    e.preventDefault();
                                    handleSubmit();
                                }
                            }}
                            onChange={(e) => {
                                if (disabled) return;
                                setValue(e.target.value);
                                adjustHeight();
                            }}
                        />
                    </div>

                    <div className="h-12 bg-brand-25 dark:bg-[#101828] rounded-b-xl flex items-center justify-between px-4">
                        {/* Character Counter */}
                        {showCounter && maxLength > 0 && (
                            <span
                                className={cn(
                                    "text-xs transition-colors",
                                    isOverLimit
                                        ? "text-red-500 dark:text-red-400 font-medium"
                                        : value.length > maxLength * 0.9
                                            ? "text-yellow-600 dark:text-yellow-400"
                                            : "text-black/40 dark:text-white/40"
                                )}
                            >
                                {value.length.toLocaleString()} / {maxLength.toLocaleString()}
                            </span>
                        )}
                        {!showCounter && <span />}
                        <button
                            type="button"
                            onClick={handleSubmit}
                            disabled={isSubmitDisabled}
                            className={cn(
                                "rounded-lg p-2 transition-colors",
                                isSubmitDisabled
                                    ? "bg-black/5 dark:bg-white/5 text-black/20 dark:text-white/20 cursor-not-allowed"
                                    : "bg-brand-500/15 text-brand-500 hover:bg-brand-500/20 cursor-pointer"
                            )}
                        >
                            <Send className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
