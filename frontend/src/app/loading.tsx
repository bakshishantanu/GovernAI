import { LoadingScreen } from "@/components/loading-screen";

// Next.js's Suspense-based fallback — only fires for a route segment
// that's genuinely doing async server work. Kept as a backstop; the
// RouteTransition in the root layout is what actually guarantees this
// shows on every navigation and hard reload.
export default function Loading() {
  return <LoadingScreen />;
}
