// CrowdPulse in iMessage: the console's alerts and Gemini's plans go to the staff on duty as texts, and
// staff answer in plain words ("status", "ack", "on my way", "plan"). Built on Spectrum (Photon).
//
// It is a separate program next to the CrowdPulse server. It listens to the console's WebSocket the way
// a script does and never touches the measurement: if it or the network fails, the console carries on.
import { Spectrum } from "spectrum-ts";
import { imessage } from "@spectrum-ts/imessage";

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
const CONSOLE_WS = process.env.CROWDPULSE_WS || "ws://127.0.0.1:8000/ws";
const ALERTING = ["caution", "danger", "critical"];

// ---- what the console is saying --------------------------------------------------------------------
type Zone = { id: string; name: string };
type ZoneState = { id: string; count: number; density: number; level: string; eta_s: number | null; eta_level: string | null; above_safe_s: number };
type Alert = { id: string; zone_name: string; kind: string; level: string; message: string; status?: string };
type Plan = { zone_name: string; level: string; headline: string; actions: { role: string; instruction: string }[]; pa_announcement: string; origin: string };

let zones: Zone[] = [];
let camera = "";
let drill = false;
let sessionKey = "";
let latest: ZoneState[] = [];
const alerts = new Map<string, Alert>();
let plan: Plan | null = null;
let socket: WebSocket | null = null;

// ---- who is on duty ----------------------------------------------------------------------------------
// A staff member goes on duty by texting the line once; from then on alerts are sent to that chat.
type Chat = { send: (text: string) => Promise<unknown> };
const onDuty = new Map<string, Chat>();

async function tell(chat: Chat, text: string) {
  try {
    await chat.send(text);
  } catch (error) {
    console.error("Could not send a message:", error instanceof Error ? error.message : error);
  }
}

function broadcast(text: string) {
  for (const chat of onDuty.values()) void tell(chat, text);
}

// ---- wording -----------------------------------------------------------------------------------------
const label = (level: string) => level.toUpperCase();

function statusText(): string {
  if (!latest.length) return "CrowdPulse: no camera is streaming right now.";
  const lines = latest.map((z) => {
    const name = zones.find((zone) => zone.id === z.id)?.name ?? z.id;
    const outlook = z.eta_s !== null && z.eta_level ? `, ${z.eta_level} in ~${Math.max(10, Math.round(z.eta_s / 10) * 10)} s` : "";
    return `${name}: ${z.density.toFixed(1)}/m² ${label(z.level)}, ${z.count} people${outlook}`;
  });
  const head = `${drill ? "DRILL (simulated readings) · " : ""}${camera}`;
  return [head, ...lines, "Action level is 4/m²."].join("\n");
}

function planText(p: Plan): string {
  const steps = p.actions.map((a, i) => `${i + 1}. ${a.role}: ${a.instruction}`);
  const written = p.origin === "gemini" ? "Written by Gemini" : "Stored plan (Gemini unreachable)";
  return [`PLAN · ${p.zone_name} · ${label(p.level)}`, p.headline, ...steps, `PA: ${p.pa_announcement}`, `${written}. Reply "ack" or "on my way".`].join("\n");
}

const HELP = 'You are on duty for CrowdPulse. I will text you when a zone reaches the action level.\nReply: "status", "plan", "ack", "on my way", or "off duty".';

function newestAlert(needs: (alert: Alert) => boolean): Alert | undefined {
  return [...alerts.values()].reverse().find((a) => a.kind !== "cleared" && needs(a));
}

function command(type: string, extra: Record<string, unknown> = {}): boolean {
  if (socket?.readyState !== WebSocket.OPEN) return false;
  socket.send(JSON.stringify({ type, ...extra }));
  return true;
}

function answer(text: string): string {
  const said = text.trim().toLowerCase();
  if (/^(status|how is it|what'?s happening)/.test(said)) return statusText();
  if (/^plan/.test(said)) {
    if (plan) return planText(plan);
    const worst = [...latest].sort((a, b) => b.density - a.density)[0];
    return worst && command("request_plan", { zone_id: worst.id }) ? "No plan yet. I have asked for one; it will follow in a few seconds." : "No plan yet, and the console is not reachable.";
  }
  if (/^(ack|acknowledge|got it|seen)/.test(said)) {
    const alert = newestAlert((a) => !a.status);
    if (!alert) return "Nothing is waiting to be acknowledged.";
    return command("ack_alert", { alert_id: alert.id, status: "acknowledged" }) ? `Acknowledged: ${alert.message}` : "The console is not reachable; tell the control room by radio.";
  }
  if (/^(on my way|omw|dispatch|going|en route)/.test(said)) {
    const alert = newestAlert((a) => a.status !== "dispatched");
    if (!alert) return "Nothing is waiting for a dispatch.";
    return command("ack_alert", { alert_id: alert.id, status: "dispatched" }) ? `Logged as dispatched: ${alert.message}` : "The console is not reachable; tell the control room by radio.";
  }
  return HELP;
}

// ---- the console's WebSocket ----------------------------------------------------------------------------
function listen() {
  const ws = new WebSocket(CONSOLE_WS);
  socket = ws;
  ws.binaryType = "arraybuffer";
  ws.onopen = () => console.log("Connected to the CrowdPulse console at", CONSOLE_WS);
  ws.onclose = () => {
    socket = null;
    setTimeout(listen, 2000);
  };
  ws.onerror = () => ws.close();
  ws.onmessage = (event) => {
    if (typeof event.data !== "string") return; // a video frame
    const msg = JSON.parse(event.data);
    if (msg.type === "config") {
      const key = `${msg.active_source}:${msg.run}`;
      if (key !== sessionKey) {
        sessionKey = key;
        alerts.clear();
        plan = null;
        latest = [];
      }
      zones = msg.zones;
      drill = Boolean(msg.drill);
      camera = msg.sources.find((s: { id: string; label: string }) => s.id === msg.active_source)?.label ?? msg.active_source;
    } else if (msg.type === "state") {
      latest = msg.zones;
    } else if (msg.type === "alert") {
      const known = alerts.has(msg.id);
      alerts.set(msg.id, msg);
      // Staff are texted from the action level up, and when a forecast says it is coming. Not for "busy".
      const matters = ALERTING.includes(msg.level) && ["level_change", "prediction", "exposure"].includes(msg.kind);
      if (!known && (matters || msg.kind === "cleared")) broadcast(`${msg.kind === "cleared" ? "CLEARED" : label(msg.level)} · ${msg.message}`);
    } else if (msg.type === "alert_update") {
      const alert = alerts.get(msg.id);
      if (alert) alert.status = msg.status;
    } else if (msg.type === "plan" && msg.status === "ready") {
      plan = msg;
      if (ALERTING.includes(msg.level)) broadcast(planText(msg));
    }
  };
}
listen();

// ---- iMessage --------------------------------------------------------------------------------------------
const app = await Spectrum({
  projectId,
  projectSecret,
  providers: [imessage.config()],
});
console.log("CrowdPulse agent is in iMessage. Text the line to go on duty.");

for await (const [space, message] of app.messages) {
  if (message.content.type !== "text") continue;
  const chat: Chat = { send: (text) => space.send(text) };
  const id = String((space as { id?: unknown }).id ?? "staff");
  const said = message.content.text.trim().toLowerCase();
  if (/^(off duty|stop|unsubscribe)/.test(said)) {
    onDuty.delete(id);
    await tell(chat, "You are off duty. Text anything to go back on.");
    continue;
  }
  const firstTime = !onDuty.has(id);
  onDuty.set(id, chat);
  const reply = answer(message.content.text);
  await tell(chat, firstTime && reply !== HELP ? `${HELP}\n\n${reply}` : reply);
}
