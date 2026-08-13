import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useParams } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { M34Provider } from "./context/M34Context";

const NewExperimentPage = lazy(() => import("./pages/M34NewExperimentPage"));
const SetupPage = lazy(() => import("./pages/M34SetupPage"));
const LiveExperimentPage = lazy(() => import("./pages/M34LivePage"));
const ComparePage = lazy(() => import("./pages/M34ComparePage"));
const InfoPage = lazy(() => import("./pages/M34InfoPage"));

function PageLoader() {
  return <div className="route-loader"><span className="spinner" /><strong>正在加载工作台…</strong></div>;
}

export default function App() {
  return (
    <M34Provider>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route element={<AppShell />}>
            <Route element={<NewExperimentPage />} path="/experiments/new" />
            <Route element={<SetupPage />} path="/experiments/:id/setup" />
            <Route element={<LiveExperimentPage />} path="/experiments/:id/live" />
            <Route element={<InfoPage kind="participants" />} path="/experiments/:id/participants" />
            <Route element={<LegacyInterventionRedirect />} path="/experiments/:id/intervention" />
            <Route element={<ComparePage />} path="/experiments/:id/compare" />
            <Route element={<InfoPage kind="province" />} path="/experiments/:id/provinces/:provinceCode" />
            <Route element={<InfoPage kind="methods" />} path="/experiments/:id/methods" />
            <Route element={<Navigate replace to="/experiments/new" />} path="*" />
          </Route>
        </Routes>
      </Suspense>
    </M34Provider>
  );
}

function LegacyInterventionRedirect() {
  const { id } = useParams();
  return <Navigate replace to={`/experiments/${id}/setup?step=design`} />;
}
