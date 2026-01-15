"use client"
import { Component, ReactNode } from 'react'

export class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean; error?: Error | null }> {
  constructor(props: any) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error: Error) { return { hasError: true, error } }
  componentDidCatch(error: Error, info: any) { console.error('ErrorBoundary', error, info) }
  render() {
    if (this.state.hasError) {
      return (
        <div className="card-surface p-6 rounded-xl">
          <h2 className="text-lg font-semibold">Something went wrong</h2>
          <p className="text-sm opacity-80 mt-1">{this.state.error?.message}</p>
          <button className="mt-3 px-3 py-2 rounded-md border focus-ring" onClick={() => this.setState({ hasError: false, error: null })}>Try again</button>
        </div>
      )
    }
    return this.props.children
  }
}

