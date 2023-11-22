from typing import Any, Dict, List, Tuple

class UnionFind:

    item_to_element: Dict[Any, int] = {}
    components: Dict[int, List[int]] = {}
    element_links: List[Tuple[int, int]] = []

    def __init__(self, items, links):
        """Initialize union-find with a list of items and a list of links given as pairs of items."""
        self.size = len(items)
        self.item_list = list(items)
        self.parent = [i for i in range(self.size)]
        self.rank = [0] * self.size
        for i, item in enumerate(self.item_list):
            self.item_to_element[item] = i
        for link in links:
            elt_link = map(self.item_to_element.get, link)
            self.element_links.append(elt_link)
        self._compute_components()

    # find the root element for given element
    def _find_representative(self, x):
        if self.parent[x] != x:
            self.parent[x] = self._find_representative(self.parent[x])
        return self.parent[x]

    def _union(self, root_x, root_y):
        if root_x != root_y:
            if self.rank[root_x] < self.rank[root_y]:
                self.parent[root_x] = root_y
            elif self.rank[root_x] > self.rank[root_y]:
                self.parent[root_y] = root_x
            else:
                self.parent[root_y] = root_x
                self.rank[root_x] += 1

    def _connect_elements(self):
        for link in self.element_links:
            roots = map(self._find_representative, link)
            self._union(*roots)

    def _compute_components(self):
        self._connect_elements()
        for i in range(self.size):
            root = self._find_representative(i)
            if root not in self.components:
                self.components[root] = [i]
            else:
                self.components[root].append(i)

    def get_item_components(self, sort_key):
        def elements_to_sorted_items(elements : List[int]):
            items = list(map(lambda e: self.item_list[e], elements))
            items.sort(key=sort_key)
            return items
        return list(map(elements_to_sorted_items, self.components.values()))
