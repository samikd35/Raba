import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";

interface InsufficientCreditsModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  buttonText1?: string;
  buttonText2?: string;
}

export function InsufficientCreditsModal({
  isOpen,
  onClose,
  title = "Insufficient Credits",
  description = "You don't have enough credits to refine your idea. Please purchase more credits to continue.",
  buttonText1 = "Request Credit",
  buttonText2 = "Close"
}: InsufficientCreditsModalProps) {
  const router = useRouter();

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <DialogDescription>
          {description}
        </DialogDescription>
        <div className="mt-4 flex justify-end items-center gap-2">
          <Button variant="default" onClick={() => router.push("/request-credit")}>
            {buttonText1}
          </Button>
          <Button variant="destructive" onClick={onClose}>
            {buttonText2}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
