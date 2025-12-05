from collections import deque
from typing import Dict, List, Set, Tuple, Optional

from django.core.management.base import BaseCommand

from api.models import Category, CategorySimilarity


class Command(BaseCommand):
    help = "Analyze category similarity graph: rabbit holes and rabbit islands."

    def handle(self, *args, **options):
        categories = Category.objects.all().only("id", "name")
        cat_by_id: Dict[int, Category] = {c.id: c for c in categories}

        graph = self._build_graph(cat_by_id)
        if not graph:
            self.stdout.write("No categories found.")
            return

        rabbit_islands = self._find_islands(graph)
        longest_path_ids = self._find_longest_rabbit_hole(graph, rabbit_islands)

        self._print_longest_rabbit_hole(longest_path_ids, cat_by_id)
        self._print_rabbit_islands(rabbit_islands, cat_by_id)
        self._export_graphviz(graph, cat_by_id, rabbit_islands, longest_path_ids)

    def _build_graph(self, cat_by_id: Dict[int, Category]) -> Dict[int, Set[int]]:
        """Build undirected graph from CategorySimilarity."""
        graph: Dict[int, Set[int]] = {cid: set() for cid in cat_by_id.keys()}

        similarities: list[tuple[int, int]] = list(
            CategorySimilarity.objects.values_list("category1_id", "category2_id")
        )

        for c1_id, c2_id in similarities:
            if c1_id in graph and c2_id in graph:
                graph[c1_id].add(c2_id)
                graph[c2_id].add(c1_id)

        return graph

    def _find_islands(self, graph: Dict[int, Set[int]]) -> List[List[int]]:
        """Find connected components (rabbit islands) via BFS."""
        visited: Set[int] = set()
        islands: List[List[int]] = []

        # list(...) to avoid creating a new view object at every iteration
        for start in list(graph.keys()):
            if start in visited:
                continue

            queue: deque[int] = deque([start])
            visited.add(start)
            component: List[int] = []

            while queue:
                node = queue.popleft()
                component.append(node)
                for neighbor in graph[node]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            islands.append(component)

        return islands

    def _bfs_longest_from(
        self,
        start: int,
        graph: Dict[int, Set[int]],
    ) -> Tuple[int, List[int]]:
        """
        BFS from 'start' and return:
        - max distance from start
        - one of the longest shortest paths (as list of node ids)
        """
        queue: deque[int] = deque([start])
        dist: Dict[int, int] = {start: 0}
        parent: Dict[int, Optional[int]] = {start: None}

        farthest_node = start
        max_dist = 0

        while queue:
            node = queue.popleft()
            for neighbor in graph[node]:
                if neighbor not in dist:
                    dist[neighbor] = dist[node] + 1
                    parent[neighbor] = node
                    queue.append(neighbor)

                    if dist[neighbor] > max_dist:
                        max_dist = dist[neighbor]
                        farthest_node = neighbor

        path: List[int] = []
        cur: Optional[int] = farthest_node
        while cur is not None:
            path.append(cur)
            cur = parent[cur]
        path.reverse()

        return max_dist, path


    def _component_diameter_exact(
        self,
        graph: Dict[int, Set[int]],
        component_nodes: List[int],
    ) -> List[int]:
        """
        Exact diameter for a single connected component
        using BFS from every node in the component.
        """
        best_distance = -1
        best_path: List[int] = []

        for node in component_nodes:
            distance, path = self._bfs_longest_from(node, graph)
            if distance > best_distance:
                best_distance = distance
                best_path = path

        return best_path

    def _component_diameter_approx(
        self,
        graph: Dict[int, Set[int]],
        component_nodes: List[int],
    ) -> List[int]:
        """
        Approximate diameter for a component using 2 BFS:
        1) BFS from an arbitrary node u -> farthest v
        2) BFS from v -> farthest w, return path v -> w
        """
        if not component_nodes:
            return []

        start = component_nodes[0]

        # First BFS: get farthest node v from start
        _, path_from_start = self._bfs_longest_from(start, graph)
        v = path_from_start[-1]

        # Second BFS: get farthest node w from v and the path v -> w
        _, path_v_to_w = self._bfs_longest_from(v, graph)
        return path_v_to_w

    def _find_longest_rabbit_hole(
        self,
        graph: Dict[int, Set[int]],
        islands: List[List[int]],
    ) -> List[int]:
        """
        Find the globally longest shortest path (longest rabbit hole),
        using per-island diameter (exact for small components, approx for large).
        """
        best_path: List[int] = []
        SMALL_COMPONENT_LIMIT = 300  # tune if needed

        for component in islands:
            if len(component) == 0:
                continue

            if len(component) <= SMALL_COMPONENT_LIMIT:
                path = self._component_diameter_exact(graph, component)
            else:
                path = self._component_diameter_approx(graph, component)

            if len(path) > len(best_path):
                best_path = path

        return best_path


    def _print_longest_rabbit_hole(
        self,
        path_ids: List[int],
        cat_by_id: Dict[int, Category],
    ) -> None:
        if not path_ids:
            print("\nNo rabbit holes found.")
            return

        print("\n=== Longest rabbit hole ===")
        print(f"Length (edges): {max(len(path_ids) - 1, 0)}")
        print(f"Length (nodes): {len(path_ids)}")

        readable = " -> ".join(
            f"{cat_by_id[cid].id}:{cat_by_id[cid].name}" for cid in path_ids
        )
        print(readable)

    def _print_rabbit_islands(
        self,
        islands: List[List[int]],
        cat_by_id: Dict[int, Category],
    ) -> None:
        print("\n=== Rabbit islands ===")
        print(f"Total islands: {len(islands)}")

        islands_sorted = sorted(islands, key=len, reverse=True)

        MAX_SHOW = 20  # result is too long.  Show first N

        for idx, component in enumerate(islands_sorted, start=1):
            print(f"\nIsland #{idx} (size={len(component)}):")

            if len(component) <= MAX_SHOW:
                # малки island-и → показваме всичко
                for cid in component:
                    cat = cat_by_id[cid]
                    print(f"  - {cat.id}: {cat.name}")
            else:
                # big islands, onnly firsts and lasts elements
                first = component[:10]
                last = component[-10:]

                print("  First 10 categories:")
                for cid in first:
                    cat = cat_by_id[cid]
                    print(f"    - {cat.id}: {cat.name}")

                print("  ...")

                print("  Last 10 categories:")
                for cid in last:
                    cat = cat_by_id[cid]
                    print(f"    - {cat.id}: {cat.name}")

    def _export_graphviz(
        self,
        graph: Dict[int, Set[int]],
        cat_by_id: Dict[int, Category],
        islands: List[List[int]],
        longest_path_ids: List[int],
        filename: str = "rabbit_graph.dot",
    ) -> None:
        # Set for quick check if an edge is in the longest path
        path_edges: Set[tuple[int, int]] = set()
        if len(longest_path_ids) > 1:
            for a, b in zip(longest_path_ids, longest_path_ids[1:]):
                path_edges.add((a, b))
                path_edges.add((b, a))  # неориентиран

        # Assign a "color index" per island
        # node_to_island: dict[int, int] = {}
        # for idx, comp in enumerate(islands):
        #     for cid in comp:
        #         node_to_island[cid] = idx

        with open(filename, "w", encoding="utf-8") as f:
            f.write('graph RabbitGraph {\n')
            f.write('  overlap=false;\n')
            f.write('  splines=true;\n')

            # Define nodes
            # for cid, cat in cat_by_id.items():
            #     # island_idx = node_to_island.get(cid, 0)
            #     # Просто colorN, реално можеш да ги мапнеш после към конкретни цветове
            #     f.write(
            #         f'  {cid} [label="{cid}: {cat.name}", '
            #         f'color="black", '
            #         f'cluster="{island_idx}"];\n'
            #     )

            # Define edges
            written_edges: Set[tuple[int, int]] = set()
            for c1, neighbors in graph.items():
                for c2 in neighbors:
                    if (c2, c1) in written_edges:
                        continue  # избегни дублиране на неориентирани ребра

                    if (c1, c2) in path_edges:
                        # Edge is part of longest rabbit hole
                        f.write(f'  {c1} -- {c2} [penwidth=3];\n')
                    else:
                        f.write(f'  {c1} -- {c2};\n')

                    written_edges.add((c1, c2))

            f.write('}\n')

        print(f"\nGraphviz file written to {filename}")
