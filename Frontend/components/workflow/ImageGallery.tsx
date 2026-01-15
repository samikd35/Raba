export function ImageGallery({ images }: { images: string[] }) {
  if (!images?.length) return null
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
      {images.map((u, i) => (
        <img key={u + i} src={u} alt={`Generated image ${i + 1}`} className="w-full aspect-square object-cover rounded-md border border-[var(--border)]" />
      ))}
    </div>
  )
}

