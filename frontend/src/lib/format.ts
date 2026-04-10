const timestampFormatter = new Intl.DateTimeFormat(undefined, {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
  timeZoneName: "short",
});

function cleanPart(value: string | undefined): string {
  return (value ?? "").replace(/\s+/g, " ").trim().replace(/[,\u200e\u200f]/g, "");
}

function parseTimestamp(value: string): Date {
  const normalized = /^[0-9]{4}-[0-9]{2}-[0-9]{2}T/.test(value) && !/[zZ]|[+\-][0-9]{2}:[0-9]{2}$/.test(value)
    ? `${value}Z`
    : value;
  return new Date(normalized);
}

function formatDate(date: Date): string {
  const parts = timestampFormatter.formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, cleanPart(part.value)]));

  const day = values.day;
  const month = values.month;
  const year = values.year;
  const hour = values.hour;
  const minute = values.minute;
  const dayPeriod = values.dayPeriod;
  const timeZoneName = values.timeZoneName;

  if (!day || !month || !year || !hour || !minute || !dayPeriod || !timeZoneName) {
    return timestampFormatter.format(date).replace(/\s+/g, " ").trim();
  }

  return `${day} ${month} ${year} ${hour}:${minute} ${dayPeriod} ${timeZoneName}`;
}

export function formatTimestamp(value: string): string {
  const date = parseTimestamp(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return formatDate(date);
}

export function formatUnixTimestamp(value: number): string {
  const date = new Date(value * 1000);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return formatDate(date);
}
