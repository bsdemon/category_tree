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

    def _build_graph(self, cat_by_id: Dict[int, Category]) -> Dict[int, Set[int]]:
        """Build undirected graph from CategorySimilarity."""
        graph: Dict[int, Set[int]] = {cid: set() for cid in cat_by_id.keys()}

        similarities: list[tuple[int, int]] = list(
            CategorySimilarity.objects.values_list("category1_id", "category2_id")
        ) # get all similaritiess

        for c1_id, c2_id in similarities: # check if category still exists
            if c1_id in graph and c2_id in graph:
                graph[c1_id].add(c2_id) # add similarities to graph
                graph[c2_id].add(c1_id) # add similarities to graph

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
            component: List[int] = [] # here we create island of connected nodes

            while queue: # BFS to find islands
                node = queue.popleft()
                component.append(node)
                for neighbor in graph[node]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            islands.append(component) # here we add island to other islands

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
        # BFS to find shortes path
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

        path: List[int] = [] # reconstruct path
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
