import { useMemo, useState } from "react";
import {
  describeActivity,
  formatClock,
  groupByDate,
  matchesChip,
  type ActivityChip,
  type ActivityItem,
} from "../../activityLog";
import type { NeuroShiftEngine } from "../../useNeuroShift";
import { ActivityRow } from "../RdIcons";

interface ActivityViewProps {
  engine: NeuroShiftEngine;
  personName: string;
  initialChip?: ActivityChip;
}

const CHIPS: { id: ActivityChip; label: string }[] = [
  { id: "all", label: "All" },
  { id: "actions", label: "Toggles" },
  { id: "review", label: "Unsure" },
  { id: "device", label: "Device" },
];

function clusterLooks(items: ActivityItem[]): ActivityItem[] {
  const out: ActivityItem[] = [];
  for (const item of items) {
    const prev = out[out.length - 1];
    if (prev && item.kind === "look" && prev.kind === "look" && prev.title === item.title) {
      const count = (prev.subtitle.match(/^(\d+) times/)?.[1] ? Number(prev.subtitle.match(/^(\d+) times/)?.[1]) : 1) + 1;
      const older = formatClock(item.timestamp);
      const newer = formatClock(prev.timestamp);
      prev.subtitle = `${count} times between ${older}–${newer}`;
      continue;
    }
    out.push({ ...item });
  }
  return out;
}

export function ActivityView({ engine, personName, initialChip = "all" }: ActivityViewProps) {
  const [chip, setChip] = useState<ActivityChip>(initialChip);
  const groups = useMemo(() => {
    const items = engine.activity
      .map((entry) => describeActivity(entry, personName))
      .filter((item) => matchesChip(item, chip));
    return groupByDate(items).map((group) => ({ ...group, items: clusterLooks(group.items) }));
  }, [chip, engine.activity, personName]);

  return (
    <div className="rd-screen">
      <div className="topbar">
        <h1 className="title">Activity</h1>
      </div>
      <div className="chiprow">
        {CHIPS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={chip === item.id ? "chip active" : "chip"}
            onClick={() => setChip(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {groups.length === 0 ? (
        <div className="empty-card activity-empty">
          <strong>No activity yet</strong>
          <span>Look at the lamp for two seconds. Toggles and unsure looks will show up here.</span>
        </div>
      ) : (
        groups.map((group) => (
          <div key={group.label}>
            <p className="daylabel">{group.label}</p>
            <div className="list">
              {group.items.map((item) => (
                <ActivityRow key={item.id} item={item} time={formatClock(item.timestamp)} bleed />
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
