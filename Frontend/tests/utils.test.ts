import { describe, expect, it } from 'vitest'
import { secondsToHms, formatCurrency } from '@/lib/utils'

describe('utils', () => {
  it('secondsToHms formats durations', () => {
    expect(secondsToHms(5)).toBe('5s')
    expect(secondsToHms(65)).toBe('1m 5s')
    expect(secondsToHms(3665)).toBe('1h 1m 5s')
  })

  it('formatCurrency formats USD', () => {
    const s = formatCurrency(12.345)
    expect(s).toMatch(/\$\s?12\.35|12\.35\s?\$/) // locale differences
  })
})

