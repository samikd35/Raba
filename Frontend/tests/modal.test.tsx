import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { Modal } from '@/components/common/Modal'

function ModalHarness() {
  const [open, setOpen] = useState(false)
  return (
    <div>
      <button onClick={()=>setOpen(true)} aria-label="open">open</button>
      <Modal open={open} onClose={()=>setOpen(false)} title="Test Modal">
        <button>first</button>
        <button>second</button>
      </Modal>
    </div>
  )
}

describe('Modal focus trap', () => {
  it('traps focus and returns on close', async () => {
    const user = userEvent.setup()
    render(<ModalHarness />)
    const open = screen.getByLabelText('open')
    await user.click(open)
    // Focus should be inside modal
    await user.tab()
    expect(screen.getByText('first')).toHaveFocus()
    await user.tab()
    expect(screen.getByText('second')).toHaveFocus()
    await user.tab()
    // cycles back
    expect(screen.getByText('first')).toHaveFocus()
    // Close by pressing Escape
    await user.keyboard('{Escape}')
    expect(open).toHaveFocus()
  })
})

