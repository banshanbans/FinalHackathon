import { createContext, useContext, type ReactNode } from "react";

import { usePolicyScope, type PolicyScopeFlow } from "../hooks/usePolicyScope";

const PolicyScopeContext = createContext<PolicyScopeFlow | null>(null);

export function PolicyScopeProvider({ children }: { children: ReactNode }) {
  const flow = usePolicyScope();
  return <PolicyScopeContext.Provider value={flow}>{children}</PolicyScopeContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function usePolicyScopeContext() {
  const value = useContext(PolicyScopeContext);
  if (!value) throw new Error("PolicyScopeProvider is missing");
  return value;
}
