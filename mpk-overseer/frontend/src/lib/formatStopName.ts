export interface StopNameParts {
  name: string;
  platform?: string | null;
}

export function formatStopName(stop: StopNameParts): string {
  if (stop.platform) {
    return `${stop.name} ${stop.platform}`;
  }
  return stop.name;
}

export function stopMatchesQuery(stop: StopNameParts, query: string): boolean {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return true;
  }
  if (stop.name.toLowerCase().includes(normalized)) {
    return true;
  }
  if (stop.platform?.toLowerCase().includes(normalized)) {
    return true;
  }
  return formatStopName(stop).toLowerCase().includes(normalized);
}
