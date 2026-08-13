import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useParams } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { V32Provider } from "./context/V32Context";

const NewExperimentPage = lazy(() => import("./pages/V32NewExperimentPage"));
const SetupPage = lazy(() => import("./pages/V32SetupPage"));
const LiveExperimentPage = lazy(() => import("./pages/V32LivePage"));
const ParticipantsPage = lazy(() => import("./pages/V32ParticipantsPage"));
const ComparePage = lazy(() => import("./pages/V32ComparePage"));
const ProvinceAgentPage = lazy(() => import("./pages/V32ProvincePage"));
const MethodsPage = lazy(() => import("./pages/V32MethodsPage"));

function PageLoader() {
  return <div className="route-loader"><span className="spinner" /><strong>正在加载工作台…</strong></div>;
}

export default function App() {
  return (
    <V32Provider>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route element={<AppShell />}>
            <Route element={<NewExperimentPage />} path="/experiments/new" />
            <Route element={<SetupPage />} path="/experiments/:id/setup" />
            <Route element={<LiveExperimentPage />} path="/experiments/:id/live" />
            <Route element={<ParticipantsPage />} path="/experiments/:id/participants" />
            <Route element={<LegacyInterventionRedirect />} path="/experiments/:id/intervention" />
            <Route element={<ComparePage />} path="/experiments/:id/compare" />
            <Route element={<ProvinceAgentPage />} path="/experiments/:id/provinces/:provinceCode" />
            <Route element={<MethodsPage />} path="/experiments/:id/methods" />
            <Route element={<Navigate replace to="/experiments/new" />} path="*" />
          </Route>
        </Routes>
      </Suspense>
    </V32Provider>
  );
}

function LegacyInterventionRedirect() {
  const { id } = useParams();
  return <Navigate replace to={`/experiments/${id}/setup?step=design`} />;
}
