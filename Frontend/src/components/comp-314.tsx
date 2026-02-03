import { CircleAlertIcon } from "lucide-react"
import { ConfirmDialog } from "@/components/ui/confirm-dialog"
import { Button } from "@/components/ui/button"

export default function AlertComponent() {
  return (
    <ConfirmDialog
      trigger={
        <Button variant="outline">Alert dialog with icon</Button>
      }
      title="Are you sure?"
      description="Are you sure you want to delete your account? All your data will be removed."
      icon={<CircleAlertIcon className="opacity-80" size={16} />}
      confirmLabel="Confirm"
      cancelLabel="Cancel"
    />
  )
}
