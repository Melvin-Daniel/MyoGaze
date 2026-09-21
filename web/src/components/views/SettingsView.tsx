import { useState } from "react";
import type { AccountUser } from "../../auth";
import { cameraState, lampState, laptopState } from "../../settings/tracking";
import type { NeuroShiftEngine } from "../../useNeuroShift";
import {
  AboutPanel,
  AccessibilityPanel,
  AppearancePanel,
  CalibrationPanel,
  ContactPanel,
  DevicePanel,
  DiagnosticsPanel,
  ExportPanel,
  GettingStartedPanel,
  HelpPanel,
  LookHoldPanel,
  NotificationsPanel,
  OwnerPanel,
  PermissionsPanel,
  PrivacyPanel,
  RecordsPanel,
  ReportPanel,
  TermsPanel,
  TrackingPanel,
  TroubleshootPanel,
  WellnessPanel,
} from "../settings/panels";
import { ProfileCard, SettingsHeader, SettingsRow, SettingsSection, SoonRow } from "../settings/ui";

interface SettingsViewProps {
  engine: NeuroShiftEngine;
  account: AccountUser;
  onSignOut: () => void;
  onOpenLive: () => void;
}

export type SettingsPanel =
  | null
  | "device"
  | "calibration"
  | "tracking"
  | "lookhold"
  | "wellness"
  | "owner"
  | "notifications"
  | "accessibility"
  | "appearance"
  | "records"
  | "permissions"
  | "export"
  | "privacy"
  | "help"
  | "started"
  | "troubleshoot"
  | "contact"
  | "report"
  | "diagnostics"
  | "about"
  | "terms";

const TITLES: Record<Exclude<SettingsPanel, null>, string> = {
  device: "Laptop & camera",
  calibration: "Calibration",
  tracking: "Eye tracking",
  lookhold: "Look & hold",
  wellness: "Break reminders",
  owner: "Account",
  notifications: "Notifications",
  accessibility: "Accessibility",
  appearance: "Appearance",
  records: "What MyoGaze records",
  permissions: "Data permissions",
  export: "Export or delete data",
  privacy: "Privacy",
  help: "Help center",
  started: "Getting started",
  troubleshoot: "Device troubleshooting",
  contact: "Contact support",
  report: "Report a problem",
  diagnostics: "Device diagnostics",
  about: "About MyoGaze",
  terms: "Terms",
};

export function SettingsView({ engine, account, onSignOut, onOpenLive }: SettingsViewProps) {
  const [panel, setPanel] = useState<SettingsPanel>(null);
  const laptop = laptopState(engine);
  const camera = cameraState(engine);
  const lamp = lampState(engine);

  return (
    <div className={panel ? "rd-screen rd-settings-wrap has-panel" : "rd-screen rd-settings-wrap"}>
      <div className="settings-hub">
        <div className="topbar">
          <h1 className="title">Settings</h1>
        </div>
        <ProfileCard
          name={account.name}
          identifier={account.identifier}
          laptop={laptop === "connected" ? "Laptop online" : laptop === "reconnecting" ? "Laptop reconnecting" : "Laptop offline"}
          camera={camera === "on" ? "Camera on" : camera === "idle" ? "Camera idle" : "Camera offline"}
          lamp={lamp === "on" ? "Lamp on" : lamp === "off" ? "Lamp off" : "Lamp offline"}
        />

        <SettingsSection label="Device & eye tracking">
          <SettingsRow
            label="Laptop & camera"
            hint={laptop === "connected" ? "Online" : "Offline"}
            onClick={() => setPanel("device")}
          />
          <SettingsRow label="Calibration" onClick={() => setPanel("calibration")} />
          <SettingsRow label="Eye tracking" onClick={() => setPanel("tracking")} />
          <SettingsRow label="Look & hold" hint={`${engine.settings.dwell_seconds.toFixed(1)}s`} onClick={() => setPanel("lookhold")} />
          <SoonRow label="Blink detection" hint="No blink detector in Phase 1." />
        </SettingsSection>

        <SettingsSection label="Eye wellness">
          <SettingsRow label="Break reminders" onClick={() => setPanel("wellness")} />
          <SoonRow label="Eye fatigue monitoring" hint="Not measured by the camera yet." />
        </SettingsSection>

        <SettingsSection label="Account">
          <SettingsRow label={`${account.name} · Owner`} onClick={() => setPanel("owner")} />
          <SoonRow label="Invite family" />
          <SoonRow label="Caregiver access" />
        </SettingsSection>

        <SettingsSection label="Preferences">
          <SettingsRow label="Notifications" onClick={() => setPanel("notifications")} />
          <SettingsRow label="Accessibility" onClick={() => setPanel("accessibility")} />
          <SettingsRow label="Appearance" onClick={() => setPanel("appearance")} />
        </SettingsSection>

        <SettingsSection label="Data & privacy">
          <SettingsRow label="What MyoGaze records" onClick={() => setPanel("records")} />
          <SettingsRow label="Data permissions" onClick={() => setPanel("permissions")} />
          <SettingsRow label="Export or delete data" onClick={() => setPanel("export")} />
          <SettingsRow label="Privacy policy" onClick={() => setPanel("privacy")} />
        </SettingsSection>

        <SettingsSection label="Support">
          <SettingsRow label="Help center" onClick={() => setPanel("help")} />
          <SettingsRow label="Getting started" onClick={() => setPanel("started")} />
          <SettingsRow label="Device troubleshooting" onClick={() => setPanel("troubleshoot")} />
          <SettingsRow label="Contact support" onClick={() => setPanel("contact")} />
          <SettingsRow label="Report a problem" onClick={() => setPanel("report")} />
          <SettingsRow label="Device diagnostics" onClick={() => setPanel("diagnostics")} />
        </SettingsSection>

        <SettingsSection label="About">
          <SettingsRow label="About MyoGaze" onClick={() => setPanel("about")} />
          <SettingsRow label="Terms" onClick={() => setPanel("terms")} />
          <SettingsRow label="Privacy policy" onClick={() => setPanel("privacy")} />
        </SettingsSection>

        <button type="button" className="logout" onClick={onSignOut}>
          Log out
        </button>
      </div>

      {panel ? (
        <div className="settings-pane">
          <SettingsHeader title={TITLES[panel]} onBack={() => setPanel(null)} />
          <PanelBody panel={panel} engine={engine} account={account} onOpenLive={onOpenLive} />
        </div>
      ) : null}
    </div>
  );
}

function PanelBody({
  panel,
  engine,
  account,
  onOpenLive,
}: {
  panel: Exclude<SettingsPanel, null>;
  engine: NeuroShiftEngine;
  account: AccountUser;
  onOpenLive: () => void;
}) {
  switch (panel) {
    case "device":
      return <DevicePanel engine={engine} onOpenLive={onOpenLive} />;
    case "calibration":
      return <CalibrationPanel engine={engine} />;
    case "tracking":
      return <TrackingPanel engine={engine} onOpenLive={onOpenLive} />;
    case "lookhold":
      return <LookHoldPanel engine={engine} />;
    case "wellness":
      return <WellnessPanel />;
    case "owner":
      return <OwnerPanel account={account} />;
    case "notifications":
      return <NotificationsPanel />;
    case "accessibility":
      return <AccessibilityPanel engine={engine} />;
    case "appearance":
      return <AppearancePanel />;
    case "records":
      return <RecordsPanel />;
    case "permissions":
      return <PermissionsPanel />;
    case "export":
      return <ExportPanel engine={engine} />;
    case "privacy":
      return <PrivacyPanel />;
    case "help":
      return <HelpPanel />;
    case "started":
      return <GettingStartedPanel />;
    case "troubleshoot":
      return <TroubleshootPanel />;
    case "contact":
      return <ContactPanel />;
    case "report":
      return <ReportPanel engine={engine} />;
    case "diagnostics":
      return <DiagnosticsPanel engine={engine} />;
    case "about":
      return <AboutPanel />;
    case "terms":
      return <TermsPanel />;
  }
}
