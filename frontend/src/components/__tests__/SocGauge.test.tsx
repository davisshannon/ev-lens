import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SocGauge } from "../SocGauge";

describe("SocGauge", () => {
  it("renders the SoC percentage", () => {
    render(<SocGauge soc={72} />);
    expect(screen.getByText("72%")).toBeDefined();
  });

  it("rounds fractional SoC", () => {
    render(<SocGauge soc={71.8} />);
    expect(screen.getByText("72%")).toBeDefined();
  });
});
