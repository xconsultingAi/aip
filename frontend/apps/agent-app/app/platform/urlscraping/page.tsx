'use client';
import { useState } from 'react';

export default function UrlScraper() {
  const [url, setUrl] = useState('');
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    setError('');
    try {
      const res = await fetch('/api/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Scraping failed');
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
   <div className="flex justify-center items-center h-screen">
      <div className="p-6 border rounded-lg shadow-md bg-white max-w-sm w-full text-center dark:bg-gray-900 shadow-2xl">
      <h2 className="text-xl font-semibold mb-2">Scrape Content from URL</h2>
      <input
        type="text"
        placeholder="Enter URL"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        className="w-full p-2 border rounded mb-2"
      />
      <button onClick={handleSubmit} className="bg-green-600 text-white px-4 py-2 rounded">
        Scrape
      </button>

      {error && <p className="text-red-600 mt-2">{error}</p>}

      {result && (
        <div className="mt-4">
          <h3 className="font-bold">{result.title}</h3>
          <p className="whitespace-pre-line">{result.content}</p>
        </div>
      )}
    </div>
    </div>
  );
}
