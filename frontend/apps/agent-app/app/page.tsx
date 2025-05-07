import { currentUser, auth } from "@clerk/nextjs/server";
import { Card } from "../components/ui/card";
import Sidebar from "../components/sidebar";
import { redirect } from "next/navigation";

const HomePage = async () => {

  //MJ: ******** API TESTING CODE STARTS ***************
  const user = await currentUser();
  const { userId, getToken } = await auth() 
  const token = await getToken({ template: "FastAPI" });
console.log(token);

  if (!token) {
    throw new Error("Failed to get access token");
  }
  const res = await fetch(`http://127.0.0.1:8000/api/users/${user?.id}`, {
    method: "GET",
    headers: {
      "Authorization": `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    throw new Error("Failed to Fetch User Data");
  }
  const user_data = await res.json();
  const name = user?.firstName+" "+user?.lastName;
  // HZ: Store Organization Using Full Name Of User In Database

  if (user_data.data.organization_id == null) {
      const token = await getToken();
      const res = await fetch("http://127.0.0.1:8000/api/organizations", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${token}`,
            },
            body: JSON.stringify({ name }),
          });
  }
  // HZ: Fetch Agents Data From Database
  const response = await fetch('http://127.0.0.1:8000/api/agents', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });  
  const data = await response.json()
  const agents = data?.data ?? [];
  if (!token) {
    throw new Error("Failed to get access token");
  }

 // HZ: Fetch Knowledge base Count From Database
 const knowledge_response = await fetch('http://127.0.0.1:8000/api/org_knowledge_count', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }); 
    const knowledge_data = await knowledge_response.json()

    const knowledge_base = knowledge_data.total_knowledge_bases ?? 0;
    if (!token) {
      throw new Error("Failed to get access token");
    }
   // HZ: Fetch Conversation Count From Database
 const conversation_response = await fetch('http://127.0.0.1:8000/api/conversations/count', {
  headers: {
    Authorization: `Bearer ${token}`,
  },
}); 
const conversation_data = await conversation_response.json()
const conversation_count = conversation_data.total_conversations ?? 0;
if (!token) {
  throw new Error("Failed to get access token");
}
  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
        Welcome {user?.firstName} {user?.lastName} !
        </h2>
        <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    <Card className="p-6 shadow rounded-2xl bg-white dark:bg-gray-800">
      <h3 className="text-sm font-medium text-gray-800 dark:text-gray-400">Total Agents</h3>
      <p className="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">{agents.length}</p>
    </Card>
    
    <Card className="p-6 shadow rounded-2xl bg-white dark:bg-gray-800">
      <h3 className="text-sm font-medium text-gray-800 dark:text-gray-400">Total Chats</h3>
      <p className="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">{conversation_count}</p> {/* Replace with dynamic data */}

    </Card>
    <Card className="p-6 shadow rounded-2xl bg-white dark:bg-gray-800">
      <h3 className="text-sm font-medium text-gray-800 dark:text-gray-400">Total Knowledge Bases</h3>
      <p className="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">{knowledge_base}</p> {/* Replace with dynamic data */}
    </Card>

  {/* Add more cards as needed */}
</div>
<div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
<Card className="p-6 shadow rounded-2xl bg-white dark:bg-gray-800 col-span-1 md:col-span-2 lg:col-span-3">
  <h3 className="text-sm font-medium text-gray-800 dark:text-gray-400 mb-4">Latest Agents</h3>
  
  <div className="overflow-auto max-h-[300px]">
    <table className="min-w-full table-auto text-sm text-left text-gray-700 dark:text-gray-300">
      <thead className="bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 sticky top-0">
        <tr>
          <th className="px-4 py-2">Name</th>
          <th className="px-4 py-2">System Prompt</th>
          <th className="px-4 py-2">Model Name</th>
          <th className="px-4 py-2">Temprature</th>
          <th className="px-4 py-2">Public</th>
        </tr>
      </thead>
      <tbody>
        {agents
          .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
          .slice(0, 5)
          .map((agent: any) => (
            <tr key={agent.id} className="border-b border-gray-200 dark:border-gray-600">
              <td className="px-4 py-2">{agent.name}</td>
              <td className="px-4 py-2">{agent.config.system_prompt}</td>
              <td className="px-4 py-2">{agent.config.model_name}</td>
              <td className="px-4 py-2">{agent.config.temperature}</td>
              <td className="px-4 py-2">
              {agent.is_public == true ? (
                  <span className="text-green-500 font-bold">✔</span>
                ) : (
                  <span className="text-red-500 font-bold">✘</span>
                )}
              </td>
            </tr>
          ))}
        {agents.length === 0 && (
          <tr>
            <td colSpan={3} className="px-4 py-2 text-center text-gray-500">
              No agents found.
            </td>
          </tr>
        )}
      </tbody>
    </table>
  </div>
</Card>


</div>
      {/* <p className="text-gray-700 dark:text-gray-400 mt-2">
        This is result of Backend API Call.
        {JSON.stringify(data)}
      </p> */}
    </div>
  );
};

//MJ: ******** API TESTING CODE ENDS ***************

export default HomePage;
