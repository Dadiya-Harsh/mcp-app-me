import { Card } from "./Card";

function Block({ w, h, round }: { w: string; h: number; round?: boolean }) {
  return <div className="skeleton" style={{ width: w, height: h, borderRadius: round ? 999 : undefined }} />;
}

/** Shown while the tool is still running. Same shape as the profile card. */
export function ProfileSkeleton() {
  return (
    <Card>
      <div aria-busy="true" aria-label="Loading profile" style={{ padding: 28, display: "grid", gap: 18 }}>
        <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
          <Block w="76px" h={76} round />
          <div style={{ display: "grid", gap: 10, flex: 1 }}>
            <Block w="55%" h={24} />
            <Block w="40%" h={16} />
          </div>
        </div>
        <Block w="100%" h={16} />
        <Block w="80%" h={16} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
          <Block w="100%" h={78} />
          <Block w="100%" h={78} />
          <Block w="100%" h={78} />
        </div>
      </div>
    </Card>
  );
}
