export function freshserviceOrigin(env = process.env) {
  if (!env.FRESHWORKS_BASE_URL) {
    throw new Error("Set FRESHWORKS_BASE_URL to your synthetic Freshservice tenant's HTTPS origin");
  }
  const url = new URL(env.FRESHWORKS_BASE_URL);
  if (url.protocol !== "https:" || url.username || url.password ||
      url.pathname !== "/" || url.search || url.hash || url.port) {
    throw new Error("FRESHWORKS_BASE_URL must be an HTTPS origin without credentials, path, query, or custom port");
  }
  return url.origin;
}

export function ticketUrl(ticketId, env = process.env) {
  if (!/^[1-9][0-9]*$/.test(String(ticketId))) {
    throw new Error("Ticket ID must be a positive integer");
  }
  return `${freshserviceOrigin(env)}/a/tickets/${ticketId}`;
}

export function isTicketUrl(value, ticketId, env = process.env) {
  const expected = new URL(ticketUrl(ticketId, env));
  try {
    const actual = new URL(value);
    return actual.origin === expected.origin && actual.pathname === expected.pathname &&
      !actual.username && !actual.password;
  } catch {
    return false;
  }
}
