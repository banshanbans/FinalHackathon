import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { PolicyScopeProvider } from "./context/PolicyScopeContext";

const NewExperimentPage = lazy(() => import("./pages/NewExperimentPage"));
const LiveExperimentPage = lazy(() => import("./pages/LiveExperimentPage"));
const InterventionPage = lazy(() => import("./pages/InterventionPage"));
const ComparePage = lazy(() => import("./pages/ComparePage"));

function PageLoader() {
  return <div className="route-loader"><span className="spinner" /><strong>正在加载工作台…</strong></div>;
}

export default function App() {
  return (
    <PolicyScopeProvider>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route element={<AppShell />}>
            <Route element={<NewExperimentPage />} path="/experiments/new" />
            <Route element={<LiveExperimentPage />} path="/experiments/:id/live" />
            <Route element={<InterventionPage />} path="/experiments/:id/intervention" />
            <Route element={<ComparePage />} path="/experiments/:id/compare" />
            <Route element={<Navigate replace to="/experiments/new" />} path="*" />
          </Route>
        </Routes>
      </Suspense>
    </PolicyScopeProvider>
  );
}
