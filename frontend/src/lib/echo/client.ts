import type {
    EchoSignal,
    ProfileOverview,
    TemporalDrift,
    TopicExposurePoint,
  } from "./types";
  
  import {
    mockEchoSignals,
    mockOverview,
    mockTemporalDrift,
    mockTopicTimeseries,
  } from "./mock";
  
  const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "");
  const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA === "true";
  
  async function fetchJson<T>(path: string): Promise<T> {
    if (USE_MOCK_DATA) {
      throw new Error("Mock mode is enabled.");
    }
  
    if (!BASE) {
      throw new Error(
        "VITE_API_BASE_URL is missing. Set VITE_API_BASE_URL=http://localhost:8080 in frontend/.env"
      );
    }
  
    const url = `${BASE}${path}`;
  
    const response = await fetch(url, {
      headers: {
        Accept: "application/json",
      },
    });
  
    if (!response.ok) {
      const body = await response.text().catch(() => "");
      throw new Error(
        `API request failed: ${response.status} ${response.statusText} for ${url}. ${body}`
      );
    }
  
    return response.json() as Promise<T>;
  }
  
  function useMockOrThrow<T>(mockFn: () => T, error: unknown): T {
    if (USE_MOCK_DATA) {
      return mockFn();
    }
  
    console.error("[EchoShield API error]", error);
    throw error;
  }
  
  export async function getProfileOverview(profileId: string): Promise<ProfileOverview> {
    try {
      return await fetchJson<ProfileOverview>(`/api/profiles/${profileId}/overview`);
    } catch (error) {
      return useMockOrThrow(() => mockOverview(profileId), error);
    }
  }
  
  export async function getEchoSignals(profileId: string): Promise<EchoSignal[]> {
    try {
      return await fetchJson<EchoSignal[]>(
        `/api/profiles/${profileId}/echo-signals?limit=10`
      );
    } catch (error) {
      return useMockOrThrow(mockEchoSignals, error);
    }
  }
  
  export async function getTemporalDrift(profileId: string): Promise<TemporalDrift[]> {
    try {
      return await fetchJson<TemporalDrift[]>(
        `/api/profiles/${profileId}/temporal-drift?granularity=weekly&limit=12`
      );
    } catch (error) {
      return useMockOrThrow(mockTemporalDrift, error);
    }
  }
  
  export async function getTopicTimeseries(profileId: string): Promise<TopicExposurePoint[]> {
    try {
      return await fetchJson<TopicExposurePoint[]>(
        `/api/profiles/${profileId}/topic-timeseries?granularity=weekly`
      );
    } catch (error) {
      return useMockOrThrow(mockTopicTimeseries, error);
    }
  }

  export type ImportJobResponse = {
    importJobId: string;
    profileId: string;
    status: string;
  };
  
  export type ImportJobStatus = {
    importJobId: string;
    profileId: string;
    source: string;
    status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
    originalFilename: string | null;
    totalEvents: number;
    insertedEvents: number;
    errorMessage: string | null;
    createdAt: string;
    startedAt: string | null;
    completedAt: string | null;
  };
  
  export async function uploadWatchHistory(
    file: File,
    displayName?: string
  ): Promise<ImportJobResponse> {
    const formData = new FormData();
    formData.append("file", file);
  
    if (displayName) {
      formData.append("displayName", displayName);
    }
  
    const response = await fetch(`${BASE}/api/imports/youtube-watch-history`, {
      method: "POST",
      body: formData,
    });
  
    if (!response.ok) {
      const message = await response.text();
      throw new Error(`Upload failed: ${response.status} ${message}`);
    }
  
    return response.json();
  }
  
  export async function getImportJobStatus(
    importJobId: string
  ): Promise<ImportJobStatus> {
    const response = await fetch(`${BASE}/api/imports/${importJobId}`);
  
    if (!response.ok) {
      const message = await response.text();
      throw new Error(`Import status failed: ${response.status} ${message}`);
    }
  
    return response.json();
  }
  
  export const USING_MOCK_DATA = USE_MOCK_DATA;