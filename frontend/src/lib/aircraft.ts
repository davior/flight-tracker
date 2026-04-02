type AircraftSummary = {
  display_type?: string | null;
  category: string | null;
  category_label: string | null;
  category_description: string | null;
};

export function formatAircraftCategory(summary: AircraftSummary): string | null {
  if (summary.category_label) {
    return summary.category ? `${summary.category_label} (${summary.category})` : summary.category_label;
  }
  return summary.category;
}

export function getAircraftCategoryDescription(summary: AircraftSummary): string | null {
  return summary.category_description;
}

export function getAircraftDisplayLabel(summary: AircraftSummary): string | null {
  if (summary.display_type) {
    return summary.display_type;
  }
  return formatAircraftCategory(summary);
}
