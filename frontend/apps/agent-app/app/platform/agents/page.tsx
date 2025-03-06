import { auth } from "@clerk/nextjs/server";
import { fetchData } from "../../utils/server/api";
import AgentListWrapper from "./AgentListWrapper";

// MJ: Fetch agents on the server
export default async function AgentsPage() {
  let agents = [];

  try {
    agents = await fetchData({
      url: "http://127.0.0.1:8000/api/agents/",
    });
  } catch (error: any) {

    //HZ: Check if the error is a 404, meaning no agents exist yet
    if (error.message.includes("404")) {
      agents = []; //HZ: Treat 404 as "no agents exist"
    } else {
      return <div className="text-red-500">Error loading agents. Please try again.</div>;
    }
  }

  return <AgentListWrapper agents={agents} />;
}
