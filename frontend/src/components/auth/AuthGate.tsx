import { useEffect, useState } from "react";
import { me } from "@/api";
import { clearToken, getToken } from "@/lib/auth";
import AuthScreen from "../AuthScreen";

export default function AuthGate(props: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    (async () => {
      const token = getToken();

      if (!token) {
        setAuthenticated(false);
        setLoading(false);
        return;
      }

      try {
        await me();
        setAuthenticated(true);
      } catch {
        clearToken();
        setAuthenticated(false);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-white">
        Loading...
      </div>
    );
  }

  if (!authenticated) {
    return <AuthScreen />;
  }

  return <>{props.children}</>;
}