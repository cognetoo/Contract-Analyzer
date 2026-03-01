import { clearToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

export default function LogoutButton() {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button
          variant="secondary"
          className="bg-white/10 hover:bg-red-500/20 hover:text-red-200 hover:border-red-400/30 border border-white/10"
        >
          Logout
        </Button>
      </AlertDialogTrigger>

      <AlertDialogContent className="bg-slate-950 border-white/10 text-white">
        <AlertDialogHeader>
          <AlertDialogTitle>Log out?</AlertDialogTitle>
          <AlertDialogDescription className="text-white/70">
            You’ll need to login again to access your contracts.
          </AlertDialogDescription>
        </AlertDialogHeader>

        <AlertDialogFooter>
          <AlertDialogCancel className="bg-white/10 border-white/10 text-white hover:bg-white/15">
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            className="bg-red-500/80 hover:bg-red-500 text-white"
            onClick={() => {
              clearToken();
              window.location.reload();
            }}
          >
            Logout
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}