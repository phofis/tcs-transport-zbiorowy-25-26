const WARSAW_FORMATTER = new Intl.DateTimeFormat("pl-PL", {
  timeZone: "Europe/Warsaw",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

export function formatDepartureTime(departureTs: number, nowTs: number): string {
  const diffSeconds = departureTs - nowTs;
  const diffMinutes = Math.floor(diffSeconds / 60);

  if (diffMinutes >= 0 && diffMinutes < 60) {
    return `${diffMinutes}'`;
  }

  return WARSAW_FORMATTER.format(new Date(departureTs * 1000));
}
