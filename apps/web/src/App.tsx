import { createFleetClient } from "./api/client";
import { FleetView } from "./components/FleetView";

const client = createFleetClient();

export function App() {
  return <FleetView client={client} />;
}
