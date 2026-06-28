import { hierarchy, tree as d3Tree } from 'd3-hierarchy';
import type { HierarchyPointLink, HierarchyPointNode } from 'd3-hierarchy';
import type {
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
const TREE_MARGIN_X = 78;
const TREE_MARGIN_Y = 70;
const CENTER_X = VIEWBOX_WIDTH / 2;
const CENTER_Y = VIEWBOX_HEIGHT / 2 + 10;

function QuestionDiagrams({ diagrams }: { diagrams?: ExamDiagram[] }) {
  const visibleDiagrams = Array.isArray(diagrams) ? diagrams.filter(isVisibleDiagram) : [];
  if (visibleDiagrams.length === 0) {
    return null;
  }

  return (
    <div className="question-diagrams">
      {visibleDiagrams.map((diagram) =>
        diagram.type === 'tree' ? (
          <TreeDiagramView key={diagram.id} diagram={diagram} />
        ) : (
          <GraphDiagramView key={diagram.id} diagram={diagram} />
        ),
      )}
    </div>
  );
}

function GraphDiagramView({ diagram }: { diagram: GraphDiagram }) {
  const nodes = diagram.nodes.filter((node) => node.id);
  const nodeIds = new Set(nodes.map((node) => node.id));
  const edges = diagram.edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target));
  const positions = layoutNodes(nodes);
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
            const labelPoint = edge.source === edge.target
              ? { x: source.x + NODE_RADIUS + 22, y: source.y - NODE_RADIUS - 18 }
              : midpoint(source.x, source.y, target.x, target.y);

            return (
              <g key={`${id}-${index}`} className={`graph-diagram__edge ${isHighlighted ? 'is-highlighted' : ''}`}>
                <path
                  d={path}
                  markerEnd={edge.directed ? `url(#${diagram.id}-${isHighlighted ? 'arrow-highlight' : 'arrow'})` : undefined}
                />
                {label != null && String(label).trim() && (
                  <g transform={`translate(${labelPoint.x} ${labelPoint.y})`}>
                    <rect className="graph-diagram__edge-label-bg" x="-18" y="-12" width="36" height="24" rx="6" />
                    <text className="graph-diagram__edge-label" textAnchor="middle" dominantBaseline="middle">
                      {String(label)}
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
            return (
              <g key={`${source.data.id}-${target.data.id}`} className="graph-diagram__edge tree-diagram__edge">
                <path
                  d={`M ${source.x} ${source.y + NODE_RADIUS} C ${source.x} ${(source.y + target.y) / 2}, ${target.x} ${(source.y + target.y) / 2}, ${target.x} ${target.y - NODE_RADIUS}`}
                />
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
  return (
    diagram?.type === 'tree' &&
    typeof diagram.id === 'string' &&
    diagram.id.trim().length > 0 &&
    Boolean(diagram.root?.id)
  );
}

function layoutNodes(nodes: GraphDiagramNode[]): Record<string, { x: number; y: number }> {
  const radius = Math.min(145, Math.max(92, nodes.length * 20));
  const startAngle = nodes.length <= 2 ? -Math.PI / 2 : -Math.PI / 2 - Math.PI / nodes.length;
  return nodes.reduce<Record<string, { x: number; y: number }>>((positions, node, index) => {
    const angle = startAngle + (index / nodes.length) * Math.PI * 2;
    positions[node.id] = {
      x: CENTER_X + Math.cos(angle) * radius,
      y: CENTER_Y + Math.sin(angle) * radius,
    };
    return positions;
  }, {});
}

function edgePath(sourceX: number, sourceY: number, targetX: number, targetY: number): string {
  const deltaX = targetX - sourceX;
  const deltaY = targetY - sourceY;
  const length = Math.hypot(deltaX, deltaY) || 1;
  const startX = sourceX + (deltaX / length) * NODE_RADIUS;
  const startY = sourceY + (deltaY / length) * NODE_RADIUS;
  const endX = targetX - (deltaX / length) * (NODE_RADIUS + 4);
  const endY = targetY - (deltaY / length) * (NODE_RADIUS + 4);
  return `M ${startX} ${startY} L ${endX} ${endY}`;
}

function selfLoopPath(x: number, y: number): string {
  const startX = x + NODE_RADIUS * 0.7;
  const startY = y - NODE_RADIUS * 0.7;
  return `M ${startX} ${startY} C ${x + 92} ${y - 92}, ${x - 8} ${y - 104}, ${x - NODE_RADIUS * 0.7} ${startY}`;
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

export default QuestionDiagrams;
