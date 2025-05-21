'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser, useAuth } from "@clerk/nextjs";

const KnowledgeBasePage = () => {
  const [knowledgeBases, setKnowledgeBases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
    const { getToken } = useAuth();

  const stats = {
    pdf: 12,
    text: 8,
    website: 5,
    youtube: 3,
    word: 7,
  };

  useEffect(() => {
    const fetchKnowledgeBases = async () => {
      try {
        const token = await getToken();
        const res = await fetch('http://127.0.0.1:8000/api/org_knowledge_base',
           {
    headers: {
      Authorization: `Bearer ${token}`,
    },}
        );
        const response = await res.json();
        console.log('API response:', response.data);

        if (Array.isArray(response.data)) {
          setKnowledgeBases(response.data);
        } else if (Array.isArray(response.data.knowledge_bases)) {
          setKnowledgeBases(response.data.knowledge_bases);
        } else {
          console.error('Unexpected API response format:', response);
          setKnowledgeBases([]);
        }
      } catch (error) {
        console.error('Error fetching knowledge bases:', error);
        setKnowledgeBases([]);
      } finally {
        setLoading(false);
      }
    };

    fetchKnowledgeBases();
  }, []);

  const handleCreateClick = () => {
    router.push('/platform/knowledgebase/CreateKnowledgebase');
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
            <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
          </svg>
          Create New
        </button>
      </div>

      {/* Stats Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
        {Object.entries(stats).map(([label, count]) => (
          <div key={label} className="bg-white p-4 rounded-lg shadow-2xl">
            <h2 className="text-gray-500 text-sm">{label.toUpperCase()}</h2>
            <p className="text-2xl font-bold">{count}</p>
          </div>
        ))}
      </div>

      {/* Knowledge Bases Table */}
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
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
           <tbody className="bg-white divide-y divide-gray-200">
  {knowledgeBases.map((kb: any) => (
    <tr key={kb.id}>
      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
        {kb.filename}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        <span className={`px-2 py-1 rounded-full text-xs ${
          kb.content_type.includes('pdf') ? 'bg-red-100 text-red-800' :
          'bg-green-100 text-green-800'
        }`}>
          {kb.content_type}
        </span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {new Date(kb.uploaded_at).toLocaleDateString()}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        <button className="text-blue-600 hover:text-blue-800 mr-3">Edit</button>
        <button className="text-red-600 hover:text-red-800">Delete</button>
      </td>
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
