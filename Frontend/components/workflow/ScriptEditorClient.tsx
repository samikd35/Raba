"use client"
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { useEffect } from 'react'

export function ScriptEditorClient({ value, onChange, readOnly = false }: { value: string; onChange: (html: string) => void; readOnly?: boolean }) {
  const editor = useEditor({
    extensions: [StarterKit],
    content: value,
    editable: !readOnly,
    editorProps: {
      attributes: {
        class: 'min-h-[200px] p-3 focus:outline-none',
      },
    },
    onUpdate({ editor }) {
      onChange(editor.getHTML())
    },
  })

  useEffect(() => {
    return () => editor?.destroy()
  }, [editor])

  return (
    <div className="rounded-md border border-[var(--border)]">
      {!readOnly && (
        <div className="border-b border-[var(--border)] px-2 py-1 text-xs opacity-70 flex gap-2">
          <button className="hover:opacity-100" onClick={() => editor?.chain().focus().toggleBold().run()} aria-label="Bold">B</button>
          <button className="hover:opacity-100" onClick={() => editor?.chain().focus().toggleItalic().run()} aria-label="Italic">I</button>
          <button className="hover:opacity-100" onClick={() => editor?.chain().focus().toggleBulletList().run()} aria-label="Bulleted list">•</button>
        </div>
      )}
      <EditorContent editor={editor} />
    </div>
  )
}
