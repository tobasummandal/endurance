export const palette = {
  void:      "#0A0908",
  carbon:    "#15120E",
  walnut:    "#3A2A1A",
  bronze:    "#8B6F47",
  brass:     "#C9A66B",
  champagne: "#E8D5A8",
  bone:      "#F2EDE4",
  ash:       "#8A8276",
  ember:     "#A84D2E",
} as const;

export type StageState = "idle" | "active" | "pass" | "fail";

export const stateColor = (s: StageState) => {
  switch (s) {
    case "active": return palette.bronze;
    case "pass":   return palette.brass;
    case "fail":   return palette.ember;
    default:       return palette.walnut;
  }
};

export const stateGlow = (s: StageState) => {
  switch (s) {
    case "active": return "glow-bronze";
    case "pass":   return "glow-brass";
    case "fail":   return "glow-ember";
    default:       return "";
  }
};
