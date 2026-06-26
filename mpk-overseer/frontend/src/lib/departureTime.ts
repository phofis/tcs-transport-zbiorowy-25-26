import { format } from "date-fns";
import { fromZonedTime } from "date-fns-tz";

const WARSAW_TZ = "Europe/Warsaw";

export function warsawDateTimeToEpoch(date: Date, time: string): number {
  const datePart = format(date, "yyyy-MM-dd");
  const normalizedTime = time.length === 5 ? `${time}:00` : time;
  return Math.floor(
    fromZonedTime(`${datePart}T${normalizedTime}`, WARSAW_TZ).getTime() / 1000,
  );
}

export function formatEpochWarsaw(epoch: number, withDate = false): string {
  const formatter = new Intl.DateTimeFormat("pl-PL", {
    timeZone: WARSAW_TZ,
    hour: "2-digit",
    minute: "2-digit",
    ...(withDate ? { day: "2-digit", month: "2-digit" } : {}),
  });
  return formatter.format(new Date(epoch * 1000));
}

export function defaultDepartureTime(): string {
  const formatter = new Intl.DateTimeFormat("en-GB", {
    timeZone: WARSAW_TZ,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return formatter.format(new Date());
}
