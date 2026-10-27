import cytoscape, { Core } from "cytoscape";
import { useEffect, useRef } from "react";
import { RISK } from "@/lib/risk";
import type { GraphData } from "@/services/api/copilot";

interface Props { data: GraphData; highlighted?: string[]; onSelect?: (id: string | null) => void; compact?: boolean }

/** Cytoscape wrapper: risk-coloured nodes; highlighted nodes + edges between them glow, everything else dims. */
export function GraphView({ data, highlighted = [], onSelect, compact }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const cy = useRef<Core | null>(null);
  const sel = useRef(onSelect);
  sel.current = onSelect;

  useEffect(() => {
    if (!el.current) return;
    const c = cytoscape({
      container: el.current,
      elements: [
        ...data.nodes.map((n) => ({ data: { id: n.id, color: RISK[n.risk_level].hex, size: compact ? 16 : 14 + n.risk_score / 5, label: compact ? "" : n.id.replace("ACC_", "") } })),
        ...data.edges.map((e, i) => ({ data: { id: `e${i}`, source: e.source, target: e.target } })),
      ],
      style: [
        { selector: "node", style: { "background-color": "data(color)", width: "data(size)", height: "data(size)", label: "data(label)", color: "#94a3b8", "font-size": 8, "text-valign": "bottom" } },
        { selector: "edge", style: { width: 1, "line-color": "#475569", "target-arrow-color": "#475569", "target-arrow-shape": "triangle", "curve-style": "bezier", opacity: 0.6 } },
        { selector: ".dim", style: { opacity: 0.08 } },
        { selector: "node.glow", style: { "border-width": 3, "border-color": "#818cf8", "overlay-color": "#6366F1", "overlay-opacity": 0.25, "overlay-padding": 8 } },
        { selector: "edge.glow", style: { "line-color": "#818cf8", "target-arrow-color": "#818cf8", width: 2.5, opacity: 1 } },
      ],
      layout: { name: "cose", animate: false, nodeRepulsion: () => 9000 } as cytoscape.LayoutOptions,
    });
    c.on("tap", "node", (e) => sel.current?.(e.target.id()));
    c.on("tap", (e) => { if (e.target === c) sel.current?.(null); });
    cy.current = c;
    return () => c.destroy();
  }, [data, compact]);

  useEffect(() => {
    const c = cy.current;
    if (!c) return;
    c.elements().removeClass("dim glow");
    if (!highlighted.length) return;
    const set = new Set(highlighted);
    const nodes = c.nodes().filter((n) => set.has(n.id()));
    const edges = nodes.edgesWith(nodes);
    c.elements().addClass("dim");
    nodes.removeClass("dim").addClass("glow");
    edges.removeClass("dim").addClass("glow");
    if (nodes.length) c.animate({ fit: { eles: nodes, padding: 60 }, duration: 350 });
  }, [highlighted, data]);

  return <div ref={el} className="h-full w-full" data-testid="graph" />;
}
