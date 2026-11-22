import { defineConfig, devices } from "@playwright/test";
import { fileURLToPath } from "node:url";

const fakeAudio = fileURLToPath(new URL("./e2e/fixtures/hello.wav", import.meta.url));
const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:8090";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  timeout: 90_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL,
    permissions: ["microphone"],
    trace: "retain-on-failure",
    video: "off",
    launchOptions: {
      args: [
        "--use-fake-ui-for-media-stream",
        "--use-fake-device-for-media-stream",
        `--use-file-for-fake-audio-capture=${fakeAudio}`,
      ],
    },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
