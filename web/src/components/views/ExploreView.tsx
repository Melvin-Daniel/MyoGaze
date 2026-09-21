import type { NeuroShiftEngine } from "../../useNeuroShift";
import type { NestedId } from "../../App";
import { ActivityIcon, CameraIcon, InsightsIcon, MonitorIcon } from "../../icons";
import { isNativeApp, isPhoneClient } from "../../serverConfig";

interface ExploreViewProps {
  engine: NeuroShiftEngine;
  onOpen: (id: NestedId) => void;
}

export function ExploreView({ engine, onOpen }: ExploreViewProps) {
  return (
    <div className="stack">
      <div className="list-card">
        <button type="button" className="list-row" onClick={() => onOpen("live")}>
          <span className="list-row__icon" aria-hidden="true">
            <MonitorIcon size={18} />
          </span>
          <span className="list-row__main">
            <span className="list-row__title">Live session</span>
            <span className="list-row__sub">Look. Lock. Confirm.</span>
          </span>
          <span className="list-row__chev" aria-hidden="true">›</span>
        </button>
        <button type="button" className="list-row" onClick={() => onOpen("history")}>
          <span className="list-row__icon" aria-hidden="true">
            <ActivityIcon size={18} />
          </span>
          <span className="list-row__main">
            <span className="list-row__title">History</span>
            <span className="list-row__sub">What happened, and why.</span>
          </span>
          <span className="list-row__chev" aria-hidden="true">›</span>
        </button>
        <button type="button" className="list-row" onClick={() => onOpen("insights")}>
          <span className="list-row__icon" aria-hidden="true">
            <InsightsIcon size={18} />
          </span>
          <span className="list-row__main">
            <span className="list-row__title">Insights</span>
            <span className="list-row__sub">Session accuracy and exports.</span>
          </span>
          <span className="list-row__chev" aria-hidden="true">›</span>
        </button>
      </div>

      {!isNativeApp() && !isPhoneClient() && (
        <div className="list-card">
          <a className="list-row" href={engine.iphoneSetupLan || engine.iphoneSetup}>
            <span className="list-row__icon" aria-hidden="true">
              <CameraIcon size={18} />
            </span>
            <span className="list-row__main">
              <span className="list-row__title">iPhone setup</span>
              <span className="list-row__sub">Install the profile, then open HTTPS.</span>
            </span>
            <span className="list-row__chev" aria-hidden="true">›</span>
          </a>
          {engine.androidApkUrl ? (
            <a className="list-row" href={engine.androidApkUrl}>
              <span className="list-row__icon" aria-hidden="true">
                <CameraIcon size={18} />
              </span>
              <span className="list-row__main">
                <span className="list-row__title">Android app</span>
                <span className="list-row__sub">Download the APK, then pair this laptop.</span>
              </span>
              <span className="list-row__chev" aria-hidden="true">›</span>
            </a>
          ) : (
            <div className="list-row">
              <span className="list-row__main">
                <span className="list-row__title">Android app</span>
                <span className="list-row__sub">APK is not built yet.</span>
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
