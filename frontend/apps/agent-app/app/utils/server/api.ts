import { auth } from "@clerk/nextjs/server";

interface FetchOptions {
  url: string;
  headers?: Record<string, string>;
}

export const fetchData = async <T = any>({ url, headers = {} }: FetchOptions): Promise<T> => {
  const { getToken } = await auth();
  const token = await getToken();

  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      ...headers,
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP Error: ${response.status}`);
  }

  const json = await response.json();

  return json.data as T;
};
