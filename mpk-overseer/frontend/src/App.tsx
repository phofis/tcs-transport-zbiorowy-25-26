import { AppProvider } from "@/context/AppContext";

import Map from "./components/Map";
import Sidebar from "./components/Sidebar";

export default function App() {
  return (
    <AppProvider>
      <div className="flex h-screen w-screen">
        <Sidebar />
        <div className="min-w-0 flex-1">
          <Map />
        </div>
      </div>
    </AppProvider>
  );
}
