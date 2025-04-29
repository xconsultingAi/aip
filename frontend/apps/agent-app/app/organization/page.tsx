'use client';

import { useUser, useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function OrganizationPage() {
  const { user } = useUser(); // HZ: Get the currently authenticated user
  const { getToken } = useAuth(); // HZ: Function to retrieve the Clerk auth token
  const router = useRouter(); // HZ: Router for navigation

  // HZ: Define state variables
  const [organization, setOrganization] = useState<string | null>(null); // HZ: Current organization name
  const [organizationInput, setOrganizationInput] = useState(''); // HZ: Input field for org name (edit/create)
  const [isEditing, setIsEditing] = useState(false); // HZ: Toggle for edit mode
  const [loading, setLoading] = useState(true); // HZ: Show loading state
  const [error, setError] = useState<string | null>(null); // HZ: Store any API or logic errors

  // HZ: Fetch user's organization on page load
  useEffect(() => {
    const fetchOrganization = async () => {
      if (!user) return;

      try {
        const token = await getToken(); // HZ: Get secure auth token

        // HZ: First, get the user's data to find organization ID
        const users = await fetch(`http://127.0.0.1:8000/api/users/${user?.id}`, {
          method: "GET",
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        });

        const user_data = await users.json();
        const organization_id = user_data?.data.organization_id;

        // HZ: Now fetch the organization details using ID
        const res = await fetch(`http://127.0.0.1:8000/api/organizations/${organization_id}`, {
          method: "GET",
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        });

        if (!res.ok) throw new Error("Failed to fetch organization details.");

        const data = await res.json();

        if (data?.name) {
          setOrganization(data.name); // HZ: Set display and input state
          setOrganizationInput(data.name);
        }
      } catch (error) {
        console.error("Error fetching organization:", error);
        setError((error as Error).message); // HZ: Handle errors gracefully
      } finally {
        setLoading(false); // HZ: Stop loading once done
      }
    };

    fetchOrganization();
  }, [user, getToken]);

  // HZ: Handle organization creation
  const handleCreate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const formData = new FormData(e.currentTarget);
    const name = formData.get("organizationName") as string;
    const token = await getToken();

    try {
      const res = await fetch("http://127.0.0.1:8000/api/organizations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ name }),
      });

      const data = await res.json();

      // HZ: Update state on success
      setOrganization(data.name);
      setOrganizationInput(data.name);
    } catch (error) {
      setError((error as Error).message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  // HZ: Handle organization name update
  const handleUpdate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const token = await getToken();

      // HZ: Re-fetch user for org ID
      const users = await fetch(`http://127.0.0.1:8000/api/users/${user?.id}`, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`,
        },
      });

      const user_data = await users.json();
      const organization_id = user_data?.data.organization_id;

      // HZ: Send update request
      const res = await fetch(`http://127.0.0.1:8000/api/organizations/${organization_id}`, {
        method: "PUT", // HZ: Use PUT or PATCH based on backend
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ name: organizationInput }),
      });

      const data = await res.json();

      setOrganization(data.name); // HZ: Reflect changes in UI
      setIsEditing(false);
    } catch (error) {
      setError((error as Error).message || "Failed to update organization.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="bg-white p-6 rounded-lg shadow-lg w-full max-w-md dark:bg-gray-900">
        <h1 className="text-2xl font-bold text-center mb-4">Organization Details</h1>

        {loading ? (
          // HZ: Show loading message
          <p className="text-center">Loading...</p>
        ) : organization ? (
          isEditing ? (
            // HZ: Edit form UI
            <form onSubmit={handleUpdate} className="flex flex-col gap-4">
              <input
                type="text"
                value={organizationInput}
                onChange={(e) => setOrganizationInput(e.target.value)}
                className="p-2 border border-gray-300 rounded-md"
                required
              />
              {error && <p className="text-red-500">{error}</p>}
              <div className="flex justify-between">
                <button
                  type="submit"
                  className="bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600 disabled:opacity-50"
                  disabled={loading}
                >
                  {loading ? "Updating..." : "Save"}
                </button>
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  className="bg-gray-500 text-white py-2 px-4 rounded-md hover:bg-gray-600"
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            // HZ: Display organization info with actions
            <div className="text-center">
              <p className="text-lg">You belong to <strong>{organization}</strong></p>
              <button
                className="mt-4 mr-2 bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600"
                onClick={() => setIsEditing(true)}
              >
                Edit
              </button>
              <button
                className="mt-4 bg-green-500 text-white py-2 px-4 rounded-md hover:bg-green-600"
                onClick={() => router.push('/')}
              >
                Go to Dashboard
              </button>
            </div>
          )
        ) : (
          // HZ: Show form if no organization exists
          <form onSubmit={handleCreate} className="flex flex-col gap-4">
            <input
              type="text"
              name="organizationName"
              placeholder="Enter your organization name"
              required
              className="p-2 border border-gray-300 rounded-md"
            />
            {error && <p className="text-red-500">{error}</p>}
            <button
              type="submit"
              className="bg-green-500 text-white py-2 px-4 rounded-md hover:bg-green-600 disabled:opacity-50"
              disabled={loading}
            >
              {loading ? "Submitting..." : "Submit"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
