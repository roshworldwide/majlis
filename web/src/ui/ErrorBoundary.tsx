import { Component, type ReactNode } from 'react';

interface Props {
  onError: (msg: string) => void;
  children: ReactNode;
  fallback?: ReactNode;
}
interface S {
  failed: boolean;
}

/** Catches render errors in the 3D canvas and hands over to the 2D Experience. Never shows a stack trace. */
export class ErrorBoundary extends Component<Props, S> {
  state: S = { failed: false };
  static getDerivedStateFromError(): S {
    return { failed: true };
  }
  componentDidCatch(err: unknown): void {
    const msg = err instanceof Error ? err.message : String(err);
    this.props.onError(msg);
  }
  render(): ReactNode {
    if (this.state.failed) return this.props.fallback ?? null;
    return this.props.children;
  }
}
