'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';

interface StatItem {
  format: string;
  count: number;
}

const KnowledgeBasePage = () => {
  const [knowledgeBases, setKnowledgeBases] = useState<any[]>([]);
  const [agentCounts, setAgentCounts] = useState<{ [key: string]: number }>({});
  const [stats, setStats] = useState<StatItem[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const { getToken } = useAuth();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const token = await getToken();

        // Fetch all data in parallel
        const [kbRes, statsRes] = await Promise.all([
          fetch('http://127.0.0.1:8000/api/org_knowledge_base', {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch('http://127.0.0.1:8000/api/format_count', {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);

        // Process knowledge bases
        const kbJson = await kbRes.json();
        const kbList = Array.isArray(kbJson.data)
          ? kbJson.data
          : kbJson.data?.knowledge_bases || [];
        setKnowledgeBases(kbList);

        // Process stats - assuming API returns array of { format, count }
        const statsJson = await statsRes.json();
        setStats(statsJson.data || []);

        // Fetch agent counts for each KB
        const countPromises = kbList.map(async (kb: any) => {
          try {
            const res = await fetch(
              `http://127.0.0.1:8000/api/agent_count?knowledge_id=${kb.id}`,
              { headers: { Authorization: `Bearer ${token}` } }
            );
            const data = await res.json();
            return { kbId: kb.id, count: data.data.agent_count ?? 0 };
          } catch (err) {
            console.error(`Error fetching count for KB ${kb.id}`, err);
            return { kbId: kb.id, count: 0 };
          }
        });

        const counts = await Promise.all(countPromises);
        const countMap: { [key: string]: number } = {};
        counts.forEach((item) => {
          countMap[item.kbId] = item.count;
        });
        setAgentCounts(countMap);

      } catch (error) {
        console.error('Error loading data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleCreateClick = () => {
    router.push('/platform/knowledgebase/CreateKnowledgebase');
  };

  // Transform stats array to the format needed for display
  const getDisplayStats = () => {
    const displayStats: { [key: string]: number } = {};
    stats.forEach((stat) => {
      displayStats[stat.format] = stat.count;
    });
    return displayStats;
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Knowledge Base</h1>
        <button
          onClick={handleCreateClick}
          className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
              clipRule="evenodd"
            />
          </svg>
          Create New
        </button>
      </div>

      {/* Stats Section */}
      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
          {stats.map((stat) => (
            <div key={stat.format} className="bg-white p-4 rounded-lg shadow-2xl">
              <h2 className="text-gray-500 text-sm">{stat.format.toUpperCase()}</h2>
              <p className="text-2xl font-bold">{stat.count}</p>
            </div>
          ))}
        </div>
      )}

      {/* Rest of your component remains the same */}
      <div className="bg-white rounded-lg shadow-2xl overflow-hidden">
        <div className="flex justify-between items-center p-4 border-b">
          <h2 className="text-lg font-semibold">Latest Knowledge Bases</h2>
          <div className="flex space-x-2">
            <button className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200">Filter</button>
            <button className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200">Sort</button>
          </div>
        </div>

        {loading ? (
          <div className="p-6 text-center text-gray-500">Loading...</div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Format</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Agents</th>
                {/* <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th> */}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {knowledgeBases.map((kb) => (
                <tr key={kb.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{kb.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <span
                      className={`px-2 py-1 rounded-full text-xs ${
                        kb.format.includes('pdf') ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                      }`}
                    >
                      {kb.format}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(kb.uploaded_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {agentCounts[kb.id] ?? 0}
                  </td>
                  {/* <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <button className="text-blue-600 hover:text-blue-800 mr-3">Edit</button>
                    <button className="text-red-600 hover:text-red-800">Delete</button>
                  </td> */}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default KnowledgeBasePage;