import { max } from 'd3-array';
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
} from 'd3-force';
import type { SimulationLinkDatum, SimulationNodeDatum } from 'd3-force';
import { hierarchy, tree as d3Tree } from 'd3-hierarchy';
import type { HierarchyPointLink, HierarchyPointNode } from 'd3-hierarchy';
import { scaleBand, scaleLinear } from 'd3-scale';
import { curveBasis, line, linkVertical } from 'd3-shape';
import type {
  ChartDiagram,
  ChartDiagramPoint,
  ExamDiagram,
  GraphDiagram,
  GraphDiagramEdge,
  GraphDiagramNode,
  TreeDiagram,
  TreeDiagramNode,
} from '../../types';

const VIEWBOX_WIDTH = 720;
const VIEWBOX_HEIGHT = 420;
const NODE_RADIUS = 24;
const GRAPH_MARGIN_X = 74;
const GRAPH_MARGIN_Y = 62;
const TREE_MARGIN_X = 78;
const TREE_MARGIN_Y = 70;
const CHART_MARGIN = { top: 34, right: 34, bottom: 58, left: 64 };
const CENTER_X = VIEWBOX_WIDTH / 2;
const CENTER_Y = VIEWBOX_HEIGHT / 2 + 10;

function QuestionDiagrams({ diagrams }: { diagrams?: ExamDiagram[] }) {
  const visibleDiagrams = Array.isArray(diagrams) ? diagrams.filter(isVisibleDiagram) : [];
  if (visibleDiagrams.length === 0) {
    return null;
  }

  return (
    <div className="question-diagrams">
      {visibleDiagrams.map((diagram) => {
        if (diagram.type === 'tree') {
          return <TreeDiagramView key={diagram.id} diagram={diagram} />;
        }
        if (diagram.type === 'chart') {
          return <ChartDiagramView key={diagram.id} diagram={diagram} />;
        }
        return <GraphDiagramView key={diagram.id} diagram={diagram} />;
      })}
    </div>
  );
}

function GraphDiagramView({ diagram }: { diagram: GraphDiagram }) {
  const nodes = diagram.nodes.filter((node) => node.id);
  const nodeIds = new Set(nodes.map((node) => node.id));
  const edges = diagram.edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target));
  const positions = layoutNodes(nodes, edges, diagram.start_node || undefined);
  const highlightedNodes = new Set(diagram.highlighted_nodes || []);
  const edgeIds = edgeIdSet(edges);
  const highlightedEdges = new Set((diagram.highlighted_edges || []).filter((id) => edgeIds.has(id)));
  const titleId = `${diagram.id}-title`;
  const descId = `${diagram.id}-description`;

  return (
    <figure className="graph-diagram">
      {diagram.title && <figcaption>{diagram.title}</figcaption>}
      <svg
        viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
        role="img"
        aria-labelledby={`${titleId} ${descId}`}
        className="graph-diagram__svg"
      >
        <title id={titleId}>{diagram.title || 'Graph diagram'}</title>
        <desc id={descId}>
          Graph with {nodes.length} nodes and {edges.length} edges.
        </desc>
        <defs>
          <marker
            id={`${diagram.id}-arrow`}
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="5"
            orient="auto"
            markerUnits="strokeWidth"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" className="graph-diagram__arrow" />
          </marker>
          <marker
            id={`${diagram.id}-arrow-highlight`}
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="5"
            orient="auto"
            markerUnits="strokeWidth"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" className="graph-diagram__arrow is-highlighted" />
          </marker>
        </defs>

        <g className="graph-diagram__edges">
          {edges.map((edge, index) => {
            const source = positions[edge.source];
            const target = positions[edge.target];
            if (!source || !target) {
              return null;
            }
            const id = edge.id || edgeKey(edge);
            const isHighlighted = highlightedEdges.has(id);
            const path = edge.source === edge.target
              ? selfLoopPath(source.x, source.y)
              : edgePath(source.x, source.y, target.x, target.y);
            const label = edge.label || edge.weight;
            const labelText = label == null ? '' : String(label).trim();
            const labelWidth = Math.max(34, labelText.length * 10 + 20);
            const labelPoint = edge.source === edge.target
              ? { x: source.x + NODE_RADIUS + 22, y: source.y - NODE_RADIUS - 18 }
              : edgeLabelPoint(source.x, source.y, target.x, target.y, index);

            return (
              <g key={`${id}-${index}`} className={`graph-diagram__edge ${isHighlighted ? 'is-highlighted' : ''}`}>
                <path
                  d={path}
                  markerEnd={edge.directed ? `url(#${diagram.id}-${isHighlighted ? 'arrow-highlight' : 'arrow'})` : undefined}
                />
                {labelText && (
                  <g transform={`translate(${labelPoint.x} ${labelPoint.y})`}>
                    <rect className="graph-diagram__edge-label-bg" x={-labelWidth / 2} y="-12" width={labelWidth} height="24" rx="6" />
                    <text className="graph-diagram__edge-label" textAnchor="middle" dominantBaseline="middle">
                      {labelText}
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </g>

        <g className="graph-diagram__nodes">
          {nodes.map((node) => {
            const position = positions[node.id];
            const isStart = diagram.start_node === node.id;
            const isHighlighted = highlightedNodes.has(node.id) || isStart;
            return (
              <g
                key={node.id}
                className={`graph-diagram__node ${isHighlighted ? 'is-highlighted' : ''} ${isStart ? 'is-start' : ''}`}
                transform={`translate(${position.x} ${position.y})`}
              >
                <circle r={NODE_RADIUS} />
                <text textAnchor="middle" dominantBaseline="middle">
                  {node.label || node.id}
                </text>
                {isStart && (
                  <text className="graph-diagram__start-label" textAnchor="middle" y={NODE_RADIUS + 18}>
                    start
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>
    </figure>
  );
}

function TreeDiagramView({ diagram }: { diagram: TreeDiagram }) {
  const layout = layoutTree(diagram.root);
  const highlightedNodes = new Set(diagram.highlighted_nodes || []);
  const titleId = `${diagram.id}-title`;
  const descId = `${diagram.id}-description`;

  return (
    <figure className="graph-diagram tree-diagram">
      {diagram.title && <figcaption>{diagram.title}</figcaption>}
      <svg
        viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
        role="img"
        aria-labelledby={`${titleId} ${descId}`}
        className="graph-diagram__svg"
      >
        <title id={titleId}>{diagram.title || 'Tree diagram'}</title>
        <desc id={descId}>
          Tree with {layout.nodes.length} nodes.
        </desc>
        <g className="graph-diagram__edges tree-diagram__edges">
          {layout.links.map((link) => {
            const source = link.source;
            const target = link.target;
            const path = treeLinkPath(source, target);
            return (
              <g key={`${source.data.id}-${target.data.id}`} className="graph-diagram__edge tree-diagram__edge">
                <path d={path} />
              </g>
            );
          })}
        </g>
        <g className="graph-diagram__nodes tree-diagram__nodes">
          {layout.nodes.map((node, index) => {
            const isHighlighted = highlightedNodes.has(node.data.id);
            return (
              <g
                key={`${node.data.id}-${index}`}
                className={`graph-diagram__node ${isHighlighted ? 'is-highlighted' : ''}`}
                transform={`translate(${node.x} ${node.y})`}
              >
                <circle r={NODE_RADIUS} />
                <text textAnchor="middle" dominantBaseline="middle">
                  {node.data.label || node.data.id}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </figure>
  );
}

function ChartDiagramView({ diagram }: { diagram: ChartDiagram }) {
  const data = diagram.data.filter((point) => point.label && Number.isFinite(point.value));
  const titleId = `${diagram.id}-title`;
  const descId = `${diagram.id}-description`;
  const chart = layoutChart(data);
  const linePath = chartLinePath(data, chart);

  return (
    <figure className="graph-diagram chart-diagram">
      {diagram.title && <figcaption>{diagram.title}</figcaption>}
      <svg
        viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
        role="img"
        aria-labelledby={`${titleId} ${descId}`}
        className="graph-diagram__svg"
      >
        <title id={titleId}>{diagram.title || 'Chart diagram'}</title>
        <desc id={descId}>
          {diagram.chart_type} chart with {data.length} data points.
        </desc>
        <g className="chart-diagram__axis">
          <line x1={CHART_MARGIN.left} y1={chart.bottom} x2={chart.right} y2={chart.bottom} />
          <line x1={CHART_MARGIN.left} y1={chart.top} x2={CHART_MARGIN.left} y2={chart.bottom} />
          {chart.ticks.map((tick) => (
            <g key={tick} transform={`translate(0 ${chart.y(tick)})`}>
              <line x1={CHART_MARGIN.left - 5} x2={chart.right} />
              <text x={CHART_MARGIN.left - 10} textAnchor="end" dominantBaseline="middle">
                {formatTick(tick)}
              </text>
            </g>
          ))}
        </g>
        {diagram.chart_type === 'bar' ? (
          <g className="chart-diagram__bars">
            {data.map((point) => {
              const x = chart.x(point.label) ?? CHART_MARGIN.left;
              const y = chart.y(point.value);
              return (
                <rect
                  key={point.label}
                  x={x}
                  y={y}
                  width={chart.x.bandwidth()}
                  height={Math.max(1, chart.bottom - y)}
                />
              );
            })}
          </g>
        ) : (
          <g className="chart-diagram__line">
            {linePath && <path d={linePath} />}
            {data.map((point) => (
              <circle key={point.label} cx={(chart.x(point.label) ?? 0) + chart.x.bandwidth() / 2} cy={chart.y(point.value)} r="4" />
            ))}
          </g>
        )}
        <g className="chart-diagram__labels">
          {data.map((point) => (
            <text
              key={point.label}
              x={(chart.x(point.label) ?? 0) + chart.x.bandwidth() / 2}
              y={chart.bottom + 20}
              textAnchor="middle"
            >
              {point.label}
            </text>
          ))}
          {diagram.x_label && (
            <text x={(CHART_MARGIN.left + chart.right) / 2} y={VIEWBOX_HEIGHT - 16} textAnchor="middle">
              {diagram.x_label}
            </text>
          )}
          {diagram.y_label && (
            <text transform={`translate(18 ${(chart.top + chart.bottom) / 2}) rotate(-90)`} textAnchor="middle">
              {diagram.y_label}
            </text>
          )}
        </g>
      </svg>
    </figure>
  );
}

function isVisibleDiagram(diagram: ExamDiagram): diagram is ExamDiagram {
  if (
    diagram?.type === 'graph' &&
    typeof diagram.id === 'string' &&
    diagram.id.trim().length > 0 &&
    Array.isArray(diagram.nodes) &&
    Array.isArray(diagram.edges) &&
    diagram.nodes.length >= 2 &&
    diagram.edges.length >= 1
  ) {
    return true;
  }
  if (
    diagram?.type === 'tree' &&
    typeof diagram.id === 'string' &&
    diagram.id.trim().length > 0 &&
    Boolean(diagram.root?.id)
  ) {
    return true;
  }
  return (
    diagram?.type === 'chart' &&
    typeof diagram.id === 'string' &&
    diagram.id.trim().length > 0 &&
    (diagram.chart_type === 'bar' || diagram.chart_type === 'line') &&
    Array.isArray(diagram.data) &&
    diagram.data.length > 0
  );
}

function layoutNodes(
  nodes: GraphDiagramNode[],
  edges: GraphDiagramEdge[],
  startNode?: string,
): Record<string, { x: number; y: number }> {
  type ForceNode = GraphDiagramNode & SimulationNodeDatum;
  type ForceEdge = SimulationLinkDatum<ForceNode>;
  const layerByNode = startNode ? graphLayers(nodes, edges, startNode) : new Map<string, number>();
  const maxLayer = Math.max(1, ...Array.from(layerByNode.values()));
  const layerCounts = new Map<number, number>();
  const layerSeen = new Map<number, number>();

  const forceNodes: ForceNode[] = nodes.map((node, index) => {
    const layer = layerByNode.get(node.id);
    const radius = Math.min(170, Math.max(110, nodes.length * 24));
    const angle = -Math.PI / 2 + (index / nodes.length) * Math.PI * 2;
    if (layer != null) {
      layerCounts.set(layer, (layerCounts.get(layer) || 0) + 1);
    }
    return {
      ...node,
      x: layer == null ? CENTER_X + Math.cos(angle) * radius : graphLayerX(layer, maxLayer),
      y: layer == null ? CENTER_Y + Math.sin(angle) * radius : CENTER_Y,
    };
  });
  forceNodes.forEach((node, index) => {
    const layer = layerByNode.get(node.id);
    if (layer == null) {
      return;
    }
    const count = layerCounts.get(layer) || 1;
    const seen = layerSeen.get(layer) || 0;
    layerSeen.set(layer, seen + 1);
    const spacing = Math.min(110, Math.max(64, 240 / Math.max(1, count - 1)));
    node.y = CENTER_Y + (seen - (count - 1) / 2) * spacing;
    node.x = graphLayerX(layer, maxLayer);
  });
  const forceEdges: ForceEdge[] = nodes.length < 2 ? [] : [];
  const nodeIds = new Set(nodes.map((node) => node.id));
  const edgeSourceTarget = edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target));
  edgeSourceTarget.forEach((edge) => {
    forceEdges.push({ source: edge.source, target: edge.target });
  });

  forceSimulation(forceNodes)
    .force('link', forceLink<ForceNode, ForceEdge>(forceEdges).id((node) => node.id).distance(145).strength(0.48))
    .force('charge', forceManyBody().strength(-620))
    .force('collide', forceCollide(NODE_RADIUS + 28).strength(1))
    .force('center', forceCenter(CENTER_X, CENTER_Y))
    .force('x', forceX<ForceNode>((node) => {
      const layer = layerByNode.get(node.id);
      return layer == null ? CENTER_X : graphLayerX(layer, maxLayer);
    }).strength(layerByNode.size ? 0.16 : 0.035))
    .force('y', forceY<ForceNode>(CENTER_Y).strength(0.035))
    .stop()
    .tick(260);

  return fitGraphPositions(forceNodes);
}

function fitGraphPositions(nodes: Array<GraphDiagramNode & SimulationNodeDatum>): Record<string, { x: number; y: number }> {
  const xs = nodes.map((node) => node.x ?? CENTER_X);
  const ys = nodes.map((node) => node.y ?? CENTER_Y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spanX = Math.max(1, maxX - minX);
  const spanY = Math.max(1, maxY - minY);
  const availableWidth = VIEWBOX_WIDTH - GRAPH_MARGIN_X * 2;
  const availableHeight = VIEWBOX_HEIGHT - GRAPH_MARGIN_Y * 2;
  const scale = Math.min(1.35, Math.max(1, Math.min(availableWidth / spanX, availableHeight / spanY)));
  const fittedWidth = spanX * scale;
  const fittedHeight = spanY * scale;
  const offsetX = GRAPH_MARGIN_X + (availableWidth - fittedWidth) / 2;
  const offsetY = GRAPH_MARGIN_Y + (availableHeight - fittedHeight) / 2;

  return nodes.reduce<Record<string, { x: number; y: number }>>((positions, node) => {
    const x = offsetX + ((node.x ?? CENTER_X) - minX) * scale;
    const y = offsetY + ((node.y ?? CENTER_Y) - minY) * scale;
    positions[node.id] = {
      x: clamp(x, GRAPH_MARGIN_X, VIEWBOX_WIDTH - GRAPH_MARGIN_X),
      y: clamp(y, GRAPH_MARGIN_Y, VIEWBOX_HEIGHT - GRAPH_MARGIN_Y),
    };
    return positions;
  }, {});
}

function graphLayers(
  nodes: GraphDiagramNode[],
  edges: GraphDiagramEdge[],
  startNode: string,
): Map<string, number> {
  const nodeIds = new Set(nodes.map((node) => node.id));
  if (!nodeIds.has(startNode)) {
    return new Map();
  }
  const adjacency = new Map<string, string[]>();
  nodes.forEach((node) => adjacency.set(node.id, []));
  edges.forEach((edge) => {
    if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) {
      return;
    }
    adjacency.get(edge.source)?.push(edge.target);
    adjacency.get(edge.target)?.push(edge.source);
  });
  const layers = new Map<string, number>([[startNode, 0]]);
  const queue = [startNode];
  while (queue.length > 0) {
    const current = queue.shift() as string;
    const nextLayer = (layers.get(current) || 0) + 1;
    (adjacency.get(current) || []).forEach((next) => {
      if (layers.has(next)) {
        return;
      }
      layers.set(next, nextLayer);
      queue.push(next);
    });
  }
  let fallbackLayer = Math.max(0, ...Array.from(layers.values())) + 1;
  nodes.forEach((node) => {
    if (!layers.has(node.id)) {
      layers.set(node.id, fallbackLayer);
      fallbackLayer += 1;
    }
  });
  return layers;
}

function graphLayerX(layer: number, maxLayer: number): number {
  return GRAPH_MARGIN_X + (layer / Math.max(1, maxLayer)) * (VIEWBOX_WIDTH - GRAPH_MARGIN_X * 2);
}

function edgePath(sourceX: number, sourceY: number, targetX: number, targetY: number): string {
  const deltaX = targetX - sourceX;
  const deltaY = targetY - sourceY;
  const length = Math.hypot(deltaX, deltaY) || 1;
  const startX = sourceX + (deltaX / length) * NODE_RADIUS;
  const startY = sourceY + (deltaY / length) * NODE_RADIUS;
  const endX = targetX - (deltaX / length) * (NODE_RADIUS + 4);
  const endY = targetY - (deltaY / length) * (NODE_RADIUS + 4);
  return line<[number, number]>()([
    [startX, startY],
    [endX, endY],
  ]) || '';
}

function selfLoopPath(x: number, y: number): string {
  const startX = x + NODE_RADIUS * 0.7;
  const startY = y - NODE_RADIUS * 0.7;
  return line<[number, number]>()
    .curve(curveBasis)([
      [startX, startY],
      [x + 92, y - 92],
      [x - 8, y - 104],
      [x - NODE_RADIUS * 0.7, startY],
    ]) || '';
}

function edgeLabelPoint(
  sourceX: number,
  sourceY: number,
  targetX: number,
  targetY: number,
  index: number,
): { x: number; y: number } {
  const mid = midpoint(sourceX, sourceY, targetX, targetY);
  const deltaX = targetX - sourceX;
  const deltaY = targetY - sourceY;
  const length = Math.hypot(deltaX, deltaY) || 1;
  const alternatingOffset = index % 2 === 0 ? 1 : -1;
  return {
    x: mid.x + (-deltaY / length) * 12 * alternatingOffset,
    y: mid.y + (deltaX / length) * 12 * alternatingOffset,
  };
}

function midpoint(sourceX: number, sourceY: number, targetX: number, targetY: number): { x: number; y: number } {
  return {
    x: (sourceX + targetX) / 2,
    y: (sourceY + targetY) / 2,
  };
}

function edgeIdSet(edges: GraphDiagramEdge[]): Set<string> {
  return new Set(edges.flatMap((edge) => [edge.id || '', edgeKey(edge)].filter(Boolean)));
}

function edgeKey(edge: GraphDiagramEdge): string {
  return `${edge.source}->${edge.target}:${edge.label || edge.weight || ''}:${edge.directed ? '1' : '0'}`;
}

function layoutTree(root: TreeDiagramNode): {
  nodes: Array<HierarchyPointNode<TreeDiagramNode>>;
  links: Array<HierarchyPointLink<TreeDiagramNode>>;
} {
  const treeRoot = hierarchy<TreeDiagramNode>(root, (node) => node.children || []);
  const layout = d3Tree<TreeDiagramNode>()
    .size([VIEWBOX_WIDTH - TREE_MARGIN_X * 2, VIEWBOX_HEIGHT - TREE_MARGIN_Y * 2])
    .separation((left, right) => (left.parent === right.parent ? 1.2 : 1.8));
  const positionedRoot = layout(treeRoot);
  const nodes = positionedRoot.descendants().map((node) => {
    node.x += TREE_MARGIN_X;
    node.y += TREE_MARGIN_Y;
    return node;
  });
  return {
    nodes,
    links: positionedRoot.links(),
  };
}

function treeLinkPath(
  source: HierarchyPointNode<TreeDiagramNode>,
  target: HierarchyPointNode<TreeDiagramNode>,
): string {
  const path = linkVertical<
    { source: { x: number; y: number }; target: { x: number; y: number } },
    { x: number; y: number }
  >()
    .x((point) => point.x)
    .y((point) => point.y)({
      source: { x: source.x, y: source.y + NODE_RADIUS },
      target: { x: target.x, y: target.y - NODE_RADIUS },
    });
  return path || '';
}

function layoutChart(data: ChartDiagramPoint[]) {
  const top = CHART_MARGIN.top;
  const bottom = VIEWBOX_HEIGHT - CHART_MARGIN.bottom;
  const right = VIEWBOX_WIDTH - CHART_MARGIN.right;
  const largestValue = Math.max(1, max(data, (point) => point.value) || 1);
  const x = scaleBand<string>()
    .domain(data.map((point) => point.label))
    .range([CHART_MARGIN.left, right])
    .padding(0.28);
  const y = scaleLinear()
    .domain([0, largestValue])
    .nice()
    .range([bottom, top]);
  return {
    top,
    bottom,
    right,
    x,
    y,
    ticks: y.ticks(5),
  };
}

function chartLinePath(
  data: ChartDiagramPoint[],
  chart: ReturnType<typeof layoutChart>,
): string {
  const path = line<ChartDiagramPoint>()
    .x((point) => (chart.x(point.label) ?? 0) + chart.x.bandwidth() / 2)
    .y((point) => chart.y(point.value))
    .curve(curveBasis)(data);
  return path || '';
}

function formatTick(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function clamp(value: number, minValue: number, maxValue: number): number {
  return Math.max(minValue, Math.min(maxValue, value));
}

export default QuestionDiagrams;
