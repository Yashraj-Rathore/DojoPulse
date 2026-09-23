export async function workspaceRequest<T>(csrf: string, path: string, method = "GET", body?: object, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api/${path}`, { method, credentials: "same-origin", cache: "no-store", signal,
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf }, body: body ? JSON.stringify(body) : undefined });
  const result = await response.json();
  if (!response.ok) {
    const message = typeof result.error === "string" ? result.error : Object.values(result).flat().filter(item => typeof item === "string").join(" ");
    throw new Error(message || "Request could not be completed. Refresh and try again.");
  }
  return result;
}

export function displayTime(value: string, zone: string = "UTC") {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short", ...(zone === "UTC" ? { timeZone: "UTC" } : {}) }).format(new Date(value)) + (zone === "UTC" ? " UTC" : ` (${Intl.DateTimeFormat().resolvedOptions().timeZone})`);
}
