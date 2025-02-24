import { fetchData } from "../../utils/server/api";
import AgentListWrapper from "./AgentListWrapper";

// MJ: Fetch agents on the server
export default async function AgentsPage() {
  const agents = await fetchData({
    url: "http://127.0.0.1:8000/api/agents/",
  });

  return <AgentListWrapper agents={agents} />;
}
