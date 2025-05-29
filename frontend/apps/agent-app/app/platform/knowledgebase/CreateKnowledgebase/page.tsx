"use client";

import { useState } from "react";
import { useUser, useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

export default function FileUpload() {
  const { user } = useUser();
  const { getToken } = useAuth();

  // File upload states
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [kbFormat, setKbFormat] = useState("pdf");

  // Website scraping states
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [depth, setDepth] = useState(1);
  const [includeLinks, setIncludeLinks] = useState(false);

  // General UI states
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    setFile(e.target.files[0]);
  };

  // Upload file to backend
  const handleUpload = async () => {
    if (!file || !name.trim() || !kbFormat) {
      setMessage("Please fill all fields and select a file.");
      return;
    }

    setLoading(true);
    setMessage("");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("name", name.trim());
    formData.append("kb_format", kbFormat);

    try {
      const token = await getToken();
      const res = await fetch("http://127.0.0.1:8000/api/upload_knowledge_base", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await res.json();

      if (res.ok) {
        setMessage("✅ Upload successful!");
        router.push("/platform/knowledgebase/");
      } else {
        setMessage(`❌ Error: ${data.detail || "Upload failed"}`);
      }
    } catch {
      setMessage("❌ Upload failed. Server error.");
    } finally {
      setLoading(false);
    }
  };

  // Scrape website content
  const handleWebsiteScrape = async () => {
    if (!name.trim() || !websiteUrl.trim()) {
      setMessage("Please enter both a name and a website URL.");
      return;
    }

    // Basic URL validation
    try {
      new URL(websiteUrl);
    } catch {
      setMessage("Please enter a valid URL.");
      return;
    }

    if (depth < 1) {
      setMessage("Depth must be at least 1.");
      return;
    }

    setLoading(true);
    setMessage("");

    const payload = {
      name: name.trim(),
      url: websiteUrl.trim(),
      depth,
      include_links: includeLinks,
    };

    console.log("Sending payload:", payload);

    try {
      const token = await getToken();
      const res = await fetch("http://127.0.0.1:8000/api/add_url", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (res.ok) {
        setMessage("✅ Website content added successfully!");
        router.push("/platform/knowledgebase/");
      } else {
        setMessage(`❌ Error: ${data.detail || "Failed to add website content."}`);
      }
    } catch {
      setMessage("❌ Request failed. Server error.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10 p-6 border rounded-lg shadow-lg bg-white dark:bg-gray-900">
      <h2 className="text-lg font-semibold mb-4 text-center">Upload Knowledge Base</h2>

      {/* KB Name */}
      <div className="mb-4">
        <label className="block mb-1 text-sm font-medium">Knowledge Base Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full border p-2 rounded-md dark:bg-gray-800"
          placeholder="My KB File or Website Name"
        />
      </div>

      {/* KB Format Select */}
      <div className="mb-4">
        <label className="block mb-1 text-sm font-medium">Select Format</label>
        <select
          value={kbFormat}
          onChange={(e) => setKbFormat(e.target.value)}
          className="w-full border p-2 rounded-md dark:bg-gray-800"
        >
          <option value="pdf">PDF</option>
          <option value="docx">DOCX</option>
          <option value="html">HTML</option>
          <option value="csv">CSV</option>
          <option value="xls">XLS</option>
          <option value="xlsx">XLSX</option>
          <option value="txt">TXT</option>
          <option value="website">Website</option>
        </select>
      </div>

      {/* Conditionally show upload or website scrape */}
      {kbFormat !== "website" ? (
        <>
          <label className="block mt-4 mb-1 text-sm font-medium">Upload File</label>
          <input
            type="file"
            accept=".pdf,.docx,.html,.csv,.xls,.xlsx,.txt"
            onChange={handleFileChange}
            className="w-full"
          />
          <button
            onClick={handleUpload}
            disabled={loading}
            className={`w-full mt-4 p-2 text-white rounded-md ${
              loading ? "bg-gray-400 cursor-not-allowed" : "bg-green-600 hover:bg-green-700"
            }`}
          >
            {loading ? "Uploading..." : "Upload File"}
          </button>
        </>
      ) : (
        <>
          <label className="block mt-4 mb-1 text-sm font-medium">Website URL</label>
          <input
            type="url"
            value={websiteUrl}
            onChange={(e) => setWebsiteUrl(e.target.value)}
            className="w-full border p-2 rounded-md dark:bg-gray-800 mb-3"
            placeholder="https://example.com"
          />

          <label className="block text-sm font-medium mb-1">Depth</label>
          <input
            type="number"
            min={1}
            max={5}
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
            className="w-full border p-2 rounded-md dark:bg-gray-800 mb-3"
          />

          <div className="flex items-center mb-4">
            <input
              type="checkbox"
              checked={includeLinks}
              onChange={(e) => setIncludeLinks(e.target.checked)}
              className="mr-2"
              id="includeLinksCheckbox"
            />
            <label htmlFor="includeLinksCheckbox" className="text-sm">
              Include links
            </label>
          </div>

          <button
            onClick={handleWebsiteScrape}
            disabled={loading}
            className={`w-full p-2 text-white rounded-md ${
              loading ? "bg-gray-400 cursor-not-allowed" : "bg-green-600 hover:bg-green-700"
            }`}
          >
            {loading ? "Scraping..." : "Scrape Website"}
          </button>
        </>
      )}

      {/* Message */}
      {message && (
        <p className="mt-4 text-center text-sm text-red-600 dark:text-red-400 whitespace-pre-wrap">{message}</p>
      )}
    </div>
  );
}
