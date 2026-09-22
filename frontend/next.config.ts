import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next 16 writes editor-tooling instruction files into the project root on
  // every `next dev` and re-creates them if deleted. This project keeps all of
  // its documentation in README.md and docs/ at the repository root, so the
  // generation is turned off at the source rather than ignored after the fact.
  agentRules: false,
};

export default nextConfig;
