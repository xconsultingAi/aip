import { fetchData } from "../../utils/server/api";
import AgentList from "./AgentList";
import AgentEditor from "./AgentEditor";

export default async function AgentsPage() {
  //MJ: Fetch agents data from the server
  //TODO: Make the URL Dynamic from .env
  const agents = await fetchData({
    url: "http://127.0.0.1:8000/api/agents/",
  });

  return (
    <div className="flex h-full bg-gray-200 dark:bg-gray-800">
      {/* MJ: Agent List */}
      <div className="w-1/4 bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-gray-400 rounded-lg ">
        <AgentList agents={agents} />
      </div>

      {/* MJ: Agent Editor */}
      <div className="w-3/4 bg-gray-100 bg-gray-200 dark:bg-gray-800">
        <AgentEditor />
      </div>
    </div>
  );
}
