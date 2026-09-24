import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";

export default defineConfig([
  ...nextVitals,

  {
    rules: {
      // The React Compiler rules find 11 real problems across nine files.
      // Tracked in #411; warnings until that list is empty, then back to error.
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/purity": "warn",
    },
  },

  globalIgnores([
    ".next/**",
    "out/**",
    "node_modules/**",
    "next-env.d.ts",
  ]),
]);
