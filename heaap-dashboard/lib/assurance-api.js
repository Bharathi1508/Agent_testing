const API_URL =
  process.env.HEAAP_API_URL || "http://127.0.0.1:8000";

export async function getAssuranceSummary() {
  const response = await fetch(
    `${API_URL}/api/assurance/summary`,
    { cache: "no-store" }
  );

  if (!response.ok) {
    throw new Error("Unable to retrieve assurance summary");
  }

  return response.json();
}

export async function getAssuranceReports() {
  const response = await fetch(
    `${API_URL}/api/assurance/reports`,
    { cache: "no-store" }
  );

  if (!response.ok) {
    throw new Error("Unable to retrieve assurance reports");
  }

  const data = await response.json();

  return data.reports || [];
}
