import { Spectrum } from "spectrum-ts";
import { imessage } from "@spectrum-ts/imessage";
// Spectrum bridges a single agent loop to many messaging interfaces.
// Each provider in `providers` adds an interface (terminal TUI, iMessage, …).
// Docs: https://photon.codes/docs/spectrum-ts

// The starter does not load .env by itself, and the dashboard's manual setup names the two values
// SPECTRUM_PROJECT_ID / SPECTRUM_PROJECT_SECRET while the scaffold uses PROJECT_ID / PROJECT_SECRET.
try {
  process.loadEnvFile(new URL("../.env", import.meta.url));
} catch {
  // No .env file: the values must already be in the environment.
}
const projectId = process.env.PROJECT_ID || process.env.SPECTRUM_PROJECT_ID;
const projectSecret = process.env.PROJECT_SECRET || process.env.SPECTRUM_PROJECT_SECRET;
if (!projectId || !projectSecret) {
  console.error("Set PROJECT_ID and PROJECT_SECRET in hacklanta/.env (from the Photon dashboard).");
  process.exit(1);
}

const app = await Spectrum({
  projectId,
  projectSecret,
  providers: [
    // imessage
    imessage.config(),
  ],
});

// `app.messages` is an async iterable. Each tick yields a `space` (the
// conversation) and an inbound `message`. Reply by awaiting `space.send(...)`.
for await (const [space, message] of app.messages) {
  if (message.content.type === "text") {
    await space.send(`echo: ${message.content.text}`);
  }
}
