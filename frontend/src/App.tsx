import AuthGate from "./components/auth/AuthGate";
import AppContent from "./AppContent";

export default function App() {
  return (
    <AuthGate>
      <AppContent />
    </AuthGate>
  );
}