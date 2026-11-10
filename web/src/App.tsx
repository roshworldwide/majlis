import { lazy, Suspense, useEffect } from 'react';
import { useStore } from './state/store';
import { ErrorBoundary } from './ui/ErrorBoundary';
import Stage2D from './fallback2d/Stage2D';
import { Overlay } from './ui/Overlay';
import { useKeyboard } from './ui/useKeyboard';

const Stage3D = lazy(() => import('./acts/Stage3D'));

function Loading() {
  return (
    <div className="boot" role="status" aria-live="polite">
      <div className="boot-mark" aria-hidden="true">
        <svg viewBox="0 0 32 32" width="40" height="40">
          <polygon points="16,2 28,9 28,23 16,30 4,23 4,9" fill="none" stroke="#E9C46A" strokeWidth="1.5" />
        </svg>
      </div>
      <div>Loading the MAJLIS Experience…</div>
    </div>
  );
}

function Fatal({ msg }: { msg: string }) {
  return (
    <div className="boot fatal" role="alert">
      <h1>MAJLIS</h1>
      <p>The simulation replay could not be loaded.</p>
      <p className="mono small">{msg}</p>
      <p className="small">If you opened the multi-file build from disk, use the single-file build (majlis_experience.html) or serve the folder over HTTP.</p>
    </div>
  );
}

export function App() {
  const status = useStore((s) => s.status);
  const error = useStore((s) => s.error);
  const renderer = useStore((s) => s.renderer);
  const present = useStore((s) => s.present);
  const lang = useStore((s) => s.lang);
  const fallbackTo2D = useStore((s) => s.fallbackTo2D);
  useKeyboard();

  useEffect(() => {
    document.documentElement.lang = lang === 'ar' ? 'ar' : 'en';
  }, [lang]);

  if (status === 'loading') return <Loading />;
  if (status === 'error') return <Fatal msg={error ?? 'unknown error'} />;

  return (
    <div className={`app ${present ? 'present' : ''}`} data-renderer={renderer} data-testid="app">
      <div className="stage" aria-hidden={false}>
        {renderer === '3d' ? (
          <ErrorBoundary onError={(m) => fallbackTo2D(`render error: ${m}`)}>
            <Suspense fallback={<div className="stage-loading" role="status">Preparing the 3D scene…</div>}>
              <Stage3D />
            </Suspense>
          </ErrorBoundary>
        ) : (
          <ErrorBoundary onError={() => undefined} fallback={<div className="stage-loading">2D stage unavailable — the story continues in the panels.</div>}>
            <Stage2D />
          </ErrorBoundary>
        )}
      </div>
      <Overlay />
    </div>
  );
}
