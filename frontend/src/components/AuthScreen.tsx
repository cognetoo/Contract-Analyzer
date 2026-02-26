import { useState } from "react";
import { loginUser, registerUser } from "@/api";
import { setToken, clearToken } from "@/lib/auth";

export default function AuthScreen() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    setError("");
    setLoading(true);
    clearToken();

    try {
      const res =
        mode === "login"
          ? await loginUser(email, password)
          : await registerUser(email, password);

      setToken(res.access_token);
      window.location.reload();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Auth failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 text-white">
      <div className="w-80 space-y-4">
        <h1 className="text-xl font-bold">Contract Analyzer</h1>

        <input
          className="w-full p-2 bg-black/40 rounded"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <input
          className="w-full p-2 bg-black/40 rounded"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {error && <div className="text-red-400 text-sm">{error}</div>}

        <button
          onClick={submit}
          disabled={loading}
          className="w-full bg-blue-600 p-2 rounded"
        >
          {loading ? "Please wait..." : mode === "login" ? "Login" : "Register"}
        </button>

        <button
          className="text-xs text-gray-400"
          onClick={() =>
            setMode(mode === "login" ? "register" : "login")
          }
        >
          {mode === "login"
            ? "Create account"
            : "Already have account? Login"}
        </button>
      </div>
    </div>
  );
}