"use client";

import { useAuth } from "@clerk/nextjs";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function CreateAgentPage() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [organization_id, setOrganizationId] = useState("");
  const { getToken } = useAuth(); // Get token function
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Prepare the data to be sent to the API
    const agentData = { name, description, organization_id };
    const token = await getToken();
    try {
      // Send POST request to the API route
      const res = await fetch("http://127.0.0.1:8000/api/agents", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify(agentData), // Send form data as JSON
      });

      // Check if the response is successful
      if (!res.ok) {
        const errorText = await res.text(); // Get the response body as text if it's not valid JSON
        console.error("Error response:", errorText);
        throw new Error("Failed to create agent. Server responded with an error.");
      }

      // Attempt to parse the JSON response
      const data = await res.json();
      console.log("Agent created successfully:", data);

      // Navigate to agent list page after successful creation
      router.push("/platform/agents");
    } catch (error) {
      console.error("Error creating agent:", error);
    }
  };

  return (
    <div className="p-6 max-w-lg mx-auto bg-white shadow-lg rounded-lg">
      <h1 className="text-2xl font-bold mb-4">Create a New Agent</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Name Input */}
        <div>
          <label className="block font-medium">Agent Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter agent name"
            className="w-full p-2 border rounded"
            required
          />
        </div>

        {/* Description Input */}
        <div>
          <label className="block font-medium">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Enter agent description"
            className="w-full p-2 border rounded"
            rows={3}
          ></textarea>
        </div>

        {/* Organization ID Input */}
        <div>
          <label className="block font-medium">Organization ID</label>
          <input
            type="text"
            value={organization_id}
            onChange={(e) => setOrganizationId(e.target.value)}
            placeholder="Enter organization ID"
            className="w-full p-2 border rounded"
            required
            // disabled // Disable input for organization ID
          />
        </div>

        {/* Submit Button */}
        <button type="submit" className="w-full py-2 px-4 bg-blue-600 text-white hover:bg-blue-700">
          Submit
        </button>
      </form>
    </div>
  );
}
